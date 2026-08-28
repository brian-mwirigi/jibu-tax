"""SQLAlchemy engine, session factory, and request-scoped DB dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


settings = get_settings()
engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create tables, then add WhatsApp columns on databases created before this feature."""
    Base.metadata.create_all(bind=engine)
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
