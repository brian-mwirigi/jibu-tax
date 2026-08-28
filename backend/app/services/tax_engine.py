"""Deterministic Kenya VAT / fuel classification and invoice arithmetic.

The LLM never computes these numbers. Voice extracts item, qty, and unit price.
This module classifies the item and recalculates every shilling.
"""

from __future__ import annotations

import logging
import re
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.tax import (
    TaxBreakdown,
    TaxClassification,
    TaxLineInput,
    TaxLineResult,
)

logger = logging.getLogger(__name__)

MONEY = Decimal("0.01")
MONEY_TOLERANCE = Decimal("1.00")
QTY = Decimal("0.0001")

RATE_STANDARD = Decimal("0.16")
RATE_FUEL = Decimal("0.08")
RATE_NONE = Decimal("0.00")

# More specific classes are checked first so "diesel export" still zero-rates.
_FUEL = ("diesel", "petrol", "gasoline", "kerosene", "paraffin", "fuel", "lpg", "jet")
_ZERO_RATED = ("fertilizer", "fertiliser", "seed", "seeds", "sanitary", "export")
_EXEMPT = (
    "maize",
    "mahindi",
    "milk",
    "maziwa",
    "potato",
    "potatoes",
    "vegetable",
    "vegetables",
    "cabbage",
    "sukuma",
    "tomato",
    "tomatoes",
    "beans",
    "wheat",
    "unga",
)

_HS_CODES = {
    TaxClassification.STANDARD_16: "2523.29.00",
    TaxClassification.FUEL_8: "2710.12.00",
    TaxClassification.EXEMPT: "1005.90.00",
    TaxClassification.ZERO_RATED: "3102.10.00",
}

_RATES = {
    TaxClassification.STANDARD_16: RATE_STANDARD,
    TaxClassification.FUEL_8: RATE_FUEL,
    TaxClassification.EXEMPT: RATE_NONE,
    TaxClassification.ZERO_RATED: RATE_NONE,
}

_SCHEDULE = {
    TaxClassification.STANDARD_16: "Standard rated (VAT 16%)",
    TaxClassification.FUEL_8: "Petroleum (VAT 8%)",
    TaxClassification.EXEMPT: "First Schedule VAT exempt",
    TaxClassification.ZERO_RATED: "Second Schedule zero-rated",
}


class TaxValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def qty(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(QTY, rounding=ROUND_HALF_UP)


def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in keywords)


def classify_item(description: str) -> TaxClassification:
    if _has_keyword(description, _ZERO_RATED):
        return TaxClassification.ZERO_RATED
    if _has_keyword(description, _FUEL):
        return TaxClassification.FUEL_8
    if _has_keyword(description, _EXEMPT):
        return TaxClassification.EXEMPT
    return TaxClassification.STANDARD_16


def _line_subtotal(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return money(qty(quantity) * unit_price)


def calculate_line(item: TaxLineInput) -> TaxLineResult:
    tax_class = classify_item(item.description)
    rate = _RATES[tax_class]
    taxable = _line_subtotal(item.quantity, item.unit_price)

    if item.claimed_line_total is not None:
        claimed = money(item.claimed_line_total)
        if abs(claimed - taxable) > MONEY_TOLERANCE:
            raise TaxValidationError(
                "MATH_MISMATCH",
                f"Line total for '{item.description}' does not match quantity × unit price "
                f"({item.quantity} × {item.unit_price} = {taxable}, claimed {claimed}). "
                "Please confirm the amount.",
            )

    tax_amount = money(taxable * rate)
    return TaxLineResult(
        description=item.description.strip(),
        hs_code=(item.hs_code or _HS_CODES[tax_class]),
        quantity=qty(item.quantity),
        unit_price=item.unit_price,
        tax_class=tax_class,
        tax_rate=rate,
        taxable_amount=taxable,
        tax_amount=tax_amount,
        line_total=money(taxable + tax_amount),
        schedule=_SCHEDULE[tax_class],
    )


def _format_kes(value: Decimal) -> str:
    return f"{money(value):,.2f}"


def _spoken_summaries(breakdown_lines: list[TaxLineResult], grand: Decimal, vat: Decimal) -> tuple[str, str]:
    if len(breakdown_lines) == 1:
        line = breakdown_lines[0]
        en = (
            f"{line.quantity} {line.description} classified as {line.schedule}. "
            f"VAT {_format_kes(line.tax_amount)} shillings. Total {_format_kes(line.line_total)} shillings."
        )
        sw = (
            f"{line.quantity} {line.description}, {line.schedule}. "
            f"Kodi shilingi {_format_kes(line.tax_amount)}. Jumla shilingi {_format_kes(line.line_total)}."
        )
        return en, sw

    en = (
        f"{len(breakdown_lines)} items. VAT {_format_kes(vat)} shillings. "
        f"Invoice total {_format_kes(grand)} shillings."
    )
    sw = (
        f"Bidhaa {len(breakdown_lines)}. Kodi shilingi {_format_kes(vat)}. "
        f"Jumla ya ankara shilingi {_format_kes(grand)}."
    )
    return en, sw


def calculate_invoice(
    items: list[TaxLineInput],
    claimed_grand_total: Decimal | None = None,
) -> TaxBreakdown:
    if not items:
        raise TaxValidationError("EMPTY_ITEMS", "An invoice needs at least one item.")

    lines = [calculate_line(item) for item in items]

    standard_amount = money(sum((ln.taxable_amount for ln in lines if ln.tax_class == TaxClassification.STANDARD_16), Decimal("0")))
    standard_vat = money(sum((ln.tax_amount for ln in lines if ln.tax_class == TaxClassification.STANDARD_16), Decimal("0")))
    fuel_amount = money(sum((ln.taxable_amount for ln in lines if ln.tax_class == TaxClassification.FUEL_8), Decimal("0")))
    fuel_tax = money(sum((ln.tax_amount for ln in lines if ln.tax_class == TaxClassification.FUEL_8), Decimal("0")))
    exempt_amount = money(sum((ln.taxable_amount for ln in lines if ln.tax_class == TaxClassification.EXEMPT), Decimal("0")))
    zero_amount = money(sum((ln.taxable_amount for ln in lines if ln.tax_class == TaxClassification.ZERO_RATED), Decimal("0")))
    total_vat = money(standard_vat + fuel_tax)
    grand = money(sum((ln.line_total for ln in lines), Decimal("0")))

    if claimed_grand_total is not None:
        claimed = money(claimed_grand_total)
        if abs(claimed - grand) > MONEY_TOLERANCE:
            raise TaxValidationError(
                "MATH_MISMATCH",
                f"Claimed invoice total {claimed} does not match calculated total {grand}. "
                "Please confirm the amount with the trader.",
            )

    spoken_en, spoken_sw = _spoken_summaries(lines, grand, total_vat)
    logger.info(
        "tax_calculated items=%s grand=%s vat=%s standard=%s fuel=%s exempt=%s zero=%s",
        len(lines),
        grand,
        total_vat,
        standard_amount,
        fuel_amount,
        exempt_amount,
        zero_amount,
    )
    return TaxBreakdown(
        lines=lines,
        total_standard_amount=standard_amount,
        total_standard_vat=standard_vat,
        total_fuel_amount=fuel_amount,
        total_fuel_tax=fuel_tax,
        total_exempt_amount=exempt_amount,
        total_zero_rated_amount=zero_amount,
        total_vat_amount=total_vat,
        grand_total=grand,
        spoken_en=spoken_en,
        spoken_sw=spoken_sw,
    )
