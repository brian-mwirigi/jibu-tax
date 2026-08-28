"""
File: backend/app/api/v1/webhooks.py
Description:
    API Routes for ElevenLabs Real-Time Agent Webhooks.
    - POST /api/v1/tools/validate-buyer: Mid-call tool for real-time buyer PIN lookup.
    - POST /api/v1/tools/calculate-tax: Mid-call tool for deterministic VAT calculation.
    - POST /api/v1/tools/file-invoice: Mid-call tool to generate official eTIMS invoice upon verbal confirmation.
    - POST /api/v1/tools/post-call: Post-call webhook triggered when conversation ends to dispatch SMS receipt.
"""
