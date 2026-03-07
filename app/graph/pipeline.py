"""LangGraph Pipeline for DEUS Bank AI Support System.

This module defines the main conversation graph that orchestrates the flow
between different agents (Greeter → Bouncer → Specialist).

Architecture:
    - StateGraph with shared State TypedDict
    - Nodes: greeter, bouncer, specialist
    - Conditional edges for dynamic routing based on state
    - Entry point: greeter (first node)
    - End conditions: conversation_ended=True or successful handoff

Flow:
    START → greeter → [authenticated?] → bouncer → [specialist_needed?] → specialist → END
                ↓                            ↓
               [conversation_ended]         [conversation_ended]
                ↓                            ↓
               END                          END
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import State
from app.agents.greeter import greeter_agent

# Configure logging
logger = logging.getLogger(__name__)


def route_after_greeter(state: State) -> Literal["bouncer", "end"]:
    """Determine next node after Greeter Agent completes.

    Routing Logic:
        - If conversation_ended=True: Route to END (max attempts or database error)
        - If is_authenticated=True: Route to "bouncer" (identity verified and authenticated)
        - Otherwise: Route back to "greeter" (continue collection/verification)

    Args:
        state: Current conversation state

    Returns:
        "bouncer" if authenticated and ready for tier classification
        "end" if conversation should terminate

    Examples:
        >>> # Authentication successful
        >>> state = {"is_authenticated": True, "conversation_ended": False}
        >>> route_after_greeter(state)
        'bouncer'

        >>> # Max attempts reached
        >>> state = {"is_authenticated": False, "conversation_ended": True}
        >>> route_after_greeter(state)
        'end'
    """
    conversation_ended = state.get("conversation_ended", False)
    is_authenticated = state.get("is_authenticated", False)

    if conversation_ended:
        logger.info("Conversation ended, routing to END")
        return "end"

    if is_authenticated:
        logger.info("User authenticated, routing to bouncer")
        return "bouncer"

    # Should not reach here in normal flow (greeter loops internally)
    logger.warning("Unexpected routing state in route_after_greeter")
    return "end"


def create_graph() -> StateGraph:
    """Create and configure the LangGraph pipeline.

    Builds the conversation graph with all agents and routing logic.
    The graph maintains shared state and routes between nodes based on
    conversation progress.

    Returns:
        Compiled StateGraph ready for invocation

    Usage:
        >>> graph = create_graph()
        >>> result = graph.invoke(initial_state)
        >>> final_state = result

    Graph Structure:
        - Nodes: greeter (more to be added: bouncer, specialist)
        - Entry: greeter (first contact point)
        - Edges: Conditional routing based on authentication and termination
    """
    # Initialize graph with State schema
    builder = StateGraph(State)

    # Add agent nodes
    builder.add_node("greeter", greeter_agent)
    # TODO: Add bouncer node when implemented
    # TODO: Add specialist node when implemented

    # Set entry point
    builder.set_entry_point("greeter")

    # Add conditional edges from greeter
    builder.add_conditional_edges(
        "greeter",
        route_after_greeter,
        {"bouncer": END, "end": END},  # Placeholder: Will route to "bouncer" node when implemented
    )

    # Compile graph
    graph = builder.compile()

    logger.info("LangGraph pipeline created successfully")
    return graph


# Create the default graph instance
graph = create_graph()
