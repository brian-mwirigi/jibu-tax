from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: Literal[
        "development",
        "test",
        "staging",
        "production",
    ] = "development"

    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str

    cors_origins: list[str] = [
        "http://localhost:5173",
    ]

    kra_environment: Literal[
        "sandbox",
        "production",
    ] = "sandbox"

    kra_api_base_url: str = "https://sandbox.kra.go.ke"
    kra_api_key: SecretStr | None = None
    kra_oscu_device_id: str = "OSCU-DEMO"

    default_trader_pin: str
    default_trader_name: str

    gemini_api_key: SecretStr | None = None

    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_agent_id: str | None = None
    webhook_secret: SecretStr

    sms_provider: Literal[
        "mock",
        "africastalking",
        "twilio",
    ] = "mock"

    africastalking_username: str | None = None
    africastalking_api_key: SecretStr | None = None
    africastalking_sender_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()