"""
Application configuration loaded from the environment.

Render injects DATABASE_URL from managed Postgres and REDIS_URL from Redis.
KRA filing tokens stay in process env and are never passed to the LLM.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    DATABASE_URL: str = "postgresql://jibutax:jibutax@localhost:5432/jibutax_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    KRA_ENVIRONMENT: str = "sandbox"
    KRA_BASE_URL: str = "https://sbx.kra.go.ke"
    KRA_API_TOKEN: str = ""
    KRA_TOT_PATH: str = "/filing/v1/tot/paymentregistration"
    KRA_NIL_PATH: str = "/dtd/return/v1/nil"
    KRA_OSCU_DEVICE_ID: str = "OSCU-KE-NBO-0042"

    TOT_RATE: str = "0.015"
    NIL_OBLIGATION_CODE: str = "7"

    DEFAULT_TRADER_PIN: str = "A012345678W"
    DEFAULT_TRADER_NAME: str = "JibuTax Demo Trader"

    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_AGENT_ID: str = ""
    WEBHOOK_SECRET: str = "jibutax_secret_token_2026"

    SMS_PROVIDER: str = "mock"
    AFRICASTALKING_USERNAME: str = ""
    AFRICASTALKING_API_KEY: str = ""
    AFRICASTALKING_SENDER_ID: str = ""
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
    return Settings()
