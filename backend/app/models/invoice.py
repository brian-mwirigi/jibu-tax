"""
File: backend/app/models/invoice.py
Description:
    eTIMS Fiscal Invoice and Line Items Models.
    - Captures official electronic tax invoices generated via OSCU engine.
    - Fields include:
        * invoice_number: Sequential eTIMS invoice number (e.g. INV-2026-00001).
        * oscu_control_code: Cryptographic control code signature.
        * oscu_device_id: KRA fiscal device identifier.
        * trader_pin / trader_name / trader_phone: Seller's credentials.
        * buyer_pin / buyer_name: Buyer's validated credentials.
        * total_taxable_amount, total_vat_amount, total_exempt_amount, grand_total.
        * qr_code_url / qr_code_base64: KRA verification link and QR image.
        * sms_status: Delivery state of customer SMS receipt.
    - InvoiceItem model captures individual line items, HS code, quantity, unit price, and VAT rate.
"""
