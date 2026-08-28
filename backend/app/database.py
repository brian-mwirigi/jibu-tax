"""
PostgreSQL connection, SQLModel session factory, and schema bootstrap.

Render supplies DATABASE_URL as postgres://…; SQLAlchemy 2 requires
postgresql+psycopg2://. Ledger tables are created here and then locked
append-only with a PostgreSQL trigger so successful sales cannot be rewritten.
"""

from collections.abc import Generator

from sqlalchemy import event, text
from sqlmodel import Session, SQLModel, create_engine

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


def normalize_database_url(url: str) -> str:
    """Adapt Render / libpq URLs to a SQLAlchemy 2 + psycopg2 driver URL."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg2" not in url and "+psycopg" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


def _build_engine():
    settings = get_settings()
    url = normalize_database_url(settings.DATABASE_URL)
    connect_args = {}
    engine_kwargs = {
        "echo": settings.ENVIRONMENT == "development",
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
    return create_engine(url, connect_args=connect_args, **engine_kwargs)


engine = _build_engine()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency alias used by request handlers."""
    yield from get_session()


def apply_ledger_immutability(bind=None) -> None:
    """Install the append-only trigger. No-op on SQLite (used in unit tests)."""
    target = bind or engine
    if target.dialect.name != "postgresql":
        return
    with target.begin() as connection:
        connection.execute(text(LEDGER_IMMUTABILITY_SQL))


def init_db() -> None:
    """Create all SQLModel tables and lock the immutable ledger on Postgres."""
    from app.models import (  # noqa: F401
        CallSession,
        Invoice,
        InvoiceItem,
        LedgerEntry,
        TaxReturnFiling,
        Taxpayer,
    )

    SQLModel.metadata.create_all(engine)
    apply_ledger_immutability()


@event.listens_for(engine, "connect")
def _set_postgres_statement_timeout(dbapi_connection, _connection_record) -> None:
    if engine.dialect.name != "postgresql":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("SET statement_timeout = '30s'")
    cursor.close()
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()

connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
    }

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()
