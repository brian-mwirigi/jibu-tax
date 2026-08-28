"""
File: backend/app/agent/__init__.py
Description:
    LangGraph Multi-Agent Orchestrator Package (Role 4).
    Contains state definitions, Google Gemini extraction, KRA validation nodes,
    deterministic tax math, and MemorySaver checkpointing.
"""

from app.agent.state import JibuTaxState, ExtractedSale, TaxBreakdown, BuyerValidationResult
from app.agent.graph import build_jibutax_graph, jibutax_agent

__all__ = [
    "JibuTaxState",
    "ExtractedSale",
    "TaxBreakdown",
    "BuyerValidationResult",
    "build_jibutax_graph",
    "jibutax_agent",
]
