"""
File: backend/tests/test_agent_robust.py
Description:
    Robust Automated Test Suite for Role 4 (LangGraph Multi-Agent Routing Engine).
    Covers:
      1. Agricultural produce extraction & First Schedule VAT exemption (0% VAT).
      2. Manufactured goods extraction & Standard 16% VAT deterministic math.
      3. Missing buyer PIN & conversational clarification branch routing.
      4. Invalid KRA PIN syntax rejection & retry handling.
      5. Multi-turn conversational memory persistence via MemorySaver checkpointer.
      6. FastAPI HTTP endpoints (/api/v1/agent/invoke & /api/v1/agent/state).
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app.agent.graph import build_jibutax_graph
from app.agent.state import JibuTaxState, ExtractedSale, BuyerValidationResult, TaxBreakdown
from app.agent.nodes.tax_math import calculate_tax_node
from app.agent.nodes.validation import validate_pin_node, should_route_after_validation
from app.main import app


@pytest.fixture(scope="module")
def agent_graph():
    """Builds a fresh instance of the compiled LangGraph StateGraph."""
    return build_jibutax_graph()


@pytest.fixture(scope="module")
def api_client():
    """FastAPI TestClient for HTTP endpoint testing."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# TEST 1: Agricultural Produce (First Schedule VAT Exempt) End-to-End
# ---------------------------------------------------------------------------
def test_agricultural_produce_exempt_tax(agent_graph):
    """
    Verifies that raw agricultural produce (maize) is extracted by Gemini,
    PIN is verified with KRA, and tax is deterministically calculated as EXEMPT (0% VAT).
    """
    phone = "+254711100001"
    transcript = "Nimeuzia Safari Hotel magunia 50 ya mahindi kwa shilingi mia nane kila moja, PIN yao ni P051234567M"

    input_state: JibuTaxState = {
        "caller_phone": phone,
        "transcript": transcript,
        "language": "sw",
        "sale": None,
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    config = {"configurable": {"thread_id": phone}}
    result = agent_graph.invoke(input_state, config=config)

    # 1. Verification of Gemini Extraction
    sale = result.get("sale")
    assert sale is not None, "Gemini failed to extract sale entities."
    assert "mahindi" in sale.item_name.lower()
    assert sale.quantity == 50.0
    assert sale.unit_price == 800.0
    assert sale.buyer_pin == "P051234567M"

    # 2. Verification of KRA PIN Validation
    buyer = result.get("buyer_validation")
    assert buyer is not None
    assert buyer.is_valid is True
    assert buyer.legal_name == "SAFARI HOTEL LIMITED"

    # 3. Verification of Deterministic Tax Engine
    tax = result.get("tax_breakdown")
    assert tax is not None
    assert tax.classification == "EXEMPT"
    assert tax.vat_amount == 0.0
    assert tax.grand_total == 40000.0
    assert tax.exempt_amount == 40000.0

    # 4. Pipeline Completion Status
    assert result.get("ready_for_filing") is True
    assert result.get("call_status") == "READY_FOR_OSCU"
    assert "40,000" in result.get("spoken_summary")


# ---------------------------------------------------------------------------
# TEST 2: Manufactured Goods (Standard 16% VAT) Deterministic Math
# ---------------------------------------------------------------------------
def test_standard_rated_cement_16_percent_vat(agent_graph):
    """
    Verifies that manufactured commodities (cement) are taxed at 16% VAT inclusive.
    Ensures ZERO arithmetic hallucination.
    """
    phone = "+254711100002"
    transcript = "I sold 20 bags of cement to Naivas Supermarket for 950 shillings each, buyer PIN is P051876543B"

    input_state: JibuTaxState = {
        "caller_phone": phone,
        "transcript": transcript,
        "language": "en",
        "sale": None,
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    config = {"configurable": {"thread_id": phone}}
    result = agent_graph.invoke(input_state, config=config)

    sale = result.get("sale")
    assert sale is not None
    assert "cement" in sale.item_name.lower()
    assert sale.quantity == 20.0
    assert sale.unit_price == 950.0

    tax = result.get("tax_breakdown")
    assert tax is not None
    assert tax.classification == "STANDARD_16"
    assert tax.grand_total == 19000.0  # 20 * 950
    # Deterministic: taxable = round(19000 / 1.16, 2) = 16379.31
    assert tax.taxable_amount == 16379.31
    # VAT = 19000 - 16379.31 = 2620.69
    assert tax.vat_amount == 2620.69
    assert result.get("ready_for_filing") is True


# ---------------------------------------------------------------------------
# TEST 3: Missing Buyer PIN & Clarification Branch Routing
# ---------------------------------------------------------------------------
def test_missing_buyer_pin_triggers_clarification(agent_graph):
    """
    Verifies that when speech is missing a buyer PIN, the conditional router
    branches to the Clarification Node rather than crashing or completing.
    """
    phone = "+254711100003"
    transcript = "Nimeuza viazi magunia kumi kwa shilingi elfu mbili kila moja."

    input_state: JibuTaxState = {
        "caller_phone": phone,
        "transcript": transcript,
        "language": "sw",
        "sale": None,
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    config = {"configurable": {"thread_id": phone}}
    result = agent_graph.invoke(input_state, config=config)

    assert result.get("call_status") == "NEEDS_CLARIFICATION"
    assert result.get("ready_for_filing") is False
    spoken = result.get("spoken_summary", "")
    assert "PIN ya mnunuzi haikutajwa" in spoken or "KRA PIN" in spoken


# ---------------------------------------------------------------------------
# TEST 4: Invalid PIN Format Rejection & Retry Threshold Escalation
# ---------------------------------------------------------------------------
def test_invalid_pin_format_and_retry_increment():
    """
    Unit test on validation node: confirms invalid regex fails and max retry router works.
    """
    # 1. Invalid regex format test
    bad_state: JibuTaxState = {
        "caller_phone": "+254711100004",
        "transcript": "Test",
        "language": "sw",
        "sale": ExtractedSale(item_name="cabbages", quantity=10, unit_price=50, buyer_pin="INVALID123"),
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    val_result = validate_pin_node(bad_state)
    buyer = val_result["buyer_validation"]
    assert buyer.is_valid is False
    assert "si sahihi" in buyer.error_message

    # 2. Test retry escalation router
    bad_state["buyer_validation"] = buyer
    bad_state["retry_count"] = 1
    assert should_route_after_validation(bad_state) == "clarify_pin"

    # When retry count reaches limit of 3, route to failed
    bad_state["retry_count"] = 3
    assert should_route_after_validation(bad_state) == "failed"


# ---------------------------------------------------------------------------
# TEST 5: Multi-Turn Conversational Memory (MemorySaver Checkpointer)
# ---------------------------------------------------------------------------
def test_multiturn_memory_checkpointing(agent_graph):
    """
    Tests that a trader's session is persisted in MemorySaver under caller_phone.
    Turn 1: User gives items without PIN (session pauses at Clarification).
    Turn 2: State is inspected, proving previous turn is held in checkpointer.
    """
    phone = "+254799888777"
    config = {"configurable": {"thread_id": phone}}

    # Turn 1: Provide items only
    turn_1_state: JibuTaxState = {
        "caller_phone": phone,
        "transcript": "Nimeuza nyanya crates tano kwa shilingi elfu tatu kila crate.",
        "language": "sw",
        "sale": None,
        "extraction_error": None,
        "buyer_validation": None,
        "retry_count": 0,
        "tax_breakdown": None,
        "spoken_summary": None,
        "ready_for_filing": False,
        "call_status": "IN_PROGRESS",
    }

    res_1 = agent_graph.invoke(turn_1_state, config=config)
    assert res_1["call_status"] == "NEEDS_CLARIFICATION"

    # Inspect checkpoint snapshot
    snapshot = agent_graph.get_state(config)
    assert snapshot is not None
    assert snapshot.values is not None
    checkpoint_sale = snapshot.values.get("sale")
    assert checkpoint_sale is not None
    assert "nyanya" in checkpoint_sale.item_name.lower()
    assert checkpoint_sale.quantity == 5.0


# ---------------------------------------------------------------------------
# TEST 6: FastAPI HTTP Endpoint Integration (/api/v1/agent/invoke & /state)
# ---------------------------------------------------------------------------
def test_fastapi_agent_endpoints(api_client):
    """
    Tests FastAPI REST API invoking the LangGraph agent over HTTP and querying checkpoint state.
    """
    phone = "+254700112233"

    # Test POST /api/v1/agent/invoke
    payload = {
        "caller_phone": phone,
        "transcript": "Nimeuzia Safari Hotel magunia 10 ya mahindi kwa shilingi elfu moja kila moja, PIN P051234567M",
        "language": "sw",
    }

    response = api_client.post("/api/v1/agent/invoke", json=payload)
    if response.status_code == 200 and response.json().get("needs_trader_pin"):
        enroll = api_client.post(
            "/api/v1/agent/invoke",
            json={
                "caller_phone": phone,
                "transcript": "PIN yangu ni A012345678W",
                "language": "sw",
            },
        )
        assert enroll.status_code == 200, enroll.text
        assert enroll.json()["needs_trader_pin"] is False
        assert enroll.json()["trader_pin"] == "A012345678W"
        response = api_client.post("/api/v1/agent/invoke", json=payload)

    assert response.status_code == 200, f"API failed: {response.text}"

    data = response.json()
    assert data["caller_phone"] == phone
    assert data["call_status"] == "READY_FOR_OSCU"
    assert data["ready_for_filing"] is True
    assert data["sale"]["item_name"] == "mahindi"
    assert data["buyer_validation"]["legal_name"] == "SAFARI HOTEL LIMITED"
    assert data["tax_breakdown"]["classification"] == "EXEMPT"
    assert data["tax_breakdown"]["grand_total"] == 10000.0

    # Test GET /api/v1/agent/state/{caller_phone}
    state_response = api_client.get(f"/api/v1/agent/state/{phone}")
    assert state_response.status_code == 200
    state_data = state_response.json()
    assert state_data["caller_phone"] == phone
    assert state_data["state"] is not None
    assert state_data["state"]["call_status"] == "READY_FOR_OSCU"
