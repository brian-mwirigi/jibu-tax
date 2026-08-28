"""
File: backend/app/agent/nodes/__init__.py
Description:
    LangGraph Nodes Package (Role 4).
    Exports:
    - extract_sale_node: Google Gemini entity extraction.
    - validate_pin_node: KRA PIN check and registry resolution.
    - should_route_after_validation: Conditional edge router.
    - calculate_tax_node: Pure Python deterministic VAT calculation.
    - clarify_pin_node: Verbal re-prompt generator.
"""

from app.agent.nodes.extraction import extract_sale_node
from app.agent.nodes.validation import validate_pin_node, should_route_after_validation
from app.agent.nodes.tax_math import calculate_tax_node
from app.agent.nodes.clarification import clarify_pin_node

__all__ = [
    "extract_sale_node",
    "validate_pin_node",
    "should_route_after_validation",
    "calculate_tax_node",
    "clarify_pin_node",
]
