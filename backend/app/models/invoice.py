"""
File: backend/app/models/invoice.py
Description:
    eTIMS Fiscal Invoice and Line Items Models.
    - Captures official electronic tax invoices generated via OSCU engine.
    - Fields include:
        * invoice_number: Sequential eTIMS invoice number (e.g. INV-2026-00001).
        * oscu_control_code: Cryptographic control code signature.
        * oscu_device_id: KRA fiscal device identifier.
        * trader_phone: Primary identifier for informal traders (dial-in MSISDN).
        * trader_pin (Optional): Seller's KRA PIN if onboarded; otherwise mapped via reverse-invoicing or phone.
        * trader_name: Seller's trading or business name.
        * buyer_name: Buyer's name or 'Walk-in Consumer' for retail sales.
        * buyer_pin (Optional): Mandatory only for B2B transactions claiming tax deduction; OPTIONAL / None for retail consumer (B2C) sales.
        * total_taxable_amount, total_vat_amount, total_exempt_amount, grand_total.
        * qr_code_url / qr_code_base64: Official KRA verification link and QR image.
        * sms_status: Delivery state of customer SMS receipt.
    - InvoiceItem model captures individual line items, HS code, quantity, unit price, and VAT rate.
"""
