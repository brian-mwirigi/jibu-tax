# Part 2: Conversational State Machine & Audio Orchestrator

Handles dynamic voice conversation flow, entity extraction, and async backend validation for JibuTax.

## Overview

This is the voice intelligence layer that:
- Extracts entities from user speech (item, quantity, price, buyer PIN)
- Manages conversation state (greeting → item → qty → price → PIN → validate → file)
- Makes non-blocking async calls to Part 1 (security middleware)
- Handles user corrections gracefully
- Prevents invalid state transitions

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Locally

```bash
python -m uvicorn elevenlabs_webhook:app --reload --port 8001
```

Server will start at: `http://localhost:8001`

### 4. Run Tests

```bash
pytest test_conversation_state_machine.py -v
```

## Project Structure

```
orchestrator/
├── conversation_state_machine.py   # Core state machine logic
├── elevenlabs_webhook.py           # FastAPI webhooks for ElevenLabs
├── test_conversation_state_machine.py  # Comprehensive tests
├── docs/
│   ├── PART2_ORCHESTRATOR_GUIDE.md      # Architecture deep dive
│   └── PART2_QUICK_REFERENCE.md         # Quick lookup cheat sheet
├── requirements.txt
├── .env.example
└── README.md (this file)
```

## API Endpoints

### Webhooks (from ElevenLabs)

- `POST /webhook/elevenlabs/transcript` - Receive user speech transcript
- `POST /webhook/elevenlabs/call-start` - Initialize new call
- `POST /webhook/elevenlabs/call-end` - Finalize call

### Debug Endpoints

- `GET /debug/call/{call_id}` - Get conversation state
- `GET /debug/active-calls` - List all active calls
- `GET /health` - Health check

### Test Endpoints

- `POST /test/simulate-call` - Simulate full conversation
- `POST /test/partial-transcript` - Test partial transcript handling

## Integration with Other Parts

### Part 1: Security Middleware
- Sends validated context via HTTP to Part 1's `/webhook/voice-transaction`
- Receives validation result (buyer_valid, total_amount, tax_amount)
- Async (non-blocking) calls via `BackendValidator`

### Part 6: Telemetry Dashboard
- Exposes real-time call state via `/debug/active-calls`
- Returns conversation snapshots via `/debug/call/{call_id}`

## Key Classes

### ConversationContext
Source of truth for what we know about a call.

```python
context = ConversationContext(user_id="call-123")
context.item_name = ExtractedEntity(value="maize", ...)
context.quantity = ExtractedEntity(value=50, ...)
context.are_critical_entities_complete()
context.calculate_total_amount()
```

### EntityExtractor
Parses voice transcript into structured entities.

```python
extractor = EntityExtractor()
context, extracted = extractor.extract_from_transcript("I sold 50 kilos of maize", context)
```

### StateTransition
Guards against invalid conversation flows.

```python
StateTransition.assert_transition(from_state, to_state)  # Raises ValueError if invalid
```

### BackendValidator
Async calls to Part 1 (non-blocking).

```python
validator = BackendValidator()
result = await validator.validate_context(context)
```

### ConversationOrchestrator
Main state machine engine.

```python
orchestrator = ConversationOrchestrator()
response = await orchestrator.process_transcript_chunk(user_id, transcript, is_final=True)
```

## Development

### Run Tests

```bash
pytest test_conversation_state_machine.py -v
```

### Simulate a Call

```bash
curl -X POST http://localhost:8001/test/simulate-call | jq .
```

### Debug a Call

```bash
curl http://localhost:8001/debug/call/call-123 | jq .
curl http://localhost:8001/debug/active-calls | jq .
```

## Deployment

### To Render

1. Create new Web Service on Render
2. Connect your GitHub repo
3. Set **Build Command:** `pip install -r orchestrator/requirements.txt`
4. Set **Start Command:** `cd orchestrator && uvicorn elevenlabs_webhook:app --host 0.0.0.0 --port 8001`
5. Add environment variables from `.env.example`

## Architecture

For detailed architecture, see: `docs/PART2_ORCHESTRATOR_GUIDE.md`  
For quick reference, see: `docs/PART2_QUICK_REFERENCE.md`

---

**Built with ❤️ for JibuTax @ Cursor Kenya Hackathon 2026**
