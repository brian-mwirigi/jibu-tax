"""PIN-to-phone enrollment: ask once on the first voice call, never again."""

from sqlmodel import Session, SQLModel, create_engine

from app.models.taxpayer import Taxpayer


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_normalize_kenyan_msisdn():
    assert Taxpayer.normalize_phone("0712345678") == "+254712345678"
    assert Taxpayer.normalize_phone("+254712345678") == "+254712345678"
    assert Taxpayer.normalize_phone("254712345678") == "+254712345678"


def test_first_call_asks_for_pin_second_call_does_not():
    session = _session()
    phone = "0711000001"

    first = Taxpayer.resolve_for_voice(session, phone=phone, transcript="Habari, ninataka kufile.")
    assert first["needs_trader_pin"] is True
    assert first["trader_pin"] is None
    assert "KRA PIN" in first["spoken_prompt"]

    enrolled = Taxpayer.resolve_for_voice(
        session,
        phone=phone,
        transcript="PIN yangu ni A 0 1 2 3 4 5 6 7 8 W",
    )
    assert enrolled["needs_trader_pin"] is False
    assert enrolled["just_enrolled"] is True
    assert enrolled["trader_pin"] == "A012345678W"
    assert Taxpayer.normalize_phone(phone) == enrolled["taxpayer"].phone

    later = Taxpayer.resolve_for_voice(
        session,
        phone="+254711000001",
        transcript="Nimeuza mahindi, PIN yao ni P051234567M",
    )
    assert later["needs_trader_pin"] is False
    assert later["just_enrolled"] is False
    assert later["trader_pin"] == "A012345678W"
    session.close()


def test_sale_transcript_does_not_steal_buyer_pin_as_trader_pin():
    session = _session()
    result = Taxpayer.resolve_for_voice(
        session,
        phone="+254711000099",
        transcript="Nimeuzia Safari Hotel magunia 50 ya mahindi, PIN yao ni P051234567M",
    )
    assert result["needs_trader_pin"] is True
    assert result["trader_pin"] is None
    session.close()
