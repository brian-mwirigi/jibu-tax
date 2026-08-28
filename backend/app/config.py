"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_PROJECT_DIR / ".env"), str(_BACKEND_DIR / ".env")),
        extra="ignore",
    )

    environment: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    database_url: str = "sqlite:///./jibutax.db"

    kra_environment: str = "sandbox"
    kra_oscu_device_id: str = "OSCU-KE-NBO-0042"
    oscu_signing_secret: str = "jibutax-oscu-demo-secret-change-me"
    default_trader_pin: str = "A012345678W"
    default_trader_name: str = "JibuTax Demo Trader"

    sms_provider: str = "mock"
    africastalking_username: str = ""
    africastalking_api_key: str = ""
    africastalking_sender_id: str = "JIBUTAX"

    public_base_url: str = "http://localhost:8000"

    # WhatsApp QR delivery: mock | meta | twilio
    whatsapp_provider: str = "mock"
    whatsapp_verify_token: str = "jibutax_whatsapp_verify"
    whatsapp_meta_token: str = ""
    whatsapp_meta_phone_number_id: str = ""
    whatsapp_meta_api_version: str = "v21.0"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"


@lru_cache
def get_settings() -> Settings:
    return Settings()
