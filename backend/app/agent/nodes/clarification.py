"""
File: backend/app/agent/nodes/clarification.py
Description:
    Clarification Node (Role 4).
    Generates verbal reprompt messages when the trader's speech has missing or invalid PINs.
"""

from typing import Dict, Any
from app.agent.state import JibuTaxState

def clarify_pin_node(state: JibuTaxState) -> Dict[str, Any]:
    """
    Constructs a polite, clear verbal reprompt when buyer PIN is invalid or missing.
    """
    validation = state.get("buyer_validation")
    error_msg = validation.error_message if validation else "Tafadhali taja tena KRA PIN ya mteja wako."
    retry_count = state.get("retry_count", 1)

    spoken_prompt = (
        f"Samahani, {error_msg} "
        f"Tafadhali nitajie KRA PIN (kwa mfano P 0 5 1 2 3 4 5 6 7 M)."
    )

    return {
        "spoken_summary": spoken_prompt,
        "call_status": "NEEDS_CLARIFICATION",
        "ready_for_filing": False,
    }
