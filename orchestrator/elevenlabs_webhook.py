"""
ElevenLabs Real-Time Webhook Integration for JibuTax
Receives voice transcript chunks and manages async state transitions.

Webhook Flow:
1. ElevenLabs streams user_transcript events (partial + final)
2. We extract entities, update conversation context
3. We decide next action (ask for more info, validate, file receipt)
4. We return bot response for ElevenLabs to speak

Key: Non-blocking validation. Backend call happens asynchronously.
      Bot can say "let me check that PIN" while validation runs in background.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import json
import asyncio
from datetime import datetime
from enum import Enum

from conversation_state_machine import (
    ConversationOrchestrator,
    ElevenLabsWebhookHandler,
    create_orchestrator,
    create_webhook_handler,
    ConversationContext,
)

# ============================================================================
# WEBHOOK REQUEST/RESPONSE MODELS
# ============================================================================

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Event types from ElevenLabs real-time API"""
    USER_TRANSCRIPT = "user_transcript"
    AGENT_RESPONSE_START = "agent_response_start"
    AGENT_RESPONSE_END = "agent_response_end"
    CALL_START = "call_start"
    CALL_END = "call_end"
    ERROR = "error"


class UserTranscriptEvent(BaseModel):
    """User speech transcript chunk from ElevenLabs"""
    event_id: str = Field(..., description="Unique event ID")
    call_id: str = Field(..., description="Unique call/session ID")
    user_transcript: str = Field(..., description="The text the user said")
    user_transcript_tokens: List[int] = Field(default_factory=list)
    is_final: bool = Field(..., description="True if this is the final chunk of speech")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentResponseRequest(BaseModel):
    """Instruction to ElevenLabs to play a bot response"""
    text: str = Field(..., description="Text for ElevenLabs TTS to speak")
    emotion: Optional[str] = Field(None, description="Emotion hint (neutral, friendly, urgent)")


class ElevenLabsWebhookPayload(BaseModel):
    """Full webhook payload from ElevenLabs"""
    event_type: WebhookEventType
    event_id: str
    call_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Event-specific data
    user_transcript: Optional[str] = None
    is_final: Optional[bool] = None
    confidence: Optional[float] = None
    agent_response: Optional[str] = None
    error_message: Optional[str] = None


class BotResponsePayload(BaseModel):
    """Response to send back to ElevenLabs (what the agent should say)"""
    call_id: str
    action: str  # "ask_for_item", "validate_with_backend", etc.
    bot_message: str  # Text for ElevenLabs to speak
    should_wait_for_input: bool = True  # Should agent wait for user to speak again?
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)  # Debug info


class ConversationSnapshot(BaseModel):
    """Debug snapshot of conversation state (for telemetry)"""
    call_id: str
    current_state: str
    extracted_entities: Dict[str, Any]
    missing_entities: List[str]
    backend_response: Optional[Dict[str, Any]] = None
    total_amount: Optional[float] = None
    user_hesitations: int = 0
    user_corrections: int = 0


# ============================================================================
# FASTAPI SETUP
# ============================================================================

app = FastAPI(title="JibuTax Conversational Orchestrator")

# Global orchestrator instance (in production: dependency injection + pool)
orchestrator: ConversationOrchestrator = create_orchestrator()
webhook_handler: ElevenLabsWebhookHandler = create_webhook_handler()

# In-memory cache of active calls (for debugging + telemetry)
# In production: Redis or database
active_calls: Dict[str, ConversationContext] = {}


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.post("/webhook/elevenlabs/transcript")
async def handle_user_transcript(payload: UserTranscriptEvent) -> BotResponsePayload:
    """
    Main webhook endpoint: receives user speech transcript from ElevenLabs.
    
    ElevenLabs sends this for every chunk of speech (real-time streaming).
    - Partial chunks: is_final=False (user still speaking, but we got something)
    - Final chunks: is_final=True (user finished speaking, final transcript)
    
    We:
    1. Extract entities from the transcript
    2. Update conversation context
    3. Decide next bot action
    4. Return bot message for ElevenLabs to speak
    """
    
    call_id = payload.call_id
    transcript = payload.user_transcript
    is_final = payload.is_final
    
    logger.info(
        f"[{call_id}] Received user transcript (final={is_final}): {transcript}"
    )
    
    try:
        # Process with state machine
        response = await webhook_handler.orchestrator.process_transcript_chunk(
            user_id=call_id,
            transcript_chunk=transcript,
            is_final=is_final,
        )
        
        # Cache the context for telemetry
        active_calls[call_id] = webhook_handler.orchestrator.get_or_create_context(call_id)
        
        # Build response for ElevenLabs
        bot_message = response.get("bot_message", "")
        action = response.get("action", "")
        context_snapshot = response.get("context_snapshot", {})
        
        logger.info(f"[{call_id}] Bot response: {bot_message}")
        
        return BotResponsePayload(
            call_id=call_id,
            action=action,
            bot_message=bot_message,
            should_wait_for_input=True,
            context_snapshot=context_snapshot,
        )
    
    except Exception as e:
        logger.error(f"[{call_id}] Error processing transcript: {str(e)}", exc_info=True)
        return BotResponsePayload(
            call_id=call_id,
            action="error",
            bot_message="Mwambie kutabirisha. Karibu sana.",
            should_wait_for_input=False,
        )


@app.post("/webhook/elevenlabs/call-start")
async def handle_call_start(data: Dict[str, str]):
    """
    Called when ElevenLabs initiates a new call.
    Initialize conversation context for this call.
    """
    
    call_id = data.get("call_id")
    logger.info(f"[{call_id}] Call started")
    
    # Initialize context
    context = orchestrator.get_or_create_context(call_id)
    active_calls[call_id] = context
    
    return {
        "call_id": call_id,
        "status": "ready",
        "initial_message": "Habari! Jina lako nani na unachouzalisha leo?",
    }


@app.post("/webhook/elevenlabs/call-end")
async def handle_call_end(data: Dict[str, str], background_tasks: BackgroundTasks):
    """
    Called when ElevenLabs call ends.
    Log final context, dispatch SMS, clean up.
    """
    
    call_id = data.get("call_id")
    logger.info(f"[{call_id}] Call ended")
    
    if call_id in active_calls:
        context = active_calls[call_id]
        
        logger.info(f"[{call_id}] Final context: {json.dumps(context.to_dict(), indent=2, default=str)}")
        
        # In background: dispatch SMS, log to analytics
        background_tasks.add_task(_log_call_completion, call_id, context)
        
        # Clean up
        del active_calls[call_id]
    
    return {"call_id": call_id, "status": "logged"}


@app.post("/webhook/elevenlabs/error")
async def handle_webhook_error(data: Dict[str, Any]):
    """Handle errors from ElevenLabs"""
    
    call_id = data.get("call_id")
    error_message = data.get("error_message")
    
    logger.error(f"[{call_id}] ElevenLabs error: {error_message}")
    
    if call_id in active_calls:
        del active_calls[call_id]
    
    return {"call_id": call_id, "status": "error_handled"}


# ============================================================================
# TELEMETRY & DEBUG ENDPOINTS
# ============================================================================

@app.get("/debug/call/{call_id}")
async def get_call_context(call_id: str) -> ConversationSnapshot:
    """
    Debug endpoint: get current state of a specific call.
    Used for dashboard/telemetry during demo.
    """
    
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    
    context = active_calls[call_id]
    
    return ConversationSnapshot(
        call_id=call_id,
        current_state=context.current_state.value,
        extracted_entities={
            "item_name": context.item_name.value if context.item_name else None,
            "quantity": context.quantity.value if context.quantity else None,
            "unit": context.unit.value if context.unit else None,
            "unit_price": context.unit_price.value if context.unit_price else None,
            "buyer_pin": context.buyer_pin.value if context.buyer_pin else None,
            "buyer_name": context.buyer_name.value if context.buyer_name else None,
        },
        missing_entities=context.get_missing_entities(),
        backend_response=context.backend_response,
        total_amount=context.calculate_total_amount(),
        user_hesitations=context.user_hesitations,
        user_corrections=context.user_corrections,
    )


@app.get("/debug/active-calls")
async def get_active_calls() -> Dict[str, Any]:
    """List all active calls and their states (for monitor dashboard)"""
    
    calls = {}
    for call_id, context in active_calls.items():
        calls[call_id] = {
            "state": context.current_state.value,
            "entities": {
                "item_name": context.item_name.value if context.item_name else None,
                "quantity": context.quantity.value if context.quantity else None,
                "buyer_pin": context.buyer_pin.value if context.buyer_pin else None,
            },
            "is_complete": context.are_critical_entities_complete(),
            "call_start_time": context.call_start_time.isoformat(),
        }
    
    return {
        "total_active": len(active_calls),
        "calls": calls,
    }


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def _log_call_completion(call_id: str, context: ConversationContext):
    """
    Background task: log call completion to database.
    In production: write to PostgreSQL, trigger SMS dispatch, fire analytics.
    """
    
    logger.info(f"[{call_id}] Logging call completion...")
    
    # Simulate async work
    await asyncio.sleep(0.5)
    
    # Extract summary
    if context.are_critical_entities_complete():
        logger.info(f"[{call_id}] Transaction summary:")
        logger.info(f"  Item: {context.item_name.value if context.item_name else 'N/A'}")
        logger.info(f"  Quantity: {context.quantity.value if context.quantity else 'N/A'}")
        logger.info(f"  Unit Price: {context.unit_price.value if context.unit_price else 'N/A'}")
        logger.info(f"  Total: KSh {context.calculate_total_amount()}")
        logger.info(f"  Status: {context.current_state.value}")
    
    # TODO: In production
    # - Write to PostgreSQL
    # - Dispatch SMS via Twilio/Africa's Talking
    # - Fire to analytics (Sentry, DataDog, etc.)


# ============================================================================
# MOCK VALIDATION CALLBACK (for async backend responses)
# ============================================================================

async def validation_complete_callback(result: Dict[str, Any]):
    """
    Called when backend validation completes (async).
    Simulates the callback that triggers bot to resume conversation.
    """
    
    logger.info(f"Backend validation callback: {result}")
    
    # In production: trigger bot to resume with new context
    # e.g., tell ElevenLabs "Validation complete, say next message"


# ============================================================================
# HEALTH & READINESS
# ============================================================================

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_calls": len(active_calls),
    }


@app.get("/ready")
async def ready():
    """Readiness check (can accept requests?)"""
    return {
        "status": "ready",
        "orchestrator": "initialized",
        "webhook_handler": "initialized",
    }


# ============================================================================
# TEST ENDPOINTS (For Local Testing & Debugging)
# ============================================================================

@app.post("/test/simulate-call")
async def test_simulate_call():
    """
    Simulate a complete voice call (for local testing).
    """
    
    call_id = f"test-{datetime.now().timestamp()}"
    
    logger.info(f"[{call_id}] Simulating call...")
    
    responses = []
    
    # User says: "I sold 50 kilos of maize"
    r1 = await handle_user_transcript(UserTranscriptEvent(
        event_id="e1",
        call_id=call_id,
        user_transcript="I sold 50 kilos of maize",
        is_final=True,
    ))
    responses.append({"user": "I sold 50 kilos of maize", "bot": r1.bot_message})
    
    # User says: "for 1,500 shillings"
    r2 = await handle_user_transcript(UserTranscriptEvent(
        event_id="e2",
        call_id=call_id,
        user_transcript="for 1,500 shillings",
        is_final=True,
    ))
    responses.append({"user": "for 1,500 shillings", "bot": r2.bot_message})
    
    # User says: "to Safari Hotel, PIN P0512345670M"
    r3 = await handle_user_transcript(UserTranscriptEvent(
        event_id="e3",
        call_id=call_id,
        user_transcript="to Safari Hotel, PIN P0512345670M",
        is_final=True,
    ))
    responses.append({"user": "to Safari Hotel, PIN P0512345670M", "bot": r3.bot_message})
    
    # Get final context
    await asyncio.sleep(1)  # Wait for async validation
    
    final_context = await get_call_context(call_id)
    
    return {
        "call_id": call_id,
        "conversation_flow": responses,
        "final_state": final_context,
    }


@app.post("/test/partial-transcript")
async def test_partial_transcript(data: Dict[str, str]):
    """
    Test partial transcript handling (user still speaking).
    """
    
    call_id = data.get("call_id", f"test-{datetime.now().timestamp()}")
    transcript = data.get("transcript", "")
    
    response = await handle_user_transcript(UserTranscriptEvent(
        event_id="test",
        call_id=call_id,
        user_transcript=transcript,
        is_final=False,
    ))
    
    return {
        "call_id": call_id,
        "input": transcript,
        "response": response,
        "context": await get_call_context(call_id),
    }


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("JibuTax Conversational Orchestrator starting...")
    logger.info(f"Orchestrator: {orchestrator}")
    logger.info(f"Webhook handler: {webhook_handler}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info(f"Shutting down. {len(active_calls)} active calls will be terminated.")
    for call_id in list(active_calls.keys()):
        logger.info(f"  Finalizing call {call_id}...")


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(level=logging.INFO)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,  # Different port from main backend
    )
