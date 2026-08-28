"""
File: backend/app/schemas/tax.py
Description:
    Pydantic Schemas for Deterministic Tax Calculations.
    - TaxClassification: Enum defining tax categories (STANDARD_16, EXEMPT, ZERO_RATED).
    - TaxCalculationItem: Input structure for commodities, quantity, and unit price.
    - TaxCalculationRequest: Batch calculation request wrapper.
    - TaxCalculationResponse: Detailed breakdown of taxable amount, VAT liability, and spoken voice summaries.
"""
