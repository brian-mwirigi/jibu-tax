"""Unit tests for TOT / NIL payload construction and month-end routing."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401 — register all SQLModel tables
from app.models.tax_return import FilingStatus, ReturnKind
from app.models.taxpayer import Taxpayer
from app.services.filing_engine import (
    FilingEngine,
    build_nil_payload,
    build_tot_payload,
    previous_tax_period,
)
from app.services.ledger_service import LedgerService, compute_entry_hash, GENESIS_HASH


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_previous_period_is_prior_calendar_month():
    assert previous_tax_period(date(2026, 8, 18)) == (2026, 7)
    assert previous_tax_period(date(2026, 1, 18)) == (2025, 12)


def test_tot_payload_matches_kra_nested_contract():
    payload = build_tot_payload("p051234567a", 2026, 7, Decimal("450000.00"))
    assert payload == {
        "TAXPAYERDETAILS": {
            "TaxpayerPIN": "P051234567A",
            "Month": "07",
            "Year": "2026",
            "GrossTurnover": 450000.00,
        }
    }


def test_nil_payload_uses_tot_obligation_code():
    payload = build_nil_payload("A012345678W", 2026, 7, "7")
    assert payload == {
        "TAXPAYERDETAILS": {
            "TaxpayerPIN": "A012345678W",
            "ObligationCode": "7",
            "Month": "07",
            "Year": "2026",
        }
    }


def test_ledger_hash_chain_and_idempotent_invoice():
    session = _session()
    service = LedgerService(session)
    first = service.append_successful_transaction(
        trader_pin="A012345678W",
        trader_name="JibuTax Demo Trader",
        invoice_number="INV-2026-00001",
        grand_total=Decimal("1160.00"),
        taxable_amount=Decimal("1000.00"),
        vat_amount=Decimal("160.00"),
        posted_at=datetime(2026, 7, 4, tzinfo=timezone.utc),
    )
    assert first.sequence == 1
    assert first.prev_hash == GENESIS_HASH
    assert first.entry_hash == compute_entry_hash(GENESIS_HASH, first.transaction_payload)

    second = service.append_successful_transaction(
        trader_pin="A012345678W",
        trader_name="JibuTax Demo Trader",
        invoice_number="INV-2026-00002",
        grand_total=Decimal("2320.00"),
        taxable_amount=Decimal("2000.00"),
        vat_amount=Decimal("320.00"),
        posted_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
    )
    assert second.sequence == 2
    assert second.prev_hash == first.entry_hash

    duplicate = service.append_successful_transaction(
        trader_pin="A012345678W",
        trader_name="JibuTax Demo Trader",
        invoice_number="INV-2026-00001",
        grand_total=Decimal("9999.00"),
        taxable_amount=Decimal("1.00"),
        vat_amount=Decimal("1.00"),
    )
    assert duplicate.id == first.id
    session.close()


def test_month_end_files_tot_when_ledger_has_sales():
    session = _session()
    session.add(
        Taxpayer(pin="A012345678W", legal_name="JibuTax Demo Trader", tot_registered=True)
    )
    session.commit()
    LedgerService(session).append_successful_transaction(
        trader_pin="A012345678W",
        trader_name="JibuTax Demo Trader",
        invoice_number="INV-2026-00010",
        grand_total=Decimal("450000.00"),
        taxable_amount=Decimal("387931.03"),
        vat_amount=Decimal("62068.97"),
        posted_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )

    filing = FilingEngine(session).file_period("A012345678W", "JibuTax Demo Trader", 2026, 7)
    assert filing.return_kind == ReturnKind.TOT
    assert filing.status == FilingStatus.FILED
    assert filing.gross_turnover == Decimal("450000.00")
    assert filing.ack_number is not None
    assert '"GrossTurnover":450000.0' in filing.kra_payload.replace(" ", "")
    session.close()


def test_month_end_files_nil_when_database_has_no_sales():
    session = _session()
    session.add(
        Taxpayer(pin="A012345678W", legal_name="JibuTax Demo Trader", tot_registered=True)
    )
    session.commit()

    filings = FilingEngine(session).run_month_end(as_of=date(2026, 8, 18))
    assert len(filings) == 1
    assert filings[0].return_kind == ReturnKind.NIL
    assert filings[0].status == FilingStatus.FILED
    assert filings[0].tax_period_year == 2026
    assert filings[0].tax_period_month == 7
    assert filings[0].invoice_count == 0
    session.close()


def test_normalize_render_postgres_url():
    from app.database import normalize_database_url

    assert normalize_database_url("postgres://u:p@h:5432/db").startswith("postgresql+psycopg2://")
    assert normalize_database_url("postgresql://u:p@h:5432/db").startswith("postgresql+psycopg2://")
