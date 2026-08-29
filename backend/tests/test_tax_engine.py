"""Deterministic tax engine: rates, classification, and math-mismatch rejects."""

from decimal import Decimal

import pytest

from app.schemas.tax import TaxClassification, TaxLineInput
from app.services.tax_engine import TaxValidationError, calculate_invoice, classify_item


def _item(description: str, quantity, unit_price, claimed=None) -> TaxLineInput:
    return TaxLineInput(
        description=description,
        quantity=Decimal(str(quantity)),
        unit_price=Decimal(str(unit_price)),
        claimed_line_total=None if claimed is None else Decimal(str(claimed)),
    )


def test_cement_is_standard_16_percent():
    result = calculate_invoice([_item("100 bags of cement", 100, 2000)])
    assert result.lines[0].tax_class == TaxClassification.STANDARD_16
    assert result.total_standard_amount == Decimal("200000.00")
    assert result.total_standard_vat == Decimal("32000.00")
    assert result.grand_total == Decimal("232000.00")


def test_maize_is_vat_exempt():
    result = calculate_invoice([_item("maize 90kg bags", 10, 4000)])
    assert result.lines[0].tax_class == TaxClassification.EXEMPT
    assert result.total_exempt_amount == Decimal("40000.00")
    assert result.total_vat_amount == Decimal("0.00")
    assert result.grand_total == Decimal("40000.00")


def test_fertilizer_is_zero_rated():
    result = calculate_invoice([_item("NPK fertilizer", 5, 2500)])
    assert result.lines[0].tax_class == TaxClassification.ZERO_RATED
    assert result.total_zero_rated_amount == Decimal("12500.00")
    assert result.total_vat_amount == Decimal("0.00")


def test_diesel_is_fuel_8_percent():
    result = calculate_invoice([_item("diesel litres", 50, 200)])
    assert result.lines[0].tax_class == TaxClassification.FUEL_8
    assert result.total_fuel_amount == Decimal("10000.00")
    assert result.total_fuel_tax == Decimal("800.00")
    assert result.grand_total == Decimal("10800.00")


def test_export_overrides_fuel_to_zero_rated():
    assert classify_item("export diesel") == TaxClassification.ZERO_RATED


def test_milkshake_does_not_match_milk_exempt():
    assert classify_item("chocolate milkshake") == TaxClassification.STANDARD_16


def test_line_total_mismatch_is_rejected():
    with pytest.raises(TaxValidationError) as exc:
        calculate_invoice([_item("cement", 100, 2000, claimed=150000)])
    assert exc.value.code == "MATH_MISMATCH"


def test_claimed_grand_total_mismatch_is_rejected():
    with pytest.raises(TaxValidationError) as exc:
        calculate_invoice(
            [_item("cement", 100, 2000)],
            claimed_grand_total=Decimal("200000"),
        )
    assert exc.value.code == "MATH_MISMATCH"


def test_mixed_invoice_sums_per_class():
    result = calculate_invoice(
        [
            _item("cement bags", 10, 1000),
            _item("fresh milk", 20, 50),
            _item("fertilizer", 2, 1500),
        ]
    )
    assert result.total_standard_amount == Decimal("10000.00")
    assert result.total_standard_vat == Decimal("1600.00")
    assert result.total_exempt_amount == Decimal("1000.00")
    assert result.total_zero_rated_amount == Decimal("3000.00")
    assert result.grand_total == Decimal("15600.00")


def test_empty_items_rejected():
    with pytest.raises(TaxValidationError) as exc:
        calculate_invoice([])
    assert exc.value.code == "EMPTY_ITEMS"


def test_spoken_summaries_include_totals():
    result = calculate_invoice([_item("cement", 100, 2000)])
    assert "232,000.00" in result.spoken_en
    assert "232,000.00" in result.spoken_sw
