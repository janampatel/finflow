"""LangGraph graph definition and compilation."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.agents.state import AgentState
from src.agents.nodes import (
    planner_node, tools_coordinator_node, insight_node,
    synthesis_node, validation_node
)


def build_agent_graph():
    """Build and compile the LangGraph state machine.

    Graph flow:
    planner → tools_coordinator → insight → synthesis → validation → END

    tools_coordinator runs all 4 tools and merges their results.
    """
    from langgraph.graph import StateGraph, END

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("tools_coordinator", tools_coordinator_node)
    graph.add_node("insight", insight_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("validation", validation_node)

    # Add edges
    graph.add_edge("planner", "tools_coordinator")
    graph.add_edge("tools_coordinator", "insight")
    graph.add_edge("insight", "synthesis")
    graph.add_edge("synthesis", "validation")
    graph.add_edge("validation", END)

    # Set entry point
    graph.set_entry_point("planner")

    # Compile
    compiled_graph = graph.compile()
    logger.info("Agent graph compiled successfully")

    return compiled_graph


def create_agent_executor(transactions: list[dict]):
    """Create an executor for a specific set of transactions.

    Args:
        transactions: List of transaction dicts

    Returns:
        Compiled graph ready to invoke
    """
    graph = build_agent_graph()

    # Initialize state
    initial_state = {
        "messages": [],
        "transactions": transactions,
        "enriched_results": [],
        "anomaly_results": [],
        "cashflow_results": {},
        "merchant_results": [],
        "insights": {},
        "agent_plan": "",
        "final_response": "",
        "grounding_score": 0.0,
        "execution_trace": []
    }

    logger.info(f"Executor created for {len(transactions)} transactions")

    return graph, initial_state
