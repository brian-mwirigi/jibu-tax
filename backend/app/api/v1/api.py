"""
File: backend/app/api/v1/api.py
Description:
    API Version 1 Router Aggregator.
    - Aggregates sub-routers into a single APIRouter instance:
        * /kra: KRA PIN verification endpoints.
        * /invoices: eTIMS electronic invoice management endpoints.
        * /tools: ElevenLabs conversational voice agent webhook endpoints.
        * /stats: Dashboard analytics & compliance metrics endpoints.
"""
