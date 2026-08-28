"""
File: backend/app/services/kra_service.py
Description:
    KRA PIN Checker & Taxpayer Verification Service (Zero-Trust Gateway).
    - Validates KRA PIN syntax format.
    - Queries KRA eCitizen/eTIMS registry to retrieve taxpayer legal identity and tax standing.
    - Prevents LLM direct access to sensitive government endpoints.
"""
