"""
File: backend/app/api/v1/agent.py
Description:
    FastAPI Router for Role 4: LangGraph Multi-Agent Brain.
    Exposes the compiled StateGraph via HTTP so Role 2 (ElevenLabs voice agent)
    and Role 6 (WebSocket / Telemetry frontend) can run turns and inspect state.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.agent.graph import jibutax_agent
from app.agent.state import ExtractedSale, BuyerValidationResult, TaxBreakdown

router = APIRouter(prefix="/agent", tags=["LangGraph Agent Brain"])


class AgentInvokeRequest(BaseModel):
    caller_phone: str = Field(
        ...,
        description="Trader's phone number used as thread_id for state checkpointing (e.g. '+254712345678')"
    )
    transcript: str = Field(
        ...,
        description="Trader's spoken audio transcript from ElevenLabs"
    )
    language: Optional[str] = Field(
        default="sw",
        description="Detected language: 'sw' (Swahili), 'en' (English), or 'sheng'"
    )


class AgentInvokeResponse(BaseModel):
    caller_phone: str
    call_status: str
    ready_for_filing: bool
    spoken_summary: Optional[str] = None
    sale: Optional[ExtractedSale] = None
    buyer_validation: Optional[BuyerValidationResult] = None
    tax_breakdown: Optional[TaxBreakdown] = None
    extraction_error: Optional[str] = None


@router.post("/invoke", response_model=AgentInvokeResponse)
def invoke_agent_turn(payload: AgentInvokeRequest):
    """
    Executes a single conversational turn through the LangGraph multi-agent DAG.
    1. Extracts entities with Google Gemini.
    2. Validates buyer PIN against KRA registry.
    3. Calculates deterministic taxes (16% vs First Schedule exempt).
    4. Formulates Swahili/English verbal response for ElevenLabs text-to-speech.
    """
    thread_config = {"configurable": {"thread_id": payload.caller_phone}}

    input_state = {
        "caller_phone": payload.caller_phone,
        "transcript": payload.transcript,
        "language": payload.language or "sw",
        "sale": None,
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    try:
        final_state = jibutax_agent.invoke(input_state, config=thread_config)
        return AgentInvokeResponse(
            caller_phone=payload.caller_phone,
            call_status=final_state.get("call_status", "COMPLETED"),
            ready_for_filing=final_state.get("ready_for_filing", False),
            spoken_summary=final_state.get("spoken_summary"),
            sale=final_state.get("sale"),
            buyer_validation=final_state.get("buyer_validation"),
            tax_breakdown=final_state.get("tax_breakdown"),
            extraction_error=final_state.get("extraction_error"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph Agent invocation error: {str(e)}"
        )


@router.get("/state/{caller_phone}", response_model=Dict[str, Any])
def get_agent_checkpoint_state(caller_phone: str):
    """
    Retrieves the persisted MemorySaver checkpoint state for a specific trader's phone.
    Enables UI telemetry and mid-call session recovery.
    """
    thread_config = {"configurable": {"thread_id": caller_phone}}
    try:
        state_snapshot = jibutax_agent.get_state(thread_config)
        if not state_snapshot or not state_snapshot.values:
            return {"caller_phone": caller_phone, "state": None, "message": "No active session checkpoint."}
        return {"caller_phone": caller_phone, "state": state_snapshot.values}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect checkpoint: {str(e)}")
