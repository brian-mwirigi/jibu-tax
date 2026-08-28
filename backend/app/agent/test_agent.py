"""
File: backend/app/agent/test_agent.py
Description:
    Test Runner for Role 4: LangGraph Multi-Agent Routing Logic.
    Executes mock Swahili/English/Sheng trader transcripts through the compiled DAG.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agent.graph import build_jibutax_graph


def run_test_scenarios():
    graph = build_jibutax_graph()
    thread_config = {"configurable": {"thread_id": "+254712345678"}}

    print("=" * 70)
    print("SCENARIO 1: Valid Maize Sale (First Schedule VAT Exempt) + Verified PIN")
    print("=" * 70)
    input_state_1 = {
        "caller_phone": "+254712345678",
        "transcript": "Nimeuzia Safari Hotel magunia 50 ya mahindi kwa shilingi mia nane kila moja, PIN yao ni P051234567M",
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

    try:
        output_1 = graph.invoke(input_state_1, config=thread_config)
        print(f"Status: {output_1.get('call_status')}")
        print(f"Extracted Sale: {output_1.get('sale')}")
        print(f"Buyer Validation: {output_1.get('buyer_validation')}")
        print(f"Tax Breakdown: {output_1.get('tax_breakdown')}")
        print(f"Spoken Summary: {output_1.get('spoken_summary')}")
        print(f"Ready for Filing: {output_1.get('ready_for_filing')}")
    except Exception as e:
        print(f"Scenario 1 Error (API key / network): {e}")

    print("\n" + "=" * 70)
    print("SCENARIO 2: Missing PIN -> Clarification Node Triggered")
    print("=" * 70)
    input_state_2 = {
        "caller_phone": "+254722999000",
        "transcript": "Nimeuza mboga kilo 20 kwa shilingi hamsini kila kilo.",
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

    try:
        output_2 = graph.invoke(input_state_2, config={"configurable": {"thread_id": "+254722999000"}})
        print(f"Status: {output_2.get('call_status')}")
        print(f"Extracted Sale: {output_2.get('sale')}")
        print(f"Spoken Reprompt: {output_2.get('spoken_summary')}")
        print(f"Ready for Filing: {output_2.get('ready_for_filing')}")
    except Exception as e:
        print(f"Scenario 2 Error: {e}")

    print("\n" + "=" * 70)
    print("TEST FINISHED")
    print("=" * 70)


if __name__ == "__main__":
    run_test_scenarios()
