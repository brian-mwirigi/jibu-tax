"""
File: backend/app/schemas/etims.py
Description:
    Pydantic Schemas for eTIMS Invoice Generation.
    - InvoiceItemCreate: Schema for adding items with HS code, quantity, and unit price.
    - CreateInvoiceRequest: Payload for creating a fiscal invoice.
        * buyer_pin: OPTIONAL (populated for corporate B2B tax deductions; null for retail consumer sales).
        * trader_phone: Required (identifies informal trader by phone line).
        * trader_pin: Optional (seller PIN if available).
    - InvoiceItemResponse: Serialized invoice item data.
    - InvoiceResponse: Full eTIMS response containing invoice number, control code, grand total, and QR verification link.
"""
