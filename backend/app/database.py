"""
File: backend/app/database.py
Description:
    PostgreSQL & SQLite connection, SQLModel & SQLAlchemy session factories,
    schema bootstrapping, ledger immutability triggers, and schema migrations.
"""

from collections.abc import Generator
from sqlalchemy import create_engine, inspect, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlmodel import Session, SQLModel

from app.config import get_settings

LEDGER_IMMUTABILITY_SQL = """
CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ledger_entries is append-only and cannot be updated or deleted';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ledger_entries_no_update ON ledger_entries;
CREATE TRIGGER ledger_entries_no_update
    BEFORE UPDATE OR DELETE ON ledger_entries
    FOR EACH ROW
    EXECUTE FUNCTION prevent_ledger_mutation();
"""


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Adapt Render / libpq URLs to a SQLAlchemy 2 + psycopg2 driver URL."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url and "+psycopg" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def _build_engine():
    settings = get_settings()
    url = normalize_database_url(settings.database_url)
    connect_args = {}
    engine_kwargs = {
        "echo": settings.environment == "development",
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database session."""
    with Session(engine) as session:
        yield session


def apply_ledger_immutability(bind=None) -> None:
    """Install the append-only trigger on PostgreSQL."""
    target = bind or engine
    if target.dialect.name != "postgresql":
        return
    with target.begin() as connection:
        connection.execute(text(LEDGER_IMMUTABILITY_SQL))


def ensure_schema() -> None:
    """Create tables, then ensure WhatsApp migration columns exist."""
    Base.metadata.create_all(bind=engine)
    SQLModel.metadata.create_all(engine)
    inspector = inspect(engine)
    if "invoices" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("invoices")}
    additions = {
        "whatsapp_status": "ALTER TABLE invoices ADD COLUMN whatsapp_status VARCHAR(32) DEFAULT 'pending'",
        "whatsapp_destination": "ALTER TABLE invoices ADD COLUMN whatsapp_destination VARCHAR(32)",
        "whatsapp_message_id": "ALTER TABLE invoices ADD COLUMN whatsapp_message_id VARCHAR(128)",
        "whatsapp_body": "ALTER TABLE invoices ADD COLUMN whatsapp_body TEXT",
    }
    missing = [sql for name, sql in additions.items() if name not in existing]
    if not missing:
        return
    with engine.begin() as conn:
        for sql in missing:
            conn.execute(text(sql))


def seed_default_taxpayers() -> None:
    """Seed demo taxpayers so demo numbers are pre-enrolled with trader PIN."""
    try:
        from app.models.taxpayer import Taxpayer
        from sqlmodel import Session, select
        with Session(engine) as session:
            demo_accounts = [
                ("+254712345678", "A012345678W", "MARY WANJIKU MAMA MBOGA", "sw"),
                ("+254722998877", "A012345678W", "OCHIENG AGROVET SUPPLIES", "sw"),
                ("+254733112233", "A012345678W", "JIBUTAX NAIROBI JUA KALI", "sheng"),
            ]
            for phone, pin, name, lang in demo_accounts:
                existing = session.exec(select(Taxpayer).where(Taxpayer.phone_number == phone)).first()
                if not existing:
                    session.add(Taxpayer(
                        phone_number=phone,
                        kra_pin=pin,
                        legal_name=name,
                        preferred_language=lang,
                        is_verified=True,
                    ))
            session.commit()
    except Exception as exc:
        logging.getLogger(__name__).warning("Default taxpayer seeding skipped: %s", exc)


def init_db() -> None:
    """Initialize schemas, apply immutability triggers, and run schema checks."""
    try:
        from app.models import (  # noqa: F401
            CallSession,
            Invoice,
            InvoiceItem,
            LedgerEntry,
            TaxReturnFiling,
            Taxpayer,
        )
    except ImportError:
        pass

    ensure_schema()
    apply_ledger_immutability()
    seed_default_taxpayers()


@event.listens_for(engine, "connect")
def _set_postgres_statement_timeout(dbapi_connection, _connection_record) -> None:
    if engine.dialect.name != "postgresql":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '30s'")
    cursor.close()
