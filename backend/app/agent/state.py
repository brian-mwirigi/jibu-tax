"""
File: backend/app/agent/state.py
Description:
    Role 4: LangGraph State Contract (Memory).
    Defines the rigid TypedDict and Pydantic schemas that pass between
    the DAG nodes: Extraction (Claude 3.5) -> Validation (KRA) -> Deterministic Math.
"""

from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ExtractedSale(BaseModel):
    """Structured sale entities extracted from trader voice audio."""
    item_name: str = Field(
        ...,
        description="Commodity or service sold (e.g. 'mahindi', 'cabbages', 'cement', 'transport')"
    )
    quantity: float = Field(
        ...,
        gt=0,
        description="Quantity of commodity sold (e.g. 50, 10.5)"
    )
    unit_price: float = Field(
        ...,
        ge=0,
        description="Price per unit in Kenya Shillings (KES)"
    )
    buyer_pin: Optional[str] = Field(
        default=None,
        description="Buyer's KRA PIN if mentioned (e.g. 'P051234567M')"
    )
    unit_of_measure: Optional[str] = Field(
        default="units",
        description="Unit of measurement (e.g. 'bags', 'kg', 'crates', 'pieces')"
    )


class BuyerValidationResult(BaseModel):
    """Zero-Trust verification output for the buyer's KRA PIN."""
    is_valid: bool = Field(default=False)
    pin: str
    legal_name: Optional[str] = None
    trading_name: Optional[str] = None
    vat_registered: bool = False
    etims_onboarded: bool = False
    error_message: Optional[str] = None


class TaxBreakdown(BaseModel):
    """Deterministic, zero-AI tax calculation breakdown."""
    taxable_amount: float = 0.0
    vat_amount: float = 0.0
    exempt_amount: float = 0.0
    zero_rated_amount: float = 0.0
    grand_total: float = 0.0
    classification: str = "STANDARD_16"  # STANDARD_16, EXEMPT, ZERO_RATED


class JibuTaxState(TypedDict):
    """
    Central State passing through LangGraph nodes.
    Maintained and checkpointed via MemorySaver(thread_id=caller_phone).
    """
    # Session Context & Identity
    caller_phone: str                      # Trader's MSISDN used as thread_id for checkpointing
    transcript: str                        # Raw voice transcript from ElevenLabs audio
    language: str                          # Detected speech language: 'sw' (Swahili), 'en', or 'sheng'
    
    # Node 1: Extraction Outputs (Claude 3.5 Sonnet)
    sale: Optional[ExtractedSale]
    extraction_error: Optional[str]
    
    # Node 2: Validation Outputs (KRA Checker)
    buyer_validation: Optional[BuyerValidationResult]
    retry_count: int                       # Retry counter for invalid / unparsed PINs
    
    # Node 3: Deterministic Tax Math Outputs
    tax_breakdown: Optional[TaxBreakdown]
    spoken_summary: Optional[str]          # Exact verbal response for ElevenLabs to speak back
    
    # Final Routing State
    ready_for_filing: bool
    call_status: str                       # 'IN_PROGRESS', 'NEEDS_CLARIFICATION', 'READY_FOR_OSCU', 'COMPLETED', 'FAILED'
