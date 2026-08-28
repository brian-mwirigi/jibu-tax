"""
File: backend/app/agent/nodes/tax_math.py
Description:
    Node 3: Deterministic Tax Calculation Node (Role 4).
    Pure Python execution (Zero AI) ensuring absolute arithmetic accuracy for KRA VAT compliance.
"""

import re
from typing import Dict, Any
from app.agent.state import JibuTaxState, TaxBreakdown

# First Schedule VAT Exempt (unprocessed agricultural products)
EXEMPT_COMMODITIES = [
    "mahindi", "maize", "corn",
    "sukuma", "cabbage", "spinach", "mboga",
    "nyanya", "tomatoes", "tomato",
    "viazi", "potatoes", "waru",
    "kitunguu", "onions",
    "maziwa", "milk",
    "mayai", "eggs",
    "maharagwe", "beans",
    "avocado", "fresh fruits", "fresh vegetables"
]

# Second Schedule Zero-Rated (0% VAT)
ZERO_RATED_COMMODITIES = [
    "fertilizer", "mbolea",
    "certified seeds", "mbegu",
    "export"
]


def calculate_tax_node(state: JibuTaxState) -> Dict[str, Any]:
    """
    Node 3 Handler:
    Performs non-AI deterministic tax calculation and generates verbal feedback strings.
    """
    sale = state.get("sale")
    buyer = state.get("buyer_validation")

    if not sale:
        return {
            "tax_breakdown": None,
            "spoken_summary": "Hitilafu imetokea. Taarifa za mauzo hazikupatikana.",
            "ready_for_filing": False,
            "call_status": "FAILED",
        }

    item_name = sale.item_name.lower().strip()
    gross_total = round(sale.quantity * sale.unit_price, 2)

    # Classify commodity deterministically
    is_exempt = any(re.search(rf"\b{re.escape(k)}\b", item_name) for k in EXEMPT_COMMODITIES)
    is_zero_rated = any(re.search(rf"\b{re.escape(k)}\b", item_name) for k in ZERO_RATED_COMMODITIES)

    if is_exempt:
        classification = "EXEMPT"
        taxable_amount = 0.0
        vat_amount = 0.0
        exempt_amount = gross_total
        zero_rated_amount = 0.0
        vat_text_sw = "Bidhaa hii haina kodi ya VAT chini ya sheria za KRA."
        vat_text_en = "This commodity is VAT-exempt under KRA regulations."
    elif is_zero_rated:
        classification = "ZERO_RATED"
        taxable_amount = 0.0
        vat_amount = 0.0
        exempt_amount = 0.0
        zero_rated_amount = gross_total
        vat_text_sw = "Bidhaa hii ina kiwango cha asilimia sifuri cha VAT."
        vat_text_en = "This commodity is zero-rated for VAT."
    else:
        classification = "STANDARD_16"
        taxable_amount = round(gross_total / 1.16, 2)
        vat_amount = round(gross_total - taxable_amount, 2)
        exempt_amount = 0.0
        zero_rated_amount = 0.0
        vat_text_sw = f"Kodi ya VAT ya asilimia 16 ni shilingi {vat_amount:,.2f}."
        vat_text_en = f"16% VAT is KES {vat_amount:,.2f}."

    breakdown = TaxBreakdown(
        taxable_amount=taxable_amount,
        vat_amount=vat_amount,
        exempt_amount=exempt_amount,
        zero_rated_amount=zero_rated_amount,
        grand_total=gross_total,
        classification=classification,
    )

    buyer_name = buyer.legal_name if (buyer and buyer.legal_name) else "Mteja"

    # Spoken summary for ElevenLabs
    spoken_summary = (
        f"Nimepokea mauzo yako ya {sale.quantity} {sale.unit_of_measure} ya {sale.item_name} "
        f"kwa {buyer_name}, jumla ni shilingi {gross_total:,.2f}. {vat_text_sw} "
        f"Je, nikamilishe kutuma eTIMS receipt kwa nambari yako ya simu?"
    )

    return {
        "tax_breakdown": breakdown,
        "spoken_summary": spoken_summary,
        "ready_for_filing": True,
        "call_status": "READY_FOR_OSCU",
    }
