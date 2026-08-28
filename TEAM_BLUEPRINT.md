# Technical Blueprint: 6-Person Engineering Team Roles

> **JibuTax 48-Hour Hackathon Execution Plan**  
> To win in 48 hours without blocking each other, everyone must agree on the JSON data structures at Hour 1, retreat to their local environments, and build these six distinct micro-architectures.

---

### Role 1: The Zero-Trust & MCP Infrastructure Engineer (Your Lane)

**The Mission:** Build the secure FastAPI shell, the Model Context Protocol (MCP) server, and the credential isolation vault. You are the "brakes" that keep the AI from doing anything illegal or hallucinated.

* **The Architecture:** You set up the main Render deployment (`render.yaml`). You build a Python FastAPI server that acts as the central router for the whole team.
* **The MCP Interception Layer:** You write the Pydantic tool schemas that the LLM is allowed to see (e.g., `verify_pin`, `submit_invoice`). But crucially, you write the middleware. When the LLM tries to call `submit_invoice`, your code intercepts it, strips the parameters, and runs a secondary strict validation before actually letting the tool fire.
* **Zero-Trust Setup:** You manage the `.env` variables and ensure the API keys for KRA/eCitizen are injected only at runtime inside isolated Python functions, meaning the LLM's prompt context physically cannot access them.

---

### Role 2: The Conversational State & Audio Orchestrator

**The Mission:** Tame the unstructured latency of human speech via ElevenLabs Webhooks.

* **The Architecture:** This engineer lives in the ElevenLabs dashboard and the FastAPI webhook routing file. They configure the voice agent's system prompt to handle Sheng/Swahili/English code-switching natively.
* **State Machine Management:** Human speech is messy. The user might pause, mumble, or correct themselves. This engineer handles the webhook logic that tells ElevenLabs to dynamically inject conversational fillers (e.g., *"Give me one second to check that PIN on the government portal"*) while asynchronously waiting for Role 1's backend to respond.
* **Post-Call Triggers:** They write the exact logic that fires when the user hangs up, triggering the background worker that finalizes the database save and sends the receipt.

---

### Role 3: The Cryptographic eTIMS Simulator & API Integrator

**The Mission:** Build the bridge to the government infrastructure and simulate what you can't access in 48 hours.

* **The Live Integration:** They write the raw HTTP Python clients to securely query the eCitizen developer APIs. Specifically, they integrate the `PIN Checker by PIN` API, configuring it to validate a taxpayer's PIN against the live iTax database within the 500ms SLA.
* **The eTIMS Simulator:** Since full eTIMS production access requires KYC, this engineer builds a mock simulator of the `eTIMS OSCU Integrator Automated Testing` endpoint. This isn't a basic JSON return; it must be mathematically rigorous. They write the cryptographic logic (SHA-256) to hash the invoice data to simulate a KRA control number, dynamically generate a QR code image from that hash, and write the integration to Africa's Talking (or Twilio) to SMS the QR code to the phone.

---

### Role 4: The Multi-Agent Routing Logic (LangGraph Engineer)

**The Mission:** Build the "brain" of the system using Claude 3.5 Sonnet and LangGraph, routing the data deterministically.

* **The Architecture:** They define the rigid `TypedDict` state (Memory) that passes between nodes.
* **Node Construction:** They build the Directed Acyclic Graph (DAG):
  * *Node 1 (Extraction):* Uses Claude to pull entities from the voice transcript.
  * *Node 2 (Validation):* Forces Claude to use Role 1's MCP tools to hit Role 3's PIN Checker. If it fails, the graph routes backward.
  * *Node 3 (Deterministic Math):* A pure Python node (no AI) that takes the extracted items and calculates the exact 16% VAT.
* **Checkpointer Integration:** They configure LangGraph's `MemorySaver` using the user's phone number as the `thread_id` so that if the live call drops or lags, the AI's state is preserved perfectly.

---

### Role 5: The Asynchronous Ledger & Tax Filing Engine

**The Mission:** Turn a single receipt generator into a massive, automated compliance engine.

* **The Architecture:** They provision the Render PostgreSQL database. They write the SQLModel schemas to save every successful transaction into an immutable ledger. They configure a background queue (like Celery/Redis) so database writes never slow down the live voice call.
* **The Cron Jobs:** They write the end-of-month automation scripts. On the 18th of the month, their code evaluates the database. If there are sales, it formats the JSON payload and targets the `TOT Return Filing` API to automate Turnover Tax. If the database is empty, it automatically hits the `NIL Return Filling` API to prevent the user from being fined.

---

### Role 6: The WebSocket Telemetry Dashboard (Frontend)

**The Mission:** Build the "demo magic." For a voice-first app, the judges need a visual representation of the deep backend complexity.

* **The Architecture:** This engineer builds a dark-mode Next.js dashboard using TypeScript and Tailwind.
* **Real-Time Telemetry:** They build a live WebSocket client that connects to Role 1's FastAPI server. During the live pitch, as the presenter speaks into the phone, this UI must flash in real-time. It intercepts the backend logs and visualizes them on the projector: showing the LangGraph nodes lighting up, displaying the 500ms latency of the KRA PIN check, and finally rendering the generated cryptographic QR code on the screen the exact millisecond the SMS hits the presenter's phone.
