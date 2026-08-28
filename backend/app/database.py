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