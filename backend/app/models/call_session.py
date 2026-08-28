"""
File: backend/app/models/call_session.py
Description:
    ElevenLabs Voice Call Session Log Model.
    - Records metadata and execution traces for incoming trader voice calls.
    - Fields include:
        * session_id: ElevenLabs unique call session identifier.
        * caller_phone: Trader's dial-in MSISDN.
        * duration_seconds: Call length.
        * language: Swahili, English, or Sheng.
        * transcript: Full voice call transcript.
        * extracted_commodity, extracted_quantity, extracted_price, extracted_buyer_pin.
        * pin_verified, invoice_generated, invoice_number, sms_dispatched flags.
"""
