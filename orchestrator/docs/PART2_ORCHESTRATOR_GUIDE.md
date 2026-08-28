# Part 2: Conversational State & Audio Orchestrator

**Your Role:** Build the dynamic conversation state machine that makes voice AI work in the real world.

**Why This Matters:** Voice AI fails at scale because of latency, interruptions, and context loss. You're building the system that prevents hallucination, handles user corrections gracefully, and bridges real-time voice input to async backend validation.

---

## 🎯 Your Hard Problem

**The Challenge:**
- User speaks in fragments: "I sold... uh... 50 kilos... wait, 60... of maize"
- You must extract "60 kilos of maize" from that messy input
- You must NOT ask redundantly ("How many again?")
- You must handle corrections ("I meant 60, not 50")
- You must NOT block the voice call while validating with backend
- You must dynamically resume when validation completes

**The Solution:**
A multi-layered state machine that:
1. Tracks conversation state (greeting → awaiting_item → awaiting_quantity → ...)
2. Extracts entities with confidence scores
3. Makes async backend calls without blocking voice
4. Handles interruptions, corrections, and user hesitations
5. Dynamically resumes conversation based on backend response

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  ELEVENLABS REAL-TIME VOICE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  User speaks: "I sold 50 kilos of maize for 4,500 to Safari..."│
│                                                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP Webhook (user_transcript)
                     │ {transcript: "50 kilos...", is_final: true}
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           ELEVENLABS_WEBHOOK.PY (FastAPI Endpoint)              │
├─────────────────────────────────────────────────────────────────┤
│  POST /webhook/elevenlabs/transcript                            │
│  - Receives transcript chunk                                     │
│  - Extracts call_id, is_final flag                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         CONVERSATION_STATE_MACHINE.PY (Orchestrator)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ 1. ConversationContext (state of THIS call)                     │
│    ├─ item_name: "maize" (with confidence, timestamp)           │
│    ├─ quantity: 50 (with confidence, timestamp)                 │
│    ├─ unit: "kilos"                                             │
│    ├─ unit_price: 4500                                          │
│    ├─ buyer_pin: "P0512345670M"                                 │
│    └─ current_state: "AWAITING_BUYER_PIN"                       │
│                                                                   │
│ 2. EntityExtractor (parse voice transcript)                     │
│    ├─ Keyword matching (item classification)                    │
│    ├─ Regex for numbers (quantity, price, PIN)                  │
│    ├─ Proper noun extraction (buyer name)                       │
│    └─ Correction detection ("wait, I meant...")                 │
│                                                                   │
│ 3. StateTransition (enforce valid flows)                        │
│    ├─ greeting → awaiting_item → awaiting_quantity → ...        │
│    ├─ validation_pending → validation_success OR validation_failed
│    └─ Guards against invalid transitions                         │
│                                                                   │
│ 4. BackendValidator (async to Part 1)                           │
│    ├─ Build payload from context                                │
│    ├─ HTTP call to Part 1's MCP endpoint                        │
│    ├─ Returns immediately (non-blocking)                        │
│    └─ Callback when response arrives                            │
│                                                                   │
│ 5. ConversationOrchestrator (main state machine)                │
│    ├─ process_transcript_chunk(user_id, transcript, is_final)   │
│    ├─ Decides next action (ask_for_*, validate, file)           │
│    └─ Returns bot response                                       │
│                                                                   │
│ 6. ElevenLabsWebhookHandler (integrates with voice)             │
│    └─ Wraps orchestrator for ElevenLabs APIs                    │
│                                                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           ELEVENLABS_WEBHOOK.PY (Return Response)               │
├─────────────────────────────────────────────────────────────────┤
│  BotResponsePayload:                                             │
│  {                                                                │
│    "call_id": "call-123",                                        │
│    "bot_message": "Sawa! PIN yao ni nini?",                     │
│    "should_wait_for_input": true,                               │
│    "context_snapshot": {...}                                     │
│  }                                                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ELEVENLABS (Agent Speaks Back)                 │
├─────────────────────────────────────────────────────────────────┤
│  ElevenLabs TTS: "Sawa! PIN yao ni nini?"                       │
│  Agent waits for user to speak again...                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Components Explained

### 1. **ConversationContext**
The SOURCE OF TRUTH for what we know about this call.

```python
context = ConversationContext(user_id="call-123")

# Extracted entities (with confidence tracking)
context.item_name = ExtractedEntity(
    value="maize",
    confidence=ContextConfidence.EXPLICIT,  # User clearly said it
    timestamp=datetime.now(),
    original_text="I sold 50 kilos of maize",
)

# Query missing entities
missing = context.get_missing_entities()  # ["unit_price", "buyer_pin", ...]

# Deterministic recalculation (catch LLM hallucination)
total = context.calculate_total_amount()  # 50 * unit_price

# Convert to backend payload (for Part 1)
payload = context.to_backend_payload()
# {
#   "item_name": "maize",
#   "quantity": 50,
#   "unit": "kg",
#   "unit_price": 90,
#   "buyer_pin": "P0512345670M",
# }
```

### 2. **EntityExtractor**
Parses messy voice input into structured data.

```python
extractor = EntityExtractor()

# User rambles: "I sold, uh, 50... no wait, 60 kilos of maize"
context, newly_extracted = extractor.extract_from_transcript(
    "60 kilos of maize",  # We parse the final/corrected version
    existing_context,
)

# Returns: 
# - context (updated with extracted entities)
# - newly_extracted (["quantity", "item_name"])

# Extraction strategy:
# - Keywords: "maize", "mahindi", "grain" → item_name
# - Regex numbers: r'\d+' → quantity, price
# - KRA PIN format: r'P\d{10}[A-Z]' → buyer_pin
# - Proper nouns: "Safari Hotel" → buyer_name
```

### 3. **StateTransition**
Enforces valid conversation flows (prevents invalid states).

```python
# Valid flow:
greeting → awaiting_item → awaiting_quantity → awaiting_unit → 
awaiting_price → awaiting_buyer_pin → confirming → validation_pending → 
validation_success → filing → complete

# Invalid (blocked):
awaiting_item → confirming  # Missing quantity, unit, price!
validation_pending → complete  # Missing validation_success!

# Guard:
StateTransition.assert_transition(
    from_state=ConversationState.AWAITING_QUANTITY,
    to_state=ConversationState.AWAITING_PRICE,  # Valid ✓
)

StateTransition.assert_transition(
    from_state=ConversationState.AWAITING_QUANTITY,
    to_state=ConversationState.COMPLETE,  # Invalid ✗ → Exception
)
```

### 4. **BackendValidator**
Async communication with Part 1 (security middleware) without blocking voice.

```python
validator = BackendValidator(backend_url="http://localhost:8000")

# Non-blocking call
result = await validator.validate_context(
    context=context,
    callback_on_complete=my_callback_function,
)

# Returns immediately with mock result
# In production: httpx.AsyncClient for real HTTP

# Callback pattern:
async def my_callback(result):
    if result["status"] == "success":
        # Resume conversation: "Receipt filed!"
    elif result["status"] == "error":
        # Resume: "PIN not found. Let me ask again."
```

### 5. **ConversationOrchestrator**
The main state machine engine.

```python
orchestrator = ConversationOrchestrator(backend_url="...")

# Process a chunk of transcript
response = await orchestrator.process_transcript_chunk(
    user_id="call-123",
    transcript_chunk="I sold 50 kilos of maize for 4,500",
    is_final=True,
)

# Response:
# {
#   "action": "ask_for_buyer_pin",
#   "bot_message": "Sawa! 50 kilos × 90 = 4,500 KSh. PIN yao?",
#   "state": "awaiting_buyer_pin",
#   "context_snapshot": {...}
# }

# The orchestrator decides:
# 1. What entities are missing?
# 2. Have we validated with backend yet?
# 3. Did validation succeed or fail?
# 4. What should the bot say next?
```

### 6. **ElevenLabsWebhookHandler**
Integrates the orchestrator with real voice calls.

```python
handler = ElevenLabsWebhookHandler(orchestrator)

# Called by FastAPI when ElevenLabs sends webhook
bot_message = await handler.handle_user_transcript(
    user_id="call-123",
    transcript="I sold 50 kilos...",
    is_final=True,
)

# Returns the text for ElevenLabs TTS to speak:
# "Sawa! PIN yao ni nini?"
```

---

## 🔄 Conversation Flow Example

**Scenario:** User calls and sells maize to Safari Hotel.

```
Time 0s:   ElevenLabs picks up
           Bot: "Habari! Unachouzalisha leo?"
           
Time 1s:   User: "I sold 50 kilos of maize"
           
           [WEBHOOK] POST /webhook/elevenlabs/transcript
           {
             "call_id": "call-123",
             "transcript": "I sold 50 kilos of maize",
             "is_final": true
           }
           
           [ORCHESTRATOR]
           - extract_from_transcript()
             → item_name: "maize" ✓
             → quantity: 50 ✓
             → unit: (not yet) ✗
           - decide_next_action()
             → missing: ["unit", "unit_price", "buyer_pin"]
             → action: "ask_for_unit"
           
           [RESPONSE]
           {
             "bot_message": "Kitengo gani? Kilos, bags?"
           }
           
           Bot: "Kitengo gani? Kilos, bags?"

Time 2s:   User: "Kilos, for 90 shillings each"
           
           [WEBHOOK] POST /webhook/elevenlabs/transcript
           {
             "transcript": "Kilos, for 90 shillings each",
             "is_final": true
           }
           
           [ORCHESTRATOR]
           - extract_from_transcript()
             → unit: "kg" (from "kilos") ✓
             → unit_price: 90 ✓
           - decide_next_action()
             → missing: ["buyer_pin"]
             → action: "ask_for_buyer_pin"
           
           [RESPONSE]
           {
             "bot_message": "Sawa! 50 kg × 90 = 4,500 KSh. PIN yao ni nini?"
           }
           
           Bot: "Sawa! 50 kg × 90 = 4,500 KSh. PIN yao ni nini?"

Time 3s:   User: "Safari Hotel, P0512345670M"
           
           [WEBHOOK] POST /webhook/elevenlabs/transcript
           {
             "transcript": "Safari Hotel, P0512345670M",
             "is_final": true
           }
           
           [ORCHESTRATOR]
           - extract_from_transcript()
             → buyer_name: "Safari Hotel" ✓
             → buyer_pin: "P0512345670M" ✓
           - decide_next_action()
             → all entities complete! ✓
             → action: "validate_with_backend"
           
           [ASYNC VALIDATION] (Non-blocking! Bot keeps speaking)
           - Context → Backend via HTTP
           - Backend validates PIN with KRA
           - Response arrives in ~500ms
           
           [RESPONSE]
           {
             "bot_message": "Sawa! Ndiyo? (confirming transaction...)"
           }
           
           Bot: "Sawa! Ndiyo?"

Time 3.5s: [Backend validation completes]
           Result: PIN valid! Buyer = "Safari Hotel Limited"
           
           [Async callback updates state]
           → validation_success ✓
           
           Bot: "Njema! Receipt inasimuliwa na KRA..."
           
           [In background]
           - File receipt with KRA (Part 3)
           - Generate QR code (Part 3)
           - Dispatch SMS (Part 3)
           
           Bot: "Receipt filed! SMS itakuja haraka."

Time 4s:   [Call ends]
           [WEBHOOK] POST /webhook/elevenlabs/call-end
           
           [BACKGROUND TASK]
           - Log transaction to DB
           - Fire analytics
           - Clean up context
```

---

## 🛠️ How to Build & Test

### Phase 1: Set Up (30 minutes)

```bash
# 1. Create conversation_state_machine.py (you have it!)
# 2. Create elevenlabs_webhook.py (you have it!)

# 3. Install dependencies
pip install fastapi httpx pydantic asyncio

# 4. Run locally
python -m uvicorn elevenlabs_webhook:app --reload --port 8001

# 5. Test the state machine
curl -X POST http://localhost:8001/test/simulate-call

# You should see a full simulated conversation flow
```

### Phase 2: Integration (1-2 hours)

```bash
# Connect to Part 1 (MCP Infrastructure)
# - Replace BackendValidator._call_backend_mock() with real HTTP call
# - Update backend_url to point to Part 1's Render app
# - Test end-to-end: voice → your orchestrator → Part 1 → validation

# Test checklist:
# ✓ Partial transcripts don't break context
# ✓ User corrections are handled (quantity: 50 → 60)
# ✓ State machine never enters invalid state
# ✓ Backend call doesn't block voice
# ✓ Callback resumes conversation after validation
# ✓ Multiple concurrent calls work (different call_ids)
```

### Phase 3: Edge Cases (1-2 hours)

Test these scenarios:

```python
# 1. User hesitation/correction
transcript = "I sold 50... wait, 60 kilos of maize"
# Should extract: quantity=60 (not 50)

# 2. Missing entity
transcript = "I sold maize"  # No quantity!
# Bot should ask: "Kiasi gani?"

# 3. Invalid PIN
transcript = "PIN P0000000000Z"
# Backend returns error
# Bot should ask: "PIN sijaipata. Karibu tena?"

# 4. Concurrent calls
call1_id = "call-001"
call2_id = "call-002"
# Must maintain separate contexts

# 5. Bilingual
transcript = "Niliuza mahindi 30 bags kwa 1,500 kila moja"  # Swahili
# Should extract correctly (keyword matching handles both languages)

# 6. User goes offline mid-call
# Connection drops during validation_pending
# WebSocket/HTTP timeout handling
```

---

## 🔗 Integration Points

### Part 1: Security Middleware (Zero-Trust & MCP Infrastructure)

**You Call Them:**
```python
# In BackendValidator.validate_context()
payload = context.to_backend_payload()
# POST http://part1-render-app.onrender.com/webhook/voice-transaction
response = await httpx.post(url, json=payload)
```

**They Validate:**
- KRA PIN (via eCitizen API)
- Total amount (recalculate: quantity × unit_price)
- Item classification (VAT-exempt or standard)

**They Return:**
```json
{
  "status": "success",
  "buyer_valid": true,
  "buyer_name": "Safari Hotel Limited",
  "total_amount": 4500,
  "tax_amount": 720,
  "message": "Receipt ready to file"
}
```

### Part 3: Tax Dispatcher & Crypto Engine

**You Tell Them:**
- Validated context (all entities extracted)
- Backend response (validation succeeded)
- Ready to file (state = validation_success)

**They Do:**
- Calculate exact tax liability
- Generate QR code
- File with eTIMS
- Dispatch SMS

### Part 6: Telemetry Dashboard (Next.js)

**You Expose:**
```python
GET /debug/call/{call_id}
# Returns real-time context snapshot

GET /debug/active-calls
# Returns all active calls + states

WebSocket /ws/call/{call_id}
# Real-time updates as conversation progresses
```

**Dashboard Shows:**
- State transitions in real-time
- Entity extraction as it happens
- Backend response → callback flow
- Latency metrics

---

## 📝 Code Walkthrough

### Extract Entity Example

```python
def extract_from_transcript(self, transcript: str, context: ConversationContext):
    """
    Input: "I sold 50 kilos of maize for 4,500 to Safari Hotel"
    Output: 
      - item_name: "maize"
      - quantity: 50
      - unit: "kg"
      - unit_price: 4500 (NO! This is total)
      - buyer_name: "Safari Hotel"
    """
    
    # ITEM: keyword matching
    for item, keywords in self.item_keywords.items():
        if any(kw in transcript.lower() for kw in keywords):
            context.item_name = ExtractedEntity(
                value=item,
                confidence=ContextConfidence.EXPLICIT,
                timestamp=datetime.now(),
                original_text=transcript,
            )
            break
    
    # QUANTITY: first number
    quantity = self._extract_number(transcript)  # 50
    if quantity:
        context.quantity = ExtractedEntity(value=quantity, ...)
    
    # UNIT: keyword matching
    if "kg" in transcript or "kilos" in transcript:
        context.unit = ExtractedEntity(value="kg", ...)
    
    # UNIT PRICE: ???
    # This is tricky! "4,500" in the transcript is TOTAL, not unit price.
    # We need to wait for next clarification.
    # OR ask: "So that's 4,500 total? Or per kilo?"
    
    # STRATEGY: If we have quantity and a price but not unit yet,
    # we assume the price is TOTAL (not per unit).
    # Once we have unit, Part 1 will recalculate and validate.
```

### State Transition Example

```python
# User says something, we extract entities, context updates
context.quantity = 60  # Updated from 50

# Now decide next action
def _decide_next_action(context, newly_extracted, is_final):
    missing = context.get_missing_entities()
    # ["unit_price", "buyer_pin", ...]
    
    if missing:
        return f"ask_for_{missing[0]}"  # "ask_for_unit_price"
    
    # All entities present, validate if we haven't yet
    if not context.backend_response:
        return "validate_with_backend"
    
    # Validation succeeded, file the receipt
    if context.backend_response["status"] == "success":
        return "file_receipt"
    
    # Validation failed, ask for correction
    if context.backend_response["status"] == "error":
        return "ask_for_pin_correction"
```

### Async Callback Example

```python
# When backend validation completes
async def _on_validation_complete(result: Dict[str, Any]):
    """
    Backend said: "PIN valid! Safari Hotel Limited. Total 4,500, tax 720."
    
    What we do:
    - Update context.backend_response
    - Trigger bot to resume conversation
    - In production: send signal to ElevenLabs to play next message
    """
    
    if result["status"] == "success":
        bot_message = (
            f"Njema! Receipt ready for {result['buyer_name']}. "
            f"Amount: {result['total_amount']} (tax: {result['tax_amount']}). "
            f"Sending SMS now..."
        )
    else:
        bot_message = result.get("message", "Validation failed. Karibu tena?")
    
    # In production: send to ElevenLabs via callback or webhook
    # logger.info(f"Bot should now say: {bot_message}")
```

---

## ⚠️ Common Pitfalls

### Pitfall 1: Blocking on Backend Call
❌ **Wrong:**
```python
response = requests.post(backend_url, json=payload)  # BLOCKS!
# Voice hangs for 500ms-1s. Bad UX.
```

✅ **Right:**
```python
asyncio.create_task(
    self.validator.validate_context(context, callback)
)  # Non-blocking!
# Bot says "let me check that PIN" while validation runs in background
```

### Pitfall 2: Losing Context on Correction
❌ **Wrong:**
```python
# User says: "50 kilos... wait, 60"
# You extract quantity=60
# But you don't audit the correction
# Later, you can't explain why quantity changed
```

✅ **Right:**
```python
context.log_correction(
    field="quantity",
    old_value=50,
    new_value=60,
    reason="User said 'wait, I meant 60'",
)
# Audit trail for debugging + analytics
```

### Pitfall 3: LLM Hallucination on Price
❌ **Wrong:**
```python
# ElevenLabs agent says:
# "I extracted unit_price: 4500"
# But transcript says: "4,500 for 50 kilos"
# That's 90 per kilo, not 4500!
```

✅ **Right:**
```python
total = context.calculate_total_amount()  # 50 * 90 = 4,500
# Verify: extracted total matches calculated total
# If not, ask user for clarification
```

### Pitfall 4: Invalid State Transitions
❌ **Wrong:**
```python
# context.current_state = ConversationState.VALIDATION_PENDING
# [Backend takes 1 second to respond]
# User hangs up
# You try: context.current_state = ConversationState.COMPLETE
# But no validation_success path!
```

✅ **Right:**
```python
StateTransition.assert_transition(
    from_state=ConversationState.VALIDATION_PENDING,
    to_state=ConversationState.COMPLETE,
)  # ✗ Raises ValueError! Catches bug early.

# Must go through: VALIDATION_PENDING → VALIDATION_SUCCESS → FILING → COMPLETE
```

---

## 🎯 Success Criteria

By the end of your work:

- ✅ Conversation state machine handles all conversation flows
- ✅ Partial transcripts don't break context (user still speaking)
- ✅ Corrections are detected and applied ("wait, I meant 60, not 50")
- ✅ Entity extraction with confidence scores
- ✅ State transitions guarded (can't jump invalid states)
- ✅ Backend validation is async (non-blocking voice)
- ✅ Multiple concurrent calls work (separate contexts)
- ✅ Edge cases handled (missing entities, invalid PIN, etc.)
- ✅ Debug endpoints expose real-time telemetry
- ✅ Integration with Part 1 (security middleware)
- ✅ Integration with Part 6 (telemetry dashboard)

---

## 🚀 Deployment Checklist

### Local Testing
- [ ] `python -m pytest tests/test_state_machine.py -v`
- [ ] `python -m pytest tests/test_entity_extraction.py -v`
- [ ] `POST /test/simulate-call` returns full conversation
- [ ] Debug endpoints work (`GET /debug/call/{call_id}`, etc.)

### Integration Testing
- [ ] Part 1 backend running (Part 1's Render app)
- [ ] Real validation calls to Part 1 succeed
- [ ] Async callbacks update conversation state
- [ ] Multiple concurrent calls handled

### Production Readiness
- [ ] Error handling for network failures
- [ ] Logging at INFO/DEBUG levels
- [ ] Context cleanup on call end
- [ ] Metrics exported (latency, success rate, etc.)
- [ ] Deploy to Render (separate service from main backend)

---

## 📚 Files You Have

1. **`conversation_state_machine.py`** — Core state machine logic
2. **`elevenlabs_webhook.py`** — FastAPI webhooks for ElevenLabs
3. **`PART2_ORCHESTRATOR_GUIDE.md`** — This file!

---

## 🤝 Team Integration

### What Part 1 (Security Middleware) Needs From You:
- Send well-formed payloads from `context.to_backend_payload()`
- Call them async (non-blocking)
- Handle their responses gracefully

### What You Need From Part 1:
- Validation endpoint: `POST /webhook/voice-transaction`
- Response format with status, buyer_valid, message, etc.

### What Part 3 (Tax Dispatcher) Needs From You:
- Validated context (state = validation_success)
- All entities extracted and confirmed

### What Part 6 (Dashboard) Needs From You:
- Debug endpoints: `GET /debug/call/{call_id}`, `GET /debug/active-calls`
- WebSocket connection for real-time updates
- Context snapshots with state transitions

---

## 💡 Pro Tips

1. **Use Pydantic models everywhere** — Type safety is your friend. Catch bugs at parse time.

2. **Log at the right level:**
   ```python
   logger.debug(f"Extracted entity: {entity}")  # For developers
   logger.info(f"[{call_id}] State transition: {from_state} → {to_state}")  # For ops
   ```

3. **Test corrections early:**
   ```python
   # User says: "50... wait, 60"
   # Parse both: [50, 60]
   # Use the last number: 60
   ```

4. **Handle Swahili + English:**
   ```python
   item_keywords = {
       "maize": ["maize", "mahindi", "corn"],  # English + Swahili
       "fish": ["fish", "samaki"],
   }
   ```

5. **Always calculate totals deterministically:**
   ```python
   # Never trust LLM extraction of price
   total = quantity * unit_price
   # Verify it matches backend's expectation
   ```

---

**You're building the orchestration layer that makes JibuTax feel magical. Let's go! 🎤💚**

