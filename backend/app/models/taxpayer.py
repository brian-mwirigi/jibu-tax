"""
File: backend/app/models/taxpayer.py
Description:
    Taxpayer Database Model (KRA Registry).
    - Table for storing verified taxpayer PINs and legal business names.
    - Fields include:
        * pin: Unique alphanumeric KRA PIN (Primary Key).
        * legal_name: Official registered business or individual name.
        * trading_name: Trade name / DBA.
        * status: Status with KRA (ACTIVE, SUSPENDED, CANCELLED).
        * taxpayer_type: INDIVIDUAL, COMPANY, or PARASTOTAL.
        * vat_registered: Boolean indicating if entity is registered for VAT.
        * etims_onboarded: Boolean indicating eTIMS compliance status.
"""
