"""
Test Suite for Conversational State Machine
Tests entity extraction, state transitions, and async validation.

Run with: pytest test_conversation_state_machine.py -v
"""

import pytest
import asyncio
import json
from datetime import datetime

from conversation_state_machine import (
    ConversationState,
    ContextConfidence,
    ExtractedEntity,
    ConversationContext,
    EntityExtractor,
    StateTransition,
    BackendValidator,
    ConversationOrchestrator,
)


# ============================================================================
# UNIT TESTS: ConversationContext
# ============================================================================

class TestConversationContext:
    """Test the conversation context data structure"""
    
    def test_create_context(self):
        """Test creating a new conversation context"""
        context = ConversationContext(user_id="user-001")
        
        assert context.user_id == "user-001"
        assert context.current_state == ConversationState.GREETING
        assert context.get_missing_entities() == [
            "item_name",
            "quantity",
            "unit",
            "unit_price",
            "buyer_pin",
        ]
    
    def test_are_entities_complete(self):
        """Test checking if all required entities are present"""
        context = ConversationContext(user_id="user-001")
        
        # Initially incomplete
        assert not context.are_critical_entities_complete()
        
        # Add entities
        context.item_name = ExtractedEntity(
            value="maize",
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        context.quantity = ExtractedEntity(
            value=50,
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        context.unit = ExtractedEntity(
            value="kg",
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        context.unit_price = ExtractedEntity(
            value=90,
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        context.buyer_pin = ExtractedEntity(
            value="P0512345670M",
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        
        # Now complete
        assert context.are_critical_entities_complete()
    
    def test_calculate_total_amount(self):
        """Test deterministic total calculation"""
        context = ConversationContext(user_id="user-001")
        
        context.quantity = ExtractedEntity(
            value=50,
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        context.unit_price = ExtractedEntity(
            value=90,
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        
        total = context.calculate_total_amount()
        assert total == 4500  # 50 * 90
    
    def test_log_correction(self):
        """Test correction audit trail"""
        context = ConversationContext(user_id="user-001")
        
        context.quantity = ExtractedEntity(
            value=50,
            confidence=ContextConfidence.EXPLICIT,
            timestamp=datetime.now(),
        )
        
        context.log_correction(
            field="quantity",
            old_value=50,
            new_value=60,
            reason="User said 'wait, I meant 60'",
        )
        
        assert len(context.correction_history) == 1
        assert context.correction_history[0]["old_value"] == 50
        assert context.correction_history[0]["new_value"] == 60
        assert context.user_corrections == 1
    
    def test_to_backend_payload(self):
        """Test conversion to backend API payload"""
        context = ConversationContext(user_id="user-001")
        context.item_name = ExtractedEntity(value="maize", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.quantity = ExtractedEntity(value=50, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit = ExtractedEntity(value="kg", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit_price = ExtractedEntity(value=90, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.buyer_pin = ExtractedEntity(value="P0512345670M", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        
        payload = context.to_backend_payload()
        
        assert payload["item_name"] == "maize"
        assert payload["quantity"] == 50
        assert payload["unit"] == "kg"
        assert payload["unit_price"] == 90
        assert payload["buyer_pin"] == "P0512345670M"


# ============================================================================
# UNIT TESTS: EntityExtractor
# ============================================================================

class TestEntityExtractor:
    """Test the entity extraction logic"""
    
    def test_extract_item_name(self):
        """Test item name extraction"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "I sold maize",
            context,
        )
        
        assert context.item_name is not None
        assert context.item_name.value == "maize"
        assert "item_name" in extracted
    
    def test_extract_quantity(self):
        """Test quantity extraction"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "50 kilos",
            context,
        )
        
        assert context.quantity is not None
        assert context.quantity.value == 50.0
        assert "quantity" in extracted
    
    def test_extract_unit(self):
        """Test unit extraction"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "in kilos",
            context,
        )
        
        assert context.unit is not None
        assert context.unit.value == "kg"
        assert "unit" in extracted
    
    def test_extract_price(self):
        """Test price extraction (handles commas)"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "2,500 shillings",
            context,
        )
        
        assert context.unit_price is not None
        assert context.unit_price.value == 2500.0
        assert "unit_price" in extracted
    
    def test_extract_kra_pin(self):
        """Test KRA PIN extraction"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "P0512345670M",
            context,
        )
        
        assert context.buyer_pin is not None
        assert context.buyer_pin.value == "P0512345670M"
        assert "buyer_pin" in extracted
    
    def test_extract_buyer_name(self):
        """Test buyer name (proper noun) extraction"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "Safari Hotel Limited",
            context,
        )
        
        assert context.buyer_name is not None
        assert "Safari Hotel" in context.buyer_name.value
        assert "buyer_name" in extracted
    
    def test_extract_multiple_entities_from_one_transcript(self):
        """Test extracting multiple entities from a single transcript"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "I sold 50 kilos of maize for 4500 to Safari Hotel",
            context,
        )
        
        # Should extract multiple entities
        assert "item_name" in extracted
        assert "quantity" in extracted
        assert "unit" in extracted
        assert "buyer_name" in extracted
        
        assert context.item_name.value == "maize"
        assert context.quantity.value == 50.0
        assert context.unit.value == "kg"
    
    def test_handle_no_extraction(self):
        """Test when transcript contains no extractable entities"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "Um, uh, well...",
            context,
        )
        
        # Nothing extracted
        assert len(extracted) == 0
        assert context.item_name is None


# ============================================================================
# UNIT TESTS: StateTransition
# ============================================================================

class TestStateTransition:
    """Test state transition validation"""
    
    def test_valid_transition(self):
        """Test valid state transitions"""
        assert StateTransition.can_transition(
            ConversationState.GREETING,
            ConversationState.AWAITING_ITEM,
        )
    
    def test_invalid_transition(self):
        """Test that invalid transitions are caught"""
        assert not StateTransition.can_transition(
            ConversationState.GREETING,
            ConversationState.COMPLETE,  # Can't jump directly!
        )
    
    def test_assert_transition_valid(self):
        """Test assert_transition with valid transition"""
        # Should not raise
        StateTransition.assert_transition(
            ConversationState.AWAITING_ITEM,
            ConversationState.AWAITING_QUANTITY,
        )
    
    def test_assert_transition_invalid(self):
        """Test assert_transition with invalid transition raises"""
        with pytest.raises(ValueError):
            StateTransition.assert_transition(
                ConversationState.AWAITING_ITEM,
                ConversationState.COMPLETE,  # Invalid!
            )
    
    def test_full_conversation_flow(self):
        """Test a complete valid conversation flow"""
        flow = [
            ConversationState.GREETING,
            ConversationState.AWAITING_ITEM,
            ConversationState.AWAITING_QUANTITY,
            ConversationState.AWAITING_UNIT,
            ConversationState.AWAITING_PRICE,
            ConversationState.AWAITING_BUYER_PIN,
            ConversationState.CONFIRMING,
            ConversationState.VALIDATION_PENDING,
            ConversationState.VALIDATION_SUCCESS,
            ConversationState.FILING,
            ConversationState.COMPLETE,
        ]
        
        # Each transition should be valid
        for i in range(len(flow) - 1):
            assert StateTransition.can_transition(flow[i], flow[i + 1])


# ============================================================================
# UNIT TESTS: BackendValidator
# ============================================================================

class TestBackendValidator:
    """Test async backend validation"""
    
    @pytest.mark.asyncio
    async def test_validate_valid_pin(self):
        """Test validation with valid KRA PIN"""
        validator = BackendValidator()
        context = ConversationContext(user_id="user-001")
        
        context.item_name = ExtractedEntity(value="maize", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.quantity = ExtractedEntity(value=50, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit = ExtractedEntity(value="kg", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit_price = ExtractedEntity(value=90, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.buyer_pin = ExtractedEntity(value="P0512345670M", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        
        result = await validator.validate_context(context)
        
        assert result["status"] == "success"
        assert result["buyer_valid"] == True
        assert "buyer_name" in result
    
    @pytest.mark.asyncio
    async def test_validate_invalid_pin(self):
        """Test validation with invalid KRA PIN"""
        validator = BackendValidator()
        context = ConversationContext(user_id="user-001")
        
        context.item_name = ExtractedEntity(value="maize", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.quantity = ExtractedEntity(value=50, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit = ExtractedEntity(value="kg", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.unit_price = ExtractedEntity(value=90, confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        context.buyer_pin = ExtractedEntity(value="P0000000000Z", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        
        result = await validator.validate_context(context)
        
        assert result["status"] == "error"
        assert result["buyer_valid"] == False


# ============================================================================
# INTEGRATION TESTS: ConversationOrchestrator
# ============================================================================

class TestConversationOrchestrator:
    """Test the full orchestrator with realistic flows"""
    
    @pytest.mark.asyncio
    async def test_simple_conversation_flow(self):
        """Test a simple complete conversation"""
        orchestrator = ConversationOrchestrator()
        user_id = "test-user-001"
        
        # User: "I sold 50 kilos of maize"
        r1 = await orchestrator.process_transcript_chunk(
            user_id,
            "I sold 50 kilos of maize",
            is_final=True,
        )
        
        assert r1["action"] == "ask_for_unit_price"
        assert "price" in r1["bot_message"].lower() or "bei" in r1["bot_message"].lower()
        
        # User: "for 90 shillings"
        r2 = await orchestrator.process_transcript_chunk(
            user_id,
            "for 90 shillings",
            is_final=True,
        )
        
        assert r2["action"] == "ask_for_buyer_pin"
        assert "PIN" in r2["bot_message"] or "pin" in r2["bot_message"]
        
        # User: "P0512345670M"
        r3 = await orchestrator.process_transcript_chunk(
            user_id,
            "P0512345670M",
            is_final=True,
        )
        
        # Should move to confirming/validation
        assert r3["action"] in ["confirming_and_validating", "ask_for_pin_correction"]
    
    @pytest.mark.asyncio
    async def test_correction_flow(self):
        """Test user correction handling"""
        orchestrator = ConversationOrchestrator()
        user_id = "test-user-002"
        
        # User: "50 kilos"
        r1 = await orchestrator.process_transcript_chunk(
            user_id,
            "50 kilos",
            is_final=True,
        )
        
        context = orchestrator.get_or_create_context(user_id)
        assert context.quantity.value == 50
        
        # User: "wait, 60 kilos"
        r2 = await orchestrator.process_transcript_chunk(
            user_id,
            "60 kilos",
            is_final=True,
        )
        
        # Should update to 60, not ask again
        context = orchestrator.get_or_create_context(user_id)
        assert context.quantity.value == 60
    
    @pytest.mark.asyncio
    async def test_partial_transcript_handling(self):
        """Test that partial transcripts don't break context"""
        orchestrator = ConversationOrchestrator()
        user_id = "test-user-003"
        
        # Partial: "50..." (user still speaking)
        r1 = await orchestrator.process_transcript_chunk(
            user_id,
            "50",
            is_final=False,  # Partial!
        )
        
        context = orchestrator.get_or_create_context(user_id)
        # Might have extracted quantity=50
        
        # Final: "50 kilos of maize"
        r2 = await orchestrator.process_transcript_chunk(
            user_id,
            "50 kilos of maize",
            is_final=True,  # Final!
        )
        
        context = orchestrator.get_or_create_context(user_id)
        # Should have item_name, quantity, unit
        assert context.item_name is not None or context.quantity is not None
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self):
        """Test that multiple calls maintain separate contexts"""
        orchestrator = ConversationOrchestrator()
        
        # Call 1: User sells maize
        r1a = await orchestrator.process_transcript_chunk(
            "call-1",
            "I sold 50 kilos of maize",
            is_final=True,
        )
        
        # Call 2: Different user sells fish
        r2a = await orchestrator.process_transcript_chunk(
            "call-2",
            "I sold 30 kilos of fish",
            is_final=True,
        )
        
        # Verify contexts are separate
        ctx1 = orchestrator.get_or_create_context("call-1")
        ctx2 = orchestrator.get_or_create_context("call-2")
        
        assert ctx1.item_name.value == "maize"
        assert ctx2.item_name.value == "fish"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_extract_price_without_commas(self):
        """Test price extraction for numbers without commas"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "1500 shillings",
            context,
        )
        
        assert context.unit_price.value == 1500.0
    
    def test_invalid_pin_format_rejected(self):
        """Test that invalid KRA PIN format is not extracted"""
        extractor = EntityExtractor()
        context = ConversationContext(user_id="user-001")
        
        context, extracted = extractor.extract_from_transcript(
            "My PIN is 12345",  # Too short, wrong format
            context,
        )
        
        # Should not extract as buyer_pin
        assert context.buyer_pin is None
    
    def test_missing_entities_list(self):
        """Test that missing entities are correctly identified"""
        context = ConversationContext(user_id="user-001")
        
        context.item_name = ExtractedEntity(value="maize", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        # Missing quantity, unit, unit_price, buyer_pin
        
        missing = context.get_missing_entities()
        assert len(missing) == 4
        assert "quantity" in missing
        assert "buyer_pin" in missing
    
    @pytest.mark.asyncio
    async def test_validation_without_critical_entities_fails(self):
        """Test that validation fails if critical entities are missing"""
        validator = BackendValidator()
        context = ConversationContext(user_id="user-001")
        
        # Only item_name, missing others
        context.item_name = ExtractedEntity(value="maize", confidence=ContextConfidence.EXPLICIT, timestamp=datetime.now())
        
        with pytest.raises(ValueError):
            await validator.validate_context(context)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
