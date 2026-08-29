from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import Base
from app.models import CallSession, Invoice, InvoiceItem, Taxpayer  # noqa: F401


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        sms_provider="mock",
        whatsapp_provider="mock",
        oscu_signing_secret="test-oscu-secret",
        kra_oscu_device_id="OSCU-KE-TEST-0001",
        default_trader_pin="A012345678W",
        default_trader_name="JibuTax Demo Trader",
        public_base_url="http://testserver",
    )


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
