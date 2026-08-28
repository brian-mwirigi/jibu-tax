# Part 2: Quick Reference Cheat Sheet

**You're building:** Dynamic conversational state machine + ElevenLabs webhook handler  
**Why it matters:** Voice AI at scale fails without proper state management + async handling  
**Key challenge:** Non-blocking backend validation + handling user corrections

---

## 📂 Files You Have

| File | Purpose | What To Do |
|------|---------|-----------|
| `conversation_state_machine.py` | Core logic: state machine, entity extraction, validation | Understand this first |
| `elevenlabs_webhook.py` | FastAPI webhooks for ElevenLabs real-time events | Deploy this on Render |
| `test_conversation_state_machine.py` | Unit + integration tests | Run: `pytest test_conversation_state_machine.py -v` |
| `PART2_ORCHESTRATOR_GUIDE.md` | Deep dive documentation | Read for detailed understanding |
| `PART2_QUICK_REFERENCE.md` | This file | Quick lookup |

---

## 🎯 5-Minute Overview

```python
# 1. Context: Stores what we know about THIS call
context = ConversationContext(user_id="call-123")
context.item_name = "maize"
context.quantity = 50
context.unit = "kg"
context.unit_price = 90
# → Ready to send to backend!

# 2. Extractor: Parse messy voice input
extractor = EntityExtractor()
context, extracted = extractor.extract_from_transcript(
    "I sold 50 kilos of maize for 4,500",
    context,
)
# → Identifies: item_name, quantity, unit, unit_price

# 3. State Machine: Enforce valid conversation flows
# greeting → awaiting_item → awaiting_quantity → ... → complete
StateTransition.assert_transition(from_state, to_state)

# 4. Backend Validator: Async call to Part 1 (non-blocking!)
validator = BackendValidator()
result = await validator.validate_context(context)
# → Returns immediately; callback fires when validation completes

# 5. Orchestrator: Main engine that ties it all together
orchestrator = ConversationOrchestrator()
response = await orchestrator.process_transcript_chunk(
    user_id="call-123",
    transcript_chunk="I sold 50 kilos...",
    is_final=True,
)
# → Returns: {"action": "ask_for_price", "bot_message": "Bei gani?"}

# 6. Webhook Handler: Integration with ElevenLabs real-time API
handler = ElevenLabsWebhookHandler(orchestrator)
bot_message = await handler.handle_user_transcript(
    user_id="call-123",
    transcript="User said this",
    is_final=True,
)
# → ElevenLabs speaks this message
```

---

## 🔄 The Data Flow

```
User speaks
    ↓
ElevenLabs captures audio + transcribes
    ↓
ElevenLabs sends webhook: POST /webhook/elevenlabs/transcript
    {
      "call_id": "call-123",
      "user_transcript": "I sold 50 kilos of maize",
      "is_final": true
    }
    ↓
Your FastAPI: handle_user_transcript()
    ↓
EntityExtractor: Extract entities from transcript
    {
      "item_name": "maize",
      "quantity": 50,
      "unit": "kg"
    }
    ↓
Orchestrator: Decide next action
    - Missing: unit_price, buyer_pin
    - Action: "ask_for_unit_price"
    ↓
Return to ElevenLabs:
    {
      "bot_message": "Bei gani kwa kilo?"
    }
    ↓
ElevenLabs TTS: Speaks "Bei gani kwa kilo?"
    ↓
User says: "90 shillings"
    ↓
(repeat)
```

---

## 🗂️ Core Classes

### ConversationContext
```python
context = ConversationContext(user_id="call-123")

# Extract + store entities
context.item_name = ExtractedEntity(
    value="maize",
    confidence=ContextConfidence.EXPLICIT,
    timestamp=datetime.now(),
)

# Query state
context.are_critical_entities_complete()  # bool
context.get_missing_entities()            # ["quantity", "buyer_pin"]
context.calculate_total_amount()          # 50 * 90 = 4500

# Convert to backend format
payload = context.to_backend_payload()

# Audit trail
context.log_correction("quantity", 50, 60, "User said 'wait, 60'")
context.correction_history             # List of corrections
```

### EntityExtractor
```python
extractor = EntityExtractor()

# Extract from transcript
context, extracted = extractor.extract_from_transcript(
    "I sold 50 kilos of maize for 4,500",
    context,
)

# extracted = ["item_name", "quantity", "unit", "unit_price"]
# context updated with ExtractedEntity objects
```

### StateTransition
```python
# Check if transition is valid
StateTransition.can_transition(
    ConversationState.AWAITING_ITEM,
    ConversationState.AWAITING_QUANTITY,
)  # True

# Assert (raise if invalid)
StateTransition.assert_transition(from_state, to_state)  # Raises ValueError if invalid
```

### BackendValidator
```python
validator = BackendValidator(backend_url="http://localhost:8000")

# Async validation (non-blocking)
result = await validator.validate_context(
    context,
    callback_on_complete=my_callback,
)

# Returns immediately with mock response
# In production: httpx.AsyncClient makes real HTTP call
```

### ConversationOrchestrator
```python
orchestrator = ConversationOrchestrator()

# Main entry point
response = await orchestrator.process_transcript_chunk(
    user_id="call-123",
    transcript_chunk="I sold 50 kilos...",
    is_final=True,
)

# response = {
#   "action": "ask_for_unit_price",
#   "bot_message": "Bei gani?",
#   "state": "awaiting_unit_price",
#   "context_snapshot": {...}
# }
```

---

## 🚀 Quick Start (10 minutes)

```bash
# 1. Install pytest + dependencies
pip install pytest pytest-asyncio

# 2. Run tests
pytest test_conversation_state_machine.py -v

# 3. Test the orchestrator directly
python -c "
import asyncio
from conversation_state_machine import create_orchestrator

async def test():
    orch = create_orchestrator()
    r = await orch.process_transcript_chunk(
        'test-user',
        'I sold 50 kilos of maize for 4500',
        is_final=True,
    )
    print(r['bot_message'])

asyncio.run(test())
"

# 4. Run FastAPI locally
python -m uvicorn elevenlabs_webhook:app --reload --port 8001

# 5. Test webhook (in another terminal)
curl -X POST http://localhost:8001/test/simulate-call | jq .
```

---

## 🎤 ElevenLabs Webhook Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook/elevenlabs/transcript` | POST | Receive user speech transcript |
| `/webhook/elevenlabs/call-start` | POST | Initialize new call |
| `/webhook/elevenlabs/call-end` | POST | Finalize call + log |
| `/webhook/elevenlabs/error` | POST | Handle errors |

---

## 🔍 Debug Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/debug/call/{call_id}` | GET | Get current state of call | ConversationSnapshot |
| `/debug/active-calls` | GET | List all active calls | {total_active, calls} |
| `/health` | GET | Health check | {status, active_calls} |
| `/test/simulate-call` | POST | Simulate full conversation | Full conversation flow |
| `/test/partial-transcript` | POST | Test partial transcript | Context after partial |

---

## 📊 Conversation States (State Machine)

```
GREETING
    ↓
AWAITING_ITEM
    ↓
AWAITING_QUANTITY
    ↓
AWAITING_UNIT
    ↓
AWAITING_PRICE
    ↓
AWAITING_BUYER_PIN
    ↓
CONFIRMING
    ↓
VALIDATION_PENDING  ← (async backend call here)
    ├→ VALIDATION_SUCCESS
    │    ↓
    │    FILING
    │    ↓
    │    COMPLETE
    │
    └→ VALIDATION_FAILED
         ↓ (ask for correction)
         AWAITING_BUYER_PIN
         (loop back)
```

---

## 🐛 Common Issues & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| **Voice hangs 1s** | Backend call blocks orchestrator | Use `asyncio.create_task()` for non-blocking |
| **User correction ignored** | Context not updated | Call `extractor.extract_from_transcript()` on each chunk |
| **Invalid state transition** | Skipped a state | Add intermediate states to flow |
| **Context lost on new call** | Reused same user_id | Use unique call_id per call |
| **Price extracted wrong** | LLM hallucination | Validate: `total = quantity × unit_price` |

---

## ✅ Testing Checklist

```python
# Run these tests
pytest test_conversation_state_machine.py::TestConversationContext -v
pytest test_conversation_state_machine.py::TestEntityExtractor -v
pytest test_conversation_state_machine.py::TestStateTransition -v
pytest test_conversation_state_machine.py::TestConversationOrchestrator -v
pytest test_conversation_state_machine.py::TestEdgeCases -v

# Simulate call
curl -X POST http://localhost:8001/test/simulate-call

# Debug active calls
curl http://localhost:8001/debug/active-calls

# Check specific call
curl http://localhost:8001/debug/call/call-123
```

---

## 🔗 Integration Points

### To Part 1 (Security Middleware)
```python
# You send
payload = context.to_backend_payload()
# {
#   "item_name": "maize",
#   "quantity": 50,
#   "unit": "kg",
#   "unit_price": 90,
#   "buyer_pin": "P0512345670M"
# }

# They return
# {
#   "status": "success",
#   "buyer_valid": true,
#   "buyer_name": "Safari Hotel Limited",
#   "total_amount": 4500,
#   "tax_amount": 720
# }
```

### To Part 6 (Dashboard)
```python
# You expose
GET /debug/call/{call_id}  # Get context snapshot
GET /debug/active-calls    # List all calls
WebSocket /ws/call/{call_id}  # Real-time updates

# Dashboard shows
- State transitions in real-time
- Entity extraction as it happens
- Backend response latency
- Conversation flow visualization
```

---

## 💡 Pro Tips

1. **Always use async/await**
   ```python
   # ✗ Wrong (blocks!)
   response = requests.post(backend_url, json=payload)
   
   # ✓ Right (non-blocking)
   result = await httpx.AsyncClient().post(backend_url, json=payload)
   ```

2. **Test corrections early**
   ```python
   # User says: "50... wait, 60"
   # Your code should extract: quantity=60
   context.log_correction("quantity", 50, 60, "User corrected")
   ```

3. **Validate calculations**
   ```python
   # Never trust LLM extraction
   assert context.calculate_total_amount() == expected_total
   ```

4. **Handle Swahili + English**
   ```python
   item_keywords = {
       "maize": ["maize", "mahindi", "corn"],  # English + Swahili
   }
   ```

5. **Log everything**
   ```python
   logger.info(f"[{call_id}] State: {state}")
   logger.debug(f"Extracted: {extracted}")
   logger.error(f"Failed: {error}")
   ```

---

## 🎬 Demo Script

For judges/demo:

```bash
# 1. Start your backend
python -m uvicorn elevenlabs_webhook:app --reload --port 8001

# 2. Simulate call
curl -X POST http://localhost:8001/test/simulate-call -s | jq .

# Shows:
# - conversation_flow: [user says, bot responds, ...]
# - final_state: completed transaction with all entities
# - No manual entries required!
```

---

## 📞 Team Contact Points

**When to talk to Part 1 (Security Middleware):**
- Your backend validation endpoint ready?
- API format for KRA PIN validation?
- Expected response schema?

**When to talk to Part 3 (Tax Dispatcher):**
- How to trigger receipt filing?
- QR code generation input?
- SMS dispatch webhook?

**When to talk to Part 6 (Dashboard):**
- WebSocket format for real-time updates?
- Metrics you want to expose?
- Call state visualization?

---

## 🚀 Deployment Checklist

- [ ] All tests pass: `pytest test_conversation_state_machine.py -v`
- [ ] No LLM touches financial data
- [ ] Backend validation is async (non-blocking)
- [ ] State transitions guarded (can't enter invalid states)
- [ ] Multiple concurrent calls work (separate contexts per call_id)
- [ ] Corrections handled (user can say "wait, I meant 60")
- [ ] Debug endpoints working (for telemetry dashboard)
- [ ] Error handling for network failures
- [ ] Logging at all critical points

---

## 🏆 Success = 

✅ Voice call → Transcript → Context → Backend validation → Bot response  
✅ No manual data entry  
✅ No LLM touching compliance logic  
✅ Async (non-blocking)  
✅ Handles corrections gracefully  
✅ Full audit trail  
✅ Integration with Parts 1, 3, 6  

**You're building the voice intelligence layer. Let's ship it! 🎤💚**

