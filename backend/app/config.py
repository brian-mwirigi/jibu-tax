"""
File: backend/app/config.py
Description:
    Application configuration loaded strictly from process environment and .env files.
    All secrets, tokens, database credentials, and KRA keys are read dynamically at runtime
    and are never hardcoded in source control.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_PROJECT_DIR / ".env"), str(_BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Settings
    ENVIRONMENT: str = Field(default="development")
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    PUBLIC_BASE_URL: str = Field(default="http://localhost:8000")

    # Databases & Queues
    DATABASE_URL: str = Field(default="sqlite:///./jibutax.db")
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_TASK_ALWAYS_EAGER: bool = Field(default=False)

    # AI Model Keys
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GOOGLE_API_KEY: Optional[str] = Field(default=None)

    # KRA / eTIMS Gateway & OSCU Engine
    KRA_ENVIRONMENT: str = Field(default="sandbox")
    KRA_BASE_URL: str = Field(default="https://sbx.kra.go.ke")
    KRA_API_TOKEN: Optional[str] = Field(default=None)
    KRA_TOT_PATH: str = Field(default="/filing/v1/tot/paymentregistration")
    KRA_NIL_PATH: str = Field(default="/dtd/return/v1/nil")
    KRA_OSCU_DEVICE_ID: str = Field(default="OSCU-KE-NBO-0042")
    OSCU_SIGNING_SECRET: str = Field(default="jibutax-oscu-demo-secret-change-me")

    TOT_RATE: str = Field(default="0.015")
    NIL_OBLIGATION_CODE: str = Field(default="7")

    DEFAULT_TRADER_PIN: str = Field(default="A012345678W")
    DEFAULT_TRADER_NAME: str = Field(default="JibuTax Demo Trader")

    # ElevenLabs Voice AI
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None)
    ELEVENLABS_AGENT_ID: Optional[str] = Field(default=None)
    WEBHOOK_SECRET: str = Field(default="")

    # SMS Gateway (Africa's Talking / Twilio / Mock)
    SMS_PROVIDER: str = Field(default="mock")
    AFRICASTALKING_USERNAME: Optional[str] = Field(default=None)
    AFRICASTALKING_API_KEY: Optional[str] = Field(default=None)
    AFRICASTALKING_SENDER_ID: str = Field(default="JIBUTAX")

    # WhatsApp QR delivery
    WHATSAPP_PROVIDER: str = Field(default="mock")
    WHATSAPP_VERIFY_TOKEN: str = Field(default="jibutax_whatsapp_verify")
    WHATSAPP_META_TOKEN: Optional[str] = Field(default=None)
    WHATSAPP_META_PHONE_NUMBER_ID: Optional[str] = Field(default=None)
    WHATSAPP_META_API_VERSION: str = Field(default="v21.0")
    TWILIO_ACCOUNT_SID: Optional[str] = Field(default=None)
    TWILIO_AUTH_TOKEN: Optional[str] = Field(default=None)
    TWILIO_WHATSAPP_FROM: str = Field(default="whatsapp:+14155238886")

    # Lowercase compatibility properties
    @property
    def environment(self) -> str:
        return self.ENVIRONMENT.lower()

    @property
    def host(self) -> str:
        return self.HOST

    @property
    def port(self) -> int:
        return self.PORT

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def cors_origins(self) -> List[str]:
        return self.CORS_ORIGINS

    @property
    def public_base_url(self) -> str:
        return self.PUBLIC_BASE_URL

    @property
    def kra_environment(self) -> str:
        return self.KRA_ENVIRONMENT.lower()

    @property
    def kra_api_base_url(self) -> str:
        return self.KRA_BASE_URL

    @property
    def kra_api_key(self) -> Optional[str]:
        return self.KRA_API_TOKEN

    @property
    def kra_oscu_device_id(self) -> str:
        return self.KRA_OSCU_DEVICE_ID

    @property
    def oscu_signing_secret(self) -> str:
        return self.OSCU_SIGNING_SECRET

    @property
    def default_trader_pin(self) -> str:
        return self.DEFAULT_TRADER_PIN

    @property
    def default_trader_name(self) -> str:
        return self.DEFAULT_TRADER_NAME

    @property
    def gemini_api_key(self) -> Optional[str]:
        return self.GEMINI_API_KEY

    @property
    def elevenlabs_api_key(self) -> Optional[str]:
        return self.ELEVENLABS_API_KEY

    @property
    def elevenlabs_agent_id(self) -> Optional[str]:
        return self.ELEVENLABS_AGENT_ID

    @property
    def webhook_secret(self) -> str:
        return self.WEBHOOK_SECRET

    @property
    def sms_provider(self) -> str:
        return self.SMS_PROVIDER.lower()

    @property
    def africastalking_username(self) -> Optional[str]:
        return self.AFRICASTALKING_USERNAME

    @property
    def africastalking_api_key(self) -> Optional[str]:
        return self.AFRICASTALKING_API_KEY

    @property
    def africastalking_sender_id(self) -> str:
        return self.AFRICASTALKING_SENDER_ID

    @property
    def whatsapp_provider(self) -> str:
        return self.WHATSAPP_PROVIDER.lower()

    @property
    def whatsapp_verify_token(self) -> str:
        return self.WHATSAPP_VERIFY_TOKEN

    @property
    def whatsapp_meta_token(self) -> Optional[str]:
        return self.WHATSAPP_META_TOKEN

    @property
    def whatsapp_meta_phone_number_id(self) -> Optional[str]:
        return self.WHATSAPP_META_PHONE_NUMBER_ID

    @property
    def whatsapp_meta_api_version(self) -> str:
        return self.WHATSAPP_META_API_VERSION

    @property
    def twilio_account_sid(self) -> Optional[str]:
        return self.TWILIO_ACCOUNT_SID

    @property
    def twilio_auth_token(self) -> Optional[str]:
        return self.TWILIO_AUTH_TOKEN

    @property
    def twilio_whatsapp_from(self) -> str:
        return self.TWILIO_WHATSAPP_FROM


@lru_cache
def get_settings() -> Settings:
    return Settings()
