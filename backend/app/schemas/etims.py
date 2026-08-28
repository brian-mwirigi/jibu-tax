"""
File: backend/app/schemas/etims.py
Description:
    Pydantic Schemas for eTIMS Invoice Generation.
    - InvoiceItemCreate: Schema for adding items with HS code, quantity, and unit price.
    - CreateInvoiceRequest: Payload for creating a fiscal invoice (seller/buyer info, item list, SMS flag).
    - InvoiceItemResponse: Serialized invoice item data.
    - InvoiceResponse: Full eTIMS response containing invoice number, control code, grand total, and QR verification link.
"""
