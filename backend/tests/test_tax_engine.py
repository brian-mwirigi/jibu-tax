"""
File: backend/tests/test_tax_engine.py
Description:
    Unit Tests for Deterministic Tax Engine.
    - Tests 16% standard VAT calculations.
    - Tests First Schedule VAT exemption keyword matching (maize, potatoes, milk).
    - Tests Second Schedule zero-rated items (fertilizer, seeds).
    - Verifies zero arithmetic hallucination guarantees.
"""
