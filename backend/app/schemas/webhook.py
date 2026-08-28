"""
File: backend/app/schemas/webhook.py
Description:
    Pydantic Schemas for ElevenLabs Real-Time Agent Webhooks.
    - ValidateBuyerWebhookInput / Output: Real-time buyer PIN verification mid-call.
    - CalculateTaxWebhookInput / Output: Real-time deterministic tax calculation mid-call.
    - FileInvoiceWebhookInput / Output: Real-time eTIMS invoice generation mid-call.
    - ElevenLabsPostCallPayload: Webhook payload received on call hangup with full transcript and duration.
"""
