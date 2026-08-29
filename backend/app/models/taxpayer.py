"""
KRA taxpayer registry: PIN is captured once on the first voice call and
permanently linked to the caller's phone number.

After enrollment, lookup is by MSISDN only — the voice agent must not ask
for the trader's KRA PIN again.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Session, SQLModel, select

KRA_PIN_REGEX = re.compile(r"^[AP][0-9]{9}[A-Z]$", re.IGNORECASE)
PIN_IN_SPEECH_REGEX = re.compile(r"\b([AP](?:\s*[0-9]){9}\s*[A-Z])\b", re.IGNORECASE)

TRADER_PIN_CUES = re.compile(
    r"\b(pin\s+yangu|pin\s+wangu|pin\s+yake\s+yang|kra\s+pin\s+yangu|"
    r"my\s+pin|my\s+kra|trader\s+pin|seller\s+pin|pin\s+yangu)\b",
    re.IGNORECASE,
)
SALE_SPEECH_CUES = re.compile(
    r"\b(nimeuz|niluz|sold|uza|mahindi|gunia|shilingi|bei|quantity|"
    r"hotel|mteja|mnunuzi|cabbages|sukuma|viazi)\b",
    re.IGNORECASE,
)

FIRST_CALL_PIN_PROMPT_SW = (
    "Karibu JibuTax. Hii ni simu yako ya kwanza. "
    "Tafadhali nitajie KRA PIN yako, herufi kwa herufi, ili nihifadhi pamoja na nambari hii ya simu. "
    "Baada ya hapo sitauliza PIN tena."
)
FIRST_CALL_PIN_PROMPT_EN = (
    "Welcome to JibuTax. This is your first call. "
    "Please tell me your KRA PIN, letter by letter, so I can save it against this phone number. "
    "I will not ask for your PIN on future calls."
)


class TaxpayerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class TaxpayerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    COMPANY = "COMPANY"
    PARASTOTAL = "PARASTOTAL"


class Taxpayer(SQLModel, table=True):
    __tablename__ = "taxpayers"
    __table_args__ = (UniqueConstraint("phone", name="uq_taxpayers_phone"),)

    pin: str = Field(primary_key=True, max_length=11, index=True)
    legal_name: str
    trading_name: Optional[str] = None
    status: TaxpayerStatus = Field(default=TaxpayerStatus.ACTIVE)
    taxpayer_type: TaxpayerType = Field(default=TaxpayerType.INDIVIDUAL)
    vat_registered: bool = False
    etims_onboarded: bool = False
    tot_registered: bool = True
    phone: Optional[str] = Field(default=None, index=True, max_length=20)
    pin_linked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def normalize_phone(raw: Optional[str]) -> str:
        """Canonical Kenyan MSISDN: +2547XXXXXXXX."""
        if not raw:
            return ""
        digits = re.sub(r"\D", "", raw)
        if digits.startswith("254") and len(digits) >= 12:
            return "+" + digits
        if digits.startswith("0") and len(digits) == 10:
            return "+254" + digits[1:]
        if digits.startswith("7") and len(digits) == 9:
            return "+254" + digits
        if digits:
            return "+" + digits if not raw.strip().startswith("+") else "+" + digits
        return raw.strip()

    @staticmethod
    def normalize_pin(raw: Optional[str]) -> str:
        if not raw:
            return ""
        return re.sub(r"\s+", "", raw).upper()

    @classmethod
    def is_valid_pin(cls, pin: str) -> bool:
        return bool(KRA_PIN_REGEX.match(cls.normalize_pin(pin)))

    @classmethod
    def pins_in_speech(cls, transcript: str) -> list[str]:
        found: list[str] = []
        for match in PIN_IN_SPEECH_REGEX.finditer(transcript or ""):
            compact = cls.normalize_pin(match.group(0))
            if cls.is_valid_pin(compact) and compact not in found:
                found.append(compact)
        return found

    @classmethod
    def extract_trader_pin_from_speech(cls, transcript: str) -> Optional[str]:
        """
        First-call enrollment: the trader's own PIN, not the buyer's.

        Prefer a PIN spoken after 'PIN yangu' / 'my PIN'. If the call is an
        enrollment turn and only one PIN is spoken, treat it as the trader's.
        """
        text = transcript or ""
        pins = cls.pins_in_speech(text)
        if not pins:
            return None

        trader_cue = TRADER_PIN_CUES.search(text)
        if trader_cue:
            after = text[trader_cue.end() :]
            after_pins = cls.pins_in_speech(after)
            return (after_pins or pins)[0]

        if len(pins) == 1 and not SALE_SPEECH_CUES.search(text):
            return pins[0]
        return None

    @classmethod
    def get_by_phone(cls, session: Session, phone: str) -> Optional["Taxpayer"]:
        msisdn = cls.normalize_phone(phone)
        if not msisdn:
            return None
        statement = select(cls).where(cls.phone == msisdn)
        return session.exec(statement).first()

    @classmethod
    def get_by_pin(cls, session: Session, pin: str) -> Optional["Taxpayer"]:
        normalized = cls.normalize_pin(pin)
        if not normalized:
            return None
        return session.get(cls, normalized)

    @classmethod
    def first_call_prompt(cls, language: str = "sw") -> str:
        if (language or "sw").lower().startswith("en"):
            return FIRST_CALL_PIN_PROMPT_EN
        return FIRST_CALL_PIN_PROMPT_SW

    def returning_caller_prompt(self, language: str = "sw") -> str:
        if (language or "sw").lower().startswith("en"):
            return (
                f"Welcome back. I already have KRA PIN {self.pin} saved on this phone. "
                "Tell me the sale when you are ready."
            )
        return (
            f"Karibu tena. Tayari nina KRA PIN yako {self.pin} kwenye nambari hii. "
            "Sitauliza PIN tena. Niambie mauzo yako."
        )

    @classmethod
    def link_pin_to_phone(
        cls,
        session: Session,
        *,
        phone: str,
        pin: str,
        legal_name: Optional[str] = None,
        trading_name: Optional[str] = None,
    ) -> "Taxpayer":
        """Persist PIN once and bind it to this MSISDN. Later calls resolve by phone only."""
        msisdn = cls.normalize_phone(phone)
        normalized_pin = cls.normalize_pin(pin)
        if not msisdn:
            raise ValueError("Phone number is required to link a KRA PIN.")
        if not cls.is_valid_pin(normalized_pin):
            raise ValueError(f"Invalid KRA PIN: {pin}")

        existing_phone = cls.get_by_phone(session, msisdn)
        if existing_phone:
            return existing_phone

        existing_pin = cls.get_by_pin(session, normalized_pin)
        now = datetime.now(timezone.utc)
        if existing_pin:
            existing_pin.phone = msisdn
            if not existing_pin.pin_linked_at:
                existing_pin.pin_linked_at = now
            if legal_name:
                existing_pin.legal_name = legal_name
            session.add(existing_pin)
            session.commit()
            session.refresh(existing_pin)
            return existing_pin

        taxpayer = cls(
            pin=normalized_pin,
            legal_name=legal_name or f"Trader {msisdn}",
            trading_name=trading_name,
            phone=msisdn,
            pin_linked_at=now,
        )
        session.add(taxpayer)
        session.commit()
        session.refresh(taxpayer)
        return taxpayer

    @classmethod
    def resolve_for_voice(
        cls,
        session: Session,
        *,
        phone: str,
        transcript: str = "",
        language: str = "sw",
    ) -> dict:
        """
        Voice-call identity gate.

        Returning caller: PIN is already on file for this phone — never ask again.
        First caller: if they just spoke their PIN, store and link it; otherwise
        return the prompt the agent should speak.
        """
        msisdn = cls.normalize_phone(phone)
        enrolled = cls.get_by_phone(session, msisdn)
        if enrolled and enrolled.pin:
            return {
                "known": True,
                "needs_trader_pin": False,
                "just_enrolled": False,
                "taxpayer": enrolled,
                "trader_pin": enrolled.pin,
                "trader_name": enrolled.legal_name,
                "spoken_prompt": None,
            }

        spoken_pin = cls.extract_trader_pin_from_speech(transcript)
        if spoken_pin:
            taxpayer = cls.link_pin_to_phone(session, phone=msisdn, pin=spoken_pin)
            thanks = (
                f"Asante. Nimehifadhi KRA PIN {taxpayer.pin} kwenye nambari {msisdn}. "
                "Sitauliza PIN tena simu zijazo."
            )
            if (language or "sw").lower().startswith("en"):
                thanks = (
                    f"Thank you. I saved KRA PIN {taxpayer.pin} against {msisdn}. "
                    "I will not ask for your PIN on future calls."
                )
            return {
                "known": True,
                "needs_trader_pin": False,
                "just_enrolled": True,
                "taxpayer": taxpayer,
                "trader_pin": taxpayer.pin,
                "trader_name": taxpayer.legal_name,
                "spoken_prompt": thanks,
            }

        return {
            "known": False,
            "needs_trader_pin": True,
            "just_enrolled": False,
            "taxpayer": None,
            "trader_pin": None,
            "trader_name": None,
            "spoken_prompt": cls.first_call_prompt(language),
        }
