"""
File: backend/app/api/v1/agent.py
Description:
    FastAPI Router for Role 4: LangGraph Multi-Agent Brain.
    Exposes the compiled StateGraph via HTTP so Role 2 (ElevenLabs voice agent)
    and Role 6 (WebSocket / Telemetry frontend) can run turns and inspect state.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from sqlmodel import Session

from app.agent.graph import jibutax_agent
from app.agent.state import ExtractedSale, BuyerValidationResult, TaxBreakdown
from app.database import engine
from app.models.taxpayer import Taxpayer

router = APIRouter(prefix="/agent", tags=["LangGraph Agent Brain"])
logger = logging.getLogger(__name__)


class AgentInvokeRequest(BaseModel):
    caller_phone: str = Field(
        min_length=10,
        max_length=20,
        description="Trader's phone number used as thread_id for state checkpointing (e.g. '+254712345678')"
    )
    transcript: str = Field(
        min_length=1,
        max_length=20000,
        description="Trader's spoken audio transcript from ElevenLabs"
    )
    language: Optional[str] = Field(
        default="sw",
        pattern="^(sw|en|sheng)$",
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
    trader_pin: Optional[str] = None
    trader_name: Optional[str] = None
    needs_trader_pin: bool = False


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
    language = payload.language or "sw"

    identity = {
        "needs_trader_pin": False,
        "just_enrolled": False,
        "trader_pin": None,
        "trader_name": None,
        "spoken_prompt": None,
    }
    try:
        with Session(engine) as session:
            identity = Taxpayer.resolve_for_voice(
                session,
                phone=payload.caller_phone,
                transcript=payload.transcript,
                language=language,
            )
    except Exception:
        identity = identity

    if identity.get("needs_trader_pin"):
        return AgentInvokeResponse(
            caller_phone=Taxpayer.normalize_phone(payload.caller_phone) or payload.caller_phone,
            call_status="NEEDS_TRADER_PIN",
            ready_for_filing=False,
            spoken_summary=identity.get("spoken_prompt") or Taxpayer.first_call_prompt(language),
            needs_trader_pin=True,
        )

    input_state = {
        "caller_phone": payload.caller_phone,
        "transcript": payload.transcript,
        "language": language,
        "trader_pin": identity.get("trader_pin"),
        "trader_name": identity.get("trader_name"),
        "needs_trader_pin": False,
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
        spoken = final_state.get("spoken_summary") or ""
        if identity.get("just_enrolled") and identity.get("spoken_prompt"):
            spoken = f"{identity['spoken_prompt']} {spoken}".strip()
        return AgentInvokeResponse(
            caller_phone=payload.caller_phone,
            call_status=final_state.get("call_status", "COMPLETED"),
            ready_for_filing=final_state.get("ready_for_filing", False),
            spoken_summary=spoken or None,
            sale=final_state.get("sale"),
            buyer_validation=final_state.get("buyer_validation"),
            tax_breakdown=final_state.get("tax_breakdown"),
            extraction_error=final_state.get("extraction_error"),
            trader_pin=identity.get("trader_pin"),
            trader_name=identity.get("trader_name"),
            needs_trader_pin=False,
        )
    except Exception:
        logger.exception("LangGraph agent invocation failed")
        raise HTTPException(
            status_code=500,
            detail="Agent invocation failed",
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
    except Exception:
        logger.exception("Failed to inspect agent checkpoint")
        raise HTTPException(
            status_code=500,
            detail="Failed to inspect checkpoint",
        )


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(default="21m00Tcm4TlvDq8ikWAM")


@router.post("/speak")
def synthesize_speech(payload: SpeakRequest):
    """
    Synthesize high-quality natural Swahili/English speech using ElevenLabs API.
    Streams back MP3 audio directly to the frontend.
    """
    from fastapi.responses import Response
    import requests
    from app.config import get_settings

    settings = get_settings()
    eleven_key = settings.ELEVENLABS_API_KEY
    if not eleven_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")

    voice_id = payload.voice_id or "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": eleven_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": payload.text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.error("ElevenLabs TTS error (%d): %s", resp.status_code, resp.text)
            raise HTTPException(status_code=resp.status_code, detail=f"ElevenLabs TTS failed: {resp.text}")
        return Response(content=resp.content, media_type="audio/mpeg")
    except requests.RequestException as e:
        logger.exception("ElevenLabs request failed")
        raise HTTPException(status_code=502, detail=f"ElevenLabs connection failed: {str(e)}")
