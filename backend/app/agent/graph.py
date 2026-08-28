"""
File: backend/app/agent/graph.py
Description:
    Role 4: LangGraph StateGraph Construction & MemorySaver Checkpointing.
    Assembles the multi-agent DAG:
        START -> extract_sale -> validate_pin -> (conditional) -> calculate_tax -> END
                                              -> (clarify_pin) -> END
    Configures state persistence using caller_phone as the thread_id.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import JibuTaxState
from app.agent.nodes import (
    extract_sale_node,
    validate_pin_node,
    should_route_after_validation,
    calculate_tax_node,
    clarify_pin_node,
)

def build_jibutax_graph(checkpointer=None):
    """
    Constructs and compiles the JibuTax StateGraph.
    """
    builder = StateGraph(JibuTaxState)

    # 1. Add Processing Nodes
    builder.add_node("extract_sale", extract_sale_node)
    builder.add_node("validate_pin", validate_pin_node)
    builder.add_node("calculate_tax", calculate_tax_node)
    builder.add_node("clarify_pin", clarify_pin_node)

    # 2. Add Fixed Edges
    builder.add_edge(START, "extract_sale")
    builder.add_edge("extract_sale", "validate_pin")

    # 3. Add Conditional Edge based on KRA validation
    builder.add_conditional_edges(
        "validate_pin",
        should_route_after_validation,
        {
            "proceed_to_math": "calculate_tax",
            "clarify_pin": "clarify_pin",
            "failed": END,
        }
    )

    # 4. Terminal Edges
    builder.add_edge("calculate_tax", END)
    builder.add_edge("clarify_pin", END)

    # 5. Checkpointer Setup (MemorySaver)
    if checkpointer is None:
        checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


# Singleton compiled graph instance ready for import
jibutax_agent = build_jibutax_graph()
