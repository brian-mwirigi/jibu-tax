"""
End-of-month TOT / NIL filing engine.

On the 18th, scan the immutable ledger for the *previous* calendar month (KRA due
date is the 20th of the following month). Sales → TOT Return Filing API. No sales
→ NIL Return Filling API so the trader is not fined for a missing return.
"""

from __future__ import annotations

import json
from calendar import month_name
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

import httpx
from sqlmodel import Session, select

from app.config import get_settings
from app.models.tax_return import FilingStatus, ReturnKind, TaxReturnFiling
from app.models.taxpayer import Taxpayer, TaxpayerStatus
from app.services.ledger_service import LedgerService, money

TOT_OBLIGATION_CODE = "7"


def previous_tax_period(as_of: Optional[date] = None) -> tuple[int, int]:
    """Return (year, month) for the period that must be filed on the 18th."""
    today = as_of or datetime.now(timezone.utc).date()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def padded_month(month: int) -> str:
    return f"{month:02d}"


def build_tot_payload(taxpayer_pin: str, year: int, month: int, gross_turnover: Decimal) -> dict[str, Any]:
    """Exact nested JSON body for KRA POST /filing/v1/tot/paymentregistration."""
    return {
        "TAXPAYERDETAILS": {
            "TaxpayerPIN": taxpayer_pin.upper(),
            "Month": padded_month(month),
            "Year": str(year),
            "GrossTurnover": float(money(gross_turnover)),
        }
    }


def build_nil_payload(taxpayer_pin: str, year: int, month: int, obligation_code: str) -> dict[str, Any]:
    """Exact nested JSON body for KRA POST /dtd/return/v1/nil (NIL Return Filling)."""
    return {
        "TAXPAYERDETAILS": {
            "TaxpayerPIN": taxpayer_pin.upper(),
            "ObligationCode": obligation_code,
            "Month": padded_month(month),
            "Year": str(year),
        }
    }


def _tax_payable(gross: Decimal, rate: Decimal) -> Decimal:
    return (money(gross) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FilingEngine:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.ledger = LedgerService(session)
        self.tot_rate = Decimal(self.settings.TOT_RATE)

    def traders_to_file(self) -> list[tuple[str, str]]:
        statement = select(Taxpayer).where(
            Taxpayer.status == TaxpayerStatus.ACTIVE,
            Taxpayer.tot_registered == True,  # noqa: E712
        )
        taxpayers = list(self.session.exec(statement).all())
        if taxpayers:
            return [(row.pin, row.legal_name) for row in taxpayers]
        return [(self.settings.DEFAULT_TRADER_PIN, self.settings.DEFAULT_TRADER_NAME)]

    def existing_filing(self, trader_pin: str, year: int, month: int) -> Optional[TaxReturnFiling]:
        statement = select(TaxReturnFiling).where(
            TaxReturnFiling.trader_pin == trader_pin.upper(),
            TaxReturnFiling.tax_period_year == year,
            TaxReturnFiling.tax_period_month == month,
        )
        return self.session.exec(statement).first()

    def file_period(
        self,
        trader_pin: str,
        trader_name: str,
        year: int,
        month: int,
    ) -> TaxReturnFiling:
        existing = self.existing_filing(trader_pin, year, month)
        if existing and existing.status == FilingStatus.FILED:
            return existing

        aggregates = self.ledger.aggregate_sales(trader_pin, year, month)
        has_sales = aggregates["invoice_count"] > 0 and aggregates["gross_turnover"] > 0

        if has_sales:
            kind = ReturnKind.TOT
            payload = build_tot_payload(trader_pin, year, month, aggregates["gross_turnover"])
            tax_payable = _tax_payable(aggregates["gross_turnover"], self.tot_rate)
            tax_rate = self.tot_rate
        else:
            kind = ReturnKind.NIL
            payload = build_nil_payload(
                trader_pin, year, month, self.settings.NIL_OBLIGATION_CODE or TOT_OBLIGATION_CODE
            )
            tax_payable = money(0)
            tax_rate = Decimal("0.0000")

        record = existing or TaxReturnFiling(
            trader_pin=trader_pin.upper(),
            trader_name=trader_name,
            tax_period_year=year,
            tax_period_month=month,
            return_kind=kind,
            status=FilingStatus.PENDING,
            invoice_count=aggregates["invoice_count"],
            gross_turnover=aggregates["gross_turnover"],
            tax_rate=tax_rate,
            tax_payable=tax_payable,
            kra_payload=json.dumps(payload, separators=(",", ":")),
        )
        if existing:
            record.return_kind = kind
            record.invoice_count = aggregates["invoice_count"]
            record.gross_turnover = aggregates["gross_turnover"]
            record.tax_rate = tax_rate
            record.tax_payable = tax_payable
            record.kra_payload = json.dumps(payload, separators=(",", ":"))
            record.status = FilingStatus.PENDING

        try:
            response_body = self._submit_to_kra(kind, payload)
            record.kra_response = json.dumps(response_body, default=str)
            data = response_body.get("data") or response_body
            record.ack_number = data.get("AckNumber") or data.get("ackNumber")
            record.prn = data.get("PRN") or data.get("prn")
            record.status = FilingStatus.FILED
            record.error_message = None
        except Exception as exc:  # noqa: BLE001 — persist the failure for ops
            record.status = FilingStatus.ERROR
            record.error_message = str(exc)

        record.filed_at = datetime.now(timezone.utc)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def run_month_end(self, as_of: Optional[date] = None) -> list[TaxReturnFiling]:
        year, month = previous_tax_period(as_of)
        results: list[TaxReturnFiling] = []
        for pin, name in self.traders_to_file():
            results.append(self.file_period(pin, name, year, month))
        return results

    def _submit_to_kra(self, kind: ReturnKind, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings
        path = settings.KRA_TOT_PATH if kind == ReturnKind.TOT else settings.KRA_NIL_PATH
        if settings.KRA_ENVIRONMENT == "sandbox" and not settings.KRA_API_TOKEN:
            return self._sandbox_ack(kind, payload)

        url = settings.KRA_BASE_URL.rstrip("/") + path
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if settings.KRA_API_TOKEN:
            headers["Authorization"] = f"Bearer {settings.KRA_API_TOKEN}"

        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    def _sandbox_ack(self, kind: ReturnKind, payload: dict[str, Any]) -> dict[str, Any]:
        details = payload["TAXPAYERDETAILS"]
        pin = details["TaxpayerPIN"]
        month = int(details["Month"])
        year = details["Year"]
        period_label = f"{month_name[month]} {year}"
        if kind == ReturnKind.TOT:
            gross = Decimal(str(details["GrossTurnover"]))
            payable = _tax_payable(gross, self.tot_rate)
            return {
                "success": True,
                "message": "TOT return filed successfully (sandbox)",
                "data": {
                    "AckNumber": f"TOT/ACK/{year}/{pin[-4:]}{details['Month']}",
                    "TaxpayerPIN": pin,
                    "Period": period_label,
                    "GrossTurnover": float(gross),
                    "TaxRate": float(self.tot_rate * 100),
                    "TaxPayable": float(payable),
                    "PRN": f"KRA{year}{details['Month']}{pin[-6:]}",
                    "DueDate": f"{year}-{padded_month(month)}-20",
                    "Status": "Filed",
                },
            }
        return {
            "success": True,
            "message": "NIL return filed successfully (sandbox)",
            "data": {
                "AckNumber": f"NIL/ACK/{year}/{pin[-4:]}{details['Month']}",
                "TaxpayerPIN": pin,
                "ObligationCode": details.get("ObligationCode"),
                "ObligationName": "Turnover Tax (TOT)",
                "Period": period_label,
                "Status": "Filed",
                "FiledAt": datetime.now(timezone.utc).isoformat(),
            },
        }
