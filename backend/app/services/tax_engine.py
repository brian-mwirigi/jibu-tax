"""
File: backend/app/services/tax_engine.py
Description:
    Deterministic Tax Engine for Kenya VAT & Commodity Classification.
    - Deterministic, non-AI Python functions to compute exact tax figures.
    - Classifies commodities according to Kenya VAT Act:
        * 16% Standard VAT (manufactured goods, services).
        * First Schedule VAT Exempt (unprocessed agricultural products: maize, milk, vegetables).
        * Second Schedule Zero-Rated (fertilizers, seeds, exports).
    - Generates natural Swahili and English spoken summaries for the voice assistant.
"""
