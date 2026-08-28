"""
File: backend/app/services/oscu_engine.py
Description:
    eTIMS OSCU (Online Sales Control Unit) Engine.
    - Generates sequential fiscal electronic invoice numbers.
    - Generates cryptographic OSCU control code signatures.
    - Constructs verifiable KRA invoice checking URLs and QR code payloads.
    - Persists compliance invoice data into PostgreSQL.
"""
