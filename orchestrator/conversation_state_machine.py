"""
JibuTax Conversational State Machine
Handles dynamic conversation flow, entity extraction, corrections, and async backend polling.

This is the orchestrator that prevents:
- Context loss on user hesitation
- Halucination on entity extraction
- Lost corrections ("wait, it was 60, not 50")
- Redundant backend calls
- Voice latency killing the UX
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import logging
from abc import ABC, abstractmethod
import asyncio
import hashlib

# ============================================================================
# CONVERSATIONAL STATE MACHINE TYPES
# ============================================================================

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """States in the voice conversation flow"""
    GREETING = "greeting"                    # Agent answers, greets user
    AWAITING_ITEM = "awaiting_item"          # Waiting for item/product name
    AWAITING_QUANTITY = "awaiting_quantity"  # Waiting for quantity
    AWAITING_UNIT = "awaiting_unit"          # Waiting for unit (kg, bags, liters)
    AWAITING_PRICE = "awaiting_price"        # Waiting for unit price
    AWAITING_BUYER_PIN = "awaiting_buyer_pin"  # Waiting for buyer's KRA PIN
    CONFIRMING = "confirming"                # Repeating back to confirm
    VALIDATION_PENDING = "validation_pending"  # Waiting for backend validation
    VALIDATION_SUCCESS = "validation_success"  # Backend validated, ready to file
    VALIDATION_FAILED = "validation_failed"  # Backend rejected (invalid PIN, etc.)
    FILING = "filing"                        # Filing with KRA
    COMPLETE = "complete"                    # Receipt filed, SMS sent
    ERROR = "error"                          # Unrecoverable error


class ContextConfidence(str, Enum):
    """Confidence level of extracted entity"""
    EXPLICIT = "explicit"      # User clearly stated ("I sold 50 kilos")
    INFERRED = "inferred"      # Extracted from context ("50... kilos")
    CORRECTED = "corrected"    # User corrected themselves
    UNCLEAR = "unclear"        # User said something ambiguous


# ============================================================================
# ENTITY EXTRACTION WITH CONFIDENCE TRACKING
# ============================================================================

@dataclass
class ExtractedEntity:
    """Represents an extracted entity with confidence and timestamp"""
    value: Any
    confidence: ContextConfidence
    timestamp: datetime
    original_text: str = ""      # Raw text the user said
    extraction_attempt: int = 1  # Which attempt (user may correct)
    
    def to_dict(self):
        return {
            "value": self.value,
            "confidence": self.confidence.value,
            "timestamp": self.timestamp.isoformat(),
            "original_text": self.original_text,
            "extraction_attempt": self.extraction_attempt,
        }


@dataclass
class ConversationContext:
    """
    Tracks all extracted entities and conversation metadata.
    This is the SOURCE OF TRUTH for what we know about the transaction.
    """
    # Core transaction entities (from voice extraction)
    item_name: Optional[ExtractedEntity] = None
    quantity: Optional[ExtractedEntity] = None
    unit: Optional[ExtractedEntity] = None
    unit_price: Optional[ExtractedEntity] = None
    buyer_pin: Optional[ExtractedEntity] = None
    buyer_name: Optional[ExtractedEntity] = None
    
    # Conversation metadata
    user_id: str = ""                         # Session ID or phone number
    call_start_time: datetime = field(default_factory=datetime.now)
    current_state: ConversationState = ConversationState.GREETING
    
    # Corrections & overwrites
    correction_history: List[Dict] = field(default_factory=list)  # Audit trail
    
    # Backend validation result
    backend_response: Optional[Dict[str, Any]] = None
    backend_response_time: Optional[float] = None
    
    # Interruptions & context recovery
    last_bot_message: str = ""                # Last thing the agent said
    pending_clarification: Optional[str] = None  # What we're waiting for
    
    # Sentiment/signals
    user_hesitations: int = 0                 # "Uh...", "wait...", etc.
    user_corrections: int = 0                 # "No, I meant..."
    
    def __post_init__(self):
        """Initialize with current time"""
        if not self.user_id:
            self.user_id = f"call-{datetime.now().timestamp()}"
    
    def get_missing_entities(self) -> List[str]:
        """Return list of entities we still need"""
        missing = []
        if not self.item_name:
            missing.append("item_name")
        if not self.quantity:
            missing.append("quantity")
        if not self.unit:
            missing.append("unit")
        if not self.unit_price:
            missing.append("unit_price")
        if not self.buyer_pin:
            missing.append("buyer_pin")
        return missing
    
    def are_critical_entities_complete(self) -> bool:
        """Check if we have all required entities to proceed to validation"""
        critical = [self.item_name, self.quantity, self.unit, self.unit_price, self.buyer_pin]
        return all(e is not None for e in critical)
    
    def calculate_total_amount(self) -> Optional[float]:
        """Deterministically recalculate total (safety check against LLM hallucination)"""
        if self.quantity and self.unit_price:
            try:
                q = float(self.quantity.value)
                up = float(self.unit_price.value)
                return q * up
            except (ValueError, TypeError):
                return None
        return None
    
    def to_backend_payload(self) -> Dict[str, Any]:
        """Format context as backend API payload"""
        return {
            "item_name": self.item_name.value if self.item_name else None,
            "quantity": float(self.quantity.value) if self.quantity else None,
            "unit": self.unit.value if self.unit else None,
            "unit_price": float(self.unit_price.value) if self.unit_price else None,
            "buyer_pin": self.buyer_pin.value if self.buyer_pin else None,
            "buyer_name": self.buyer_name.value if self.buyer_name else None,
        }
    
    def log_correction(self, field: str, old_value: Any, new_value: Any, reason: str):
        """Audit trail for corrections (user said "wait, I meant X not Y")"""
        self.correction_history.append({
            "timestamp": datetime.now().isoformat(),
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
        })
        self.user_corrections += 1
    
    def to_dict(self):
        """Convert entire context to dict for logging/debugging"""
        return {
            "user_id": self.user_id,
            "call_start_time": self.call_start_time.isoformat(),
            "current_state": self.current_state.value,
            "item_name": self.item_name.to_dict() if self.item_name else None,
            "quantity": self.quantity.to_dict() if self.quantity else None,
            "unit": self.unit.to_dict() if self.unit else None,
            "unit_price": self.unit_price.to_dict() if self.unit_price else None,
            "buyer_pin": self.buyer_pin.to_dict() if self.buyer_pin else None,
            "buyer_name": self.buyer_name.to_dict() if self.buyer_name else None,
            "correction_history": self.correction_history,
            "backend_response": self.backend_response,
            "backend_response_time": self.backend_response_time,
            "total_amount": self.calculate_total_amount(),
            "missing_entities": self.get_missing_entities(),
            "is_ready_for_validation": self.are_critical_entities_complete(),
        }


# ============================================================================
# STATE TRANSITION RULES (the orchestration logic)
# ============================================================================

class StateTransition:
    """
    Encodes the valid transitions between conversation states.
    This prevents invalid flows and ensures data completeness before advancing.
    """
    
    # Define which states can transition to which
    VALID_TRANSITIONS = {
        ConversationState.GREETING: [ConversationState.AWAITING_ITEM],
        ConversationState.AWAITING_ITEM: [ConversationState.AWAITING_QUANTITY],
        ConversationState.AWAITING_QUANTITY: [ConversationState.AWAITING_UNIT],
        ConversationState.AWAITING_UNIT: [ConversationState.AWAITING_PRICE],
        ConversationState.AWAITING_PRICE: [ConversationState.AWAITING_BUYER_PIN],
        ConversationState.AWAITING_BUYER_PIN: [ConversationState.CONFIRMING],
        ConversationState.CONFIRMING: [
            ConversationState.VALIDATION_PENDING,
            ConversationState.AWAITING_ITEM,  # User said "no, let me restart"
        ],
        ConversationState.VALIDATION_PENDING: [
            ConversationState.VALIDATION_SUCCESS,
            ConversationState.VALIDATION_FAILED,
        ],
        ConversationState.VALIDATION_SUCCESS: [ConversationState.FILING],
        ConversationState.VALIDATION_FAILED: [ConversationState.AWAITING_BUYER_PIN],  # Ask for PIN again
        ConversationState.FILING: [ConversationState.COMPLETE],
        ConversationState.COMPLETE: [],  # Terminal state
        ConversationState.ERROR: [],  # Terminal state
    }
    
    @staticmethod
    def can_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
        """Check if transition is valid"""
        valid = StateTransition.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid
    
    @staticmethod
    def assert_transition(from_state: ConversationState, to_state: ConversationState):
        """Raise exception if transition is invalid"""
        if not StateTransition.can_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition: {from_state.value} → {to_state.value}"
            )


# ============================================================================
# ASYNC BACKEND VALIDATION (polling without blocking voice)
# ============================================================================

class BackendValidator:
    """
    Handles async communication with the backend (Part 1: MCP Infrastructure).
    Prevents voice latency by polling asynchronously.
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.timeout = 5.0  # Max 5 seconds to wait for validation
    
    async def validate_context(
        self,
        context: ConversationContext,
        callback_on_complete: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Send context to backend for validation.
        Returns immediately; uses callback to notify when response arrives.
        """
        
        if not context.are_critical_entities_complete():
            raise ValueError("Cannot validate: missing critical entities")
        
        # Build payload
        payload = context.to_backend_payload()
        
        logger.info(f"[{context.user_id}] Sending validation payload to backend")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Make async HTTP call (in real impl: httpx.AsyncClient)
        try:
            # Simulate async call (replace with real httpx in production)
            result = await self._call_backend_mock(payload)
            
            context.backend_response = result
            logger.info(f"[{context.user_id}] Backend validation complete: {result.get('status')}")
            
            if callback_on_complete:
                await callback_on_complete(result)
            
            return result
        
        except asyncio.TimeoutError:
            logger.error(f"[{context.user_id}] Backend validation timed out after {self.timeout}s")
            return {
                "status": "error",
                "message": "Backend validation timed out. Please try again.",
                "error": "timeout",
            }
        except Exception as e:
            logger.error(f"[{context.user_id}] Backend validation failed: {str(e)}")
            return {
                "status": "error",
                "message": "System error. Please try again.",
                "error": str(e),
            }
    
    async def _call_backend_mock(self, payload: Dict) -> Dict[str, Any]:
        """
        Mock backend call (replace with real httpx call in production).
        Simulates the MCP Infrastructure response from Part 1.
        """
        await asyncio.sleep(0.5)  # Simulate 500ms API latency
        
        # Mock validation logic
        buyer_pin = payload.get("buyer_pin")
        
        if not buyer_pin:
            return {"status": "error", "message": "Missing buyer PIN"}
        
        # Mock KRA PIN validation (in production, hits Part 1's security middleware)
        valid_pins = ["P0512345670M", "P0712345671X", "P0912345672A"]
        
        if buyer_pin in valid_pins:
            return {
                "status": "success",
                "buyer_valid": True,
                "buyer_name": "Safari Hotel Limited",
                "total_amount": payload.get("quantity", 0) * payload.get("unit_price", 0),
                "tax_amount": payload.get("quantity", 0) * payload.get("unit_price", 0) * 0.16,
                "message": f"Receipt ready to file for {payload.get('item_name')}",
            }
        else:
            return {
                "status": "error",
                "buyer_valid": False,
                "message": f"KRA PIN {buyer_pin} not found. Please verify.",
            }


# ============================================================================
# ENTITY EXTRACTION & CORRECTION HANDLING
# ============================================================================

class EntityExtractor:
    """
    Extracts entities from voice transcripts.
    Handles corrections, overwrites, and maintains confidence scores.
    """
    
    def __init__(self):
        self.item_keywords = {
            "maize": ["maize", "mahindi", "corn", "grain"],
            "tomato": ["tomato", "tomatoes", "tamato"],
            "fish": ["fish", "samaki", "tilapia"],
        }
        self.unit_keywords = {
            "kg": ["kg", "kilo", "kilogram"],
            "bags": ["bags", "bag"],
            "liters": ["liters", "liter", "litres"],
            "units": ["units", "unit", "pieces"],
        }
    
    def extract_from_transcript(
        self,
        transcript: str,
        existing_context: ConversationContext,
    ) -> tuple[ConversationContext, List[str]]:
        """
        Extract entities from a new transcript snippet.
        Handle corrections and update context.
        Returns: (updated_context, newly_extracted_fields)
        """
        
        logger.info(f"Extracting from transcript: {transcript}")
        
        newly_extracted = []
        
        # Check for correction markers ("wait, no...", "I meant...")
        if any(word in transcript.lower() for word in ["wait", "no", "actually", "I meant"]):
            existing_context.user_hesitations += 1
            logger.info(f"[{existing_context.user_id}] Detected user correction attempt")
        
        # ITEM EXTRACTION
        if not existing_context.item_name:
            for item, keywords in self.item_keywords.items():
                if any(kw in transcript.lower() for kw in keywords):
                    existing_context.item_name = ExtractedEntity(
                        value=item,
                        confidence=ContextConfidence.EXPLICIT,
                        timestamp=datetime.now(),
                        original_text=transcript,
                    )
                    newly_extracted.append("item_name")
                    logger.info(f"Extracted item: {item}")
                    break
        
        # QUANTITY EXTRACTION
        if not existing_context.quantity:
            quantity = self._extract_number(transcript)
            if quantity is not None:
                existing_context.quantity = ExtractedEntity(
                    value=quantity,
                    confidence=ContextConfidence.EXPLICIT,
                    timestamp=datetime.now(),
                    original_text=transcript,
                )
                newly_extracted.append("quantity")
                logger.info(f"Extracted quantity: {quantity}")
        
        # UNIT EXTRACTION
        if not existing_context.unit:
            for unit, keywords in self.unit_keywords.items():
                if any(kw in transcript.lower() for kw in keywords):
                    existing_context.unit = ExtractedEntity(
                        value=unit,
                        confidence=ContextConfidence.EXPLICIT,
                        timestamp=datetime.now(),
                        original_text=transcript,
                    )
                    newly_extracted.append("unit")
                    logger.info(f"Extracted unit: {unit}")
                    break
        
        # UNIT PRICE EXTRACTION
        if not existing_context.unit_price:
            # Look for price patterns: "2,500 each", "1500 per kilo", etc.
            price = self._extract_price(transcript)
            if price is not None:
                existing_context.unit_price = ExtractedEntity(
                    value=price,
                    confidence=ContextConfidence.EXPLICIT,
                    timestamp=datetime.now(),
                    original_text=transcript,
                )
                newly_extracted.append("unit_price")
                logger.info(f"Extracted unit price: {price}")
        
        # BUYER PIN EXTRACTION
        if not existing_context.buyer_pin:
            pin = self._extract_kra_pin(transcript)
            if pin:
                existing_context.buyer_pin = ExtractedEntity(
                    value=pin,
                    confidence=ContextConfidence.EXPLICIT,
                    timestamp=datetime.now(),
                    original_text=transcript,
                )
                newly_extracted.append("buyer_pin")
                logger.info(f"Extracted buyer PIN: {pin}")
        
        # BUYER NAME EXTRACTION
        if not existing_context.buyer_name:
            # Look for "Safari Hotel", "Equity Bank", etc. (capitalized sequences)
            buyer = self._extract_proper_noun(transcript)
            if buyer:
                existing_context.buyer_name = ExtractedEntity(
                    value=buyer,
                    confidence=ContextConfidence.INFERRED,
                    timestamp=datetime.now(),
                    original_text=transcript,
                )
                newly_extracted.append("buyer_name")
                logger.info(f"Extracted buyer name: {buyer}")
        
        return existing_context, newly_extracted
    
    @staticmethod
    def _extract_number(text: str) -> Optional[float]:
        """Extract first number from text"""
        import re
        match = re.search(r'\d+', text)
        if match:
            return float(match.group())
        return None
    
    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        """Extract price (handles 2,500, 2500, etc.)"""
        import re
        # Match numbers with optional commas: 2,500 or 2500
        match = re.search(r'(\d+(?:,\d+)*)', text)
        if match:
            price_str = match.group(1).replace(',', '')
            return float(price_str)
        return None
    
    @staticmethod
    def _extract_kra_pin(text: str) -> Optional[str]:
        """Extract KRA PIN (format: P + 10 digits + 1 letter)"""
        import re
        match = re.search(r'P\d{10}[A-Z]', text)
        if match:
            return match.group().upper()
        return None
    
    @staticmethod
    def _extract_proper_noun(text: str) -> Optional[str]:
        """Extract capitalized proper noun (buyer name)"""
        import re
        # Look for capitalized sequences (e.g., "Safari Hotel", "Equity Bank")
        matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        if matches:
            return matches[0]
        return None


# ============================================================================
# ORCHESTRATOR: The Main Conversational State Machine
# ============================================================================

class ConversationOrchestrator:
    """
    Main orchestrator that manages the entire voice conversation flow.
    
    Responsibilities:
    1. Track conversation state (greeting → item → quantity → ... → complete)
    2. Extract entities from partial transcripts (handle corrections)
    3. Decide when to call backend for validation (async, non-blocking)
    4. Handle interruptions and user hesitations gracefully
    5. Provide bot responses based on current state
    """
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.extractor = EntityExtractor()
        self.validator = BackendValidator(backend_url)
        self.contexts: Dict[str, ConversationContext] = {}  # user_id → context
    
    def get_or_create_context(self, user_id: str) -> ConversationContext:
        """Get existing context or create new one"""
        if user_id not in self.contexts:
            context = ConversationContext(user_id=user_id)
            self.contexts[user_id] = context
            logger.info(f"Created new conversation context for {user_id}")
        return self.contexts[user_id]
    
    async def process_transcript_chunk(
        self,
        user_id: str,
        transcript_chunk: str,
        is_final: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a chunk of transcript from ElevenLabs real-time webhook.
        
        Handles:
        - Entity extraction
        - State transitions
        - Backend validation (async)
        - Bot response generation
        """
        
        context = self.get_or_create_context(user_id)
        
        logger.info(f"[{user_id}] Processing transcript chunk (final={is_final}): {transcript_chunk}")
        
        # Step 1: Extract entities from this chunk
        context, newly_extracted = self.extractor.extract_from_transcript(
            transcript_chunk,
            context,
        )
        
        logger.debug(f"Newly extracted: {newly_extracted}")
        logger.debug(f"Context state: {context.to_dict()}")
        
        # Step 2: Determine next action based on what we know
        next_action = self._decide_next_action(context, newly_extracted, is_final)
        
        logger.info(f"[{user_id}] Next action: {next_action}")
        
        # Step 3: Execute action
        response = await self._execute_action(context, next_action)
        
        return response
    
    def _decide_next_action(
        self,
        context: ConversationContext,
        newly_extracted: List[str],
        is_final: bool,
    ) -> str:
        """
        Decide what to do next based on current context.
        
        Logic:
        - If missing entities: ask for next one
        - If all entities extracted & final chunk: validate with backend
        - If validation pending & response arrived: confirm or ask for correction
        """
        
        # Are we missing critical entities?
        missing = context.get_missing_entities()
        
        if missing:
            # Ask for the next missing entity
            return f"ask_for_{missing[0]}"
        
        # We have all entities
        if context.are_critical_entities_complete():
            
            # Sanity check: recalculate total to catch LLM hallucination
            calc_total = context.calculate_total_amount()
            if calc_total is None:
                return "ask_for_clarification"
            
            # If we haven't validated yet, do it now
            if not context.backend_response:
                return "validate_with_backend"
            
            # If validation succeeded, file the receipt
            if context.backend_response.get("status") == "success":
                return "file_receipt"
            
            # If validation failed, ask for correction
            if context.backend_response.get("status") == "error":
                return "ask_for_pin_correction"
        
        return "await_more_input"
    
    async def _execute_action(
        self,
        context: ConversationContext,
        action: str,
    ) -> Dict[str, Any]:
        """Execute the decided action and return bot response"""
        
        if action.startswith("ask_for_"):
            field = action.replace("ask_for_", "")
            StateTransition.assert_transition(
                context.current_state,
                ConversationState[field.upper()],
            )
            context.current_state = ConversationState[field.upper()]
            
            # Generate bot message asking for the field
            bot_message = self._generate_ask_message(field, context)
            
            return {
                "action": action,
                "bot_message": bot_message,
                "state": context.current_state.value,
                "context_snapshot": context.to_dict(),
            }
        
        elif action == "validate_with_backend":
            # Transition to validation pending
            StateTransition.assert_transition(
                context.current_state,
                ConversationState.CONFIRMING,
            )
            context.current_state = ConversationState.CONFIRMING
            
            # Generate confirmation message
            bot_message = self._generate_confirmation_message(context)
            
            # Fire off async validation (non-blocking)
            asyncio.create_task(
                self.validator.validate_context(
                    context,
                    callback_on_complete=self._on_validation_complete,
                )
            )
            
            context.current_state = ConversationState.VALIDATION_PENDING
            
            return {
                "action": "confirming_and_validating",
                "bot_message": bot_message,
                "state": context.current_state.value,
                "context_snapshot": context.to_dict(),
            }
        
        elif action == "file_receipt":
            StateTransition.assert_transition(
                context.current_state,
                ConversationState.FILING,
            )
            context.current_state = ConversationState.FILING
            
            bot_message = "Sawa! Ninaandika receipt kwenye KRA sasa. Karibu dakika moja..."
            
            # In production: call Part 3 (Tax Engine) to file
            await asyncio.sleep(1)
            
            context.current_state = ConversationState.COMPLETE
            bot_message = "Njema! Receipt imefiled na KRA. SMS itakuja haraka. Asante!"
            
            return {
                "action": "receipt_filed",
                "bot_message": bot_message,
                "state": context.current_state.value,
                "context_snapshot": context.to_dict(),
            }
        
        elif action == "ask_for_pin_correction":
            StateTransition.assert_transition(
                context.current_state,
                ConversationState.VALIDATION_FAILED,
            )
            context.current_state = ConversationState.VALIDATION_FAILED
            
            error_msg = context.backend_response.get("message", "Validation failed")
            bot_message = f"{error_msg} Karibu tena?"
            
            # Reset to awaiting PIN again
            context.buyer_pin = None
            context.current_state = ConversationState.AWAITING_BUYER_PIN
            
            return {
                "action": "ask_for_correction",
                "bot_message": bot_message,
                "state": context.current_state.value,
                "context_snapshot": context.to_dict(),
            }
        
        else:
            return {
                "action": action,
                "bot_message": "Karibu, endelea...",
                "state": context.current_state.value,
                "context_snapshot": context.to_dict(),
            }
    
    def _generate_ask_message(self, field: str, context: ConversationContext) -> str:
        """Generate natural bot message asking for a field"""
        messages = {
            "item_name": "Ni nini kile unachouzalisha?",
            "quantity": f"Uliweza kuweka kiasi gani cha {context.item_name.value if context.item_name else 'kitu'}?",
            "unit": "Kitengo gani? Kilos, bags, liters?",
            "unit_price": "Bei gani kwa kila unit?",
            "buyer_pin": "PIN yao ni nini?",
        }
        return messages.get(field, "Karibu, ndiyo?")
    
    def _generate_confirmation_message(self, context: ConversationContext) -> str:
        """Generate confirmation message summarizing the transaction"""
        q = context.quantity.value if context.quantity else "?"
        item = context.item_name.value if context.item_name else "item"
        price = context.unit_price.value if context.unit_price else "?"
        total = context.calculate_total_amount() or "?"
        
        return (
            f"Sawa! Uliweza kuweka {q} {context.unit.value if context.unit else 'units'} "
            f"ya {item} kwa {price} kila moja = {total} shillings. "
            f"Ndiyo?"
        )
    
    async def _on_validation_complete(self, result: Dict[str, Any]):
        """Callback when backend validation completes"""
        logger.info(f"Validation complete: {result}")
        # Update context or trigger next action in real system


# ============================================================================
# ELEVENLABS WEBHOOK HANDLER
# ============================================================================

class ElevenLabsWebhookHandler:
    """
    Handles real-time webhook events from ElevenLabs.
    
    Event types:
    - user_transcript (partial/final chunks as user speaks)
    - agent_response_start (agent starts speaking)
    - agent_response_end (agent stops speaking)
    - call_end (conversation ended)
    """
    
    def __init__(self, orchestrator: ConversationOrchestrator):
        self.orchestrator = orchestrator
    
    async def handle_user_transcript(
        self,
        user_id: str,
        transcript: str,
        is_final: bool,
    ) -> str:
        """
        Handles user speech transcript from ElevenLabs real-time webhook.
        
        Returns: Bot response to play back to user (or empty string if not yet)
        """
        
        logger.info(f"[{user_id}] User transcript (final={is_final}): {transcript}")
        
        # Process with orchestrator
        response = await self.orchestrator.process_transcript_chunk(
            user_id,
            transcript,
            is_final,
        )
        
        # Extract bot message to return
        bot_message = response.get("bot_message", "")
        
        logger.info(f"[{user_id}] Bot response: {bot_message}")
        
        return bot_message
    
    async def handle_call_end(self, user_id: str):
        """Clean up context when call ends"""
        context = self.orchestrator.get_or_create_context(user_id)
        
        logger.info(f"[{user_id}] Call ended. Final context: {context.to_dict()}")
        
        # In production: log to database, trigger SMS dispatch, analytics


# ============================================================================
# MAIN EXPORT: Instantiate for use in FastAPI
# ============================================================================

def create_orchestrator(backend_url: str = "http://localhost:8000") -> ConversationOrchestrator:
    """Factory function to create a new orchestrator instance"""
    return ConversationOrchestrator(backend_url)


def create_webhook_handler(
    backend_url: str = "http://localhost:8000",
) -> ElevenLabsWebhookHandler:
    """Factory function to create a new webhook handler instance"""
    orchestrator = ConversationOrchestrator(backend_url)
    return ElevenLabsWebhookHandler(orchestrator)


if __name__ == "__main__":
    # Test the orchestrator
    logging.basicConfig(level=logging.DEBUG)
    
    async def test():
        orchestrator = create_orchestrator()
        
        # Simulate a voice call
        user_id = "test-user-001"
        
        # User says: "I sold 50 kilos of maize"
        r1 = await orchestrator.process_transcript_chunk(
            user_id,
            "I sold 50 kilos of maize",
            is_final=True,
        )
        print(f"\n=== Response 1 ===\n{json.dumps(r1, indent=2, default=str)}")
        
        # User says: "for 1,500 shillings"
        r2 = await orchestrator.process_transcript_chunk(
            user_id,
            "for 1,500 shillings",
            is_final=True,
        )
        print(f"\n=== Response 2 ===\n{json.dumps(r2, indent=2, default=str)}")
        
        # User says: "to Safari Hotel, PIN P0512345670M"
        r3 = await orchestrator.process_transcript_chunk(
            user_id,
            "to Safari Hotel, PIN P0512345670M",
            is_final=True,
        )
        print(f"\n=== Response 3 ===\n{json.dumps(r3, indent=2, default=str)}")
    
    asyncio.run(test())
