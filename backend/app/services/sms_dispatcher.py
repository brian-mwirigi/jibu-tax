"""
File: backend/app/services/sms_dispatcher.py
Description:
    Post-Call SMS Receipt Dispatch Service.
    - Formats concise SMS receipt messages containing invoice number, buyer name, total, and official KRA verification link.
    - Dispatches SMS receipts to informal traders via Africa's Talking API / Twilio.
    - Provides mock mode for local offline testing.
"""
