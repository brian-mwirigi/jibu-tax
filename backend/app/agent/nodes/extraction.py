"""
File: backend/app/agent/nodes/extraction.py
Description:
    Node 1: Entity Extraction Node powered by Google Gemini (Gemini 1.5 Flash).
    Parses unstructured Swahili/English/Sheng audio transcripts into structured ExtractedSale entities.
"""

import os
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.state import JibuTaxState, ExtractedSale
from app.agent.prompts import EXTRACTION_SYSTEM_PROMPT


def get_llm():
    """Initializes Google Gemini model with zero temperature for deterministic parsing."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=api_key,
        temperature=0.0,
    )


def extract_sale_node(state: JibuTaxState) -> Dict[str, Any]:
    """
    Node 1 Handler:
    Extracts item_name, quantity, unit_price, and buyer_pin from trader's voice transcript.
    """
    transcript = state.get("transcript", "").strip()
    if not transcript:
        return {
            "sale": None,
            "extraction_error": "Transcript is empty.",
            "call_status": "NEEDS_CLARIFICATION",
        }

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ExtractedSale)

        messages = [
            SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=f"Trader Audio Transcript: \"{transcript}\"")
        ]

        extracted: ExtractedSale = structured_llm.invoke(messages)
        return {
            "sale": extracted,
            "extraction_error": None,
            "call_status": "IN_PROGRESS",
        }
    except Exception as e:
        return {
            "sale": None,
            "extraction_error": f"Failed to extract entities: {str(e)}",
            "call_status": "NEEDS_CLARIFICATION",
        }
