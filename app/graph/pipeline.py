"""LangGraph Pipeline for DEUS Bank AI Support System.

This module defines the main conversation graph that orchestrates the flow
between different agents (Greeter → Bouncer → Specialist).

Architecture:
    - StateGraph with shared State TypedDict
    - Nodes: greeter, bouncer, specialist_standard, specialist_premium, specialist_vip
    - Conditional edges for dynamic routing based on state
    - Entry point: greeter (first node)
    - End conditions: conversation_ended=True
    - Interrupt after each node for multi-turn conversation pattern

Flow:
    START → greeter → [authenticated?] → bouncer → [tier?] → specialist_* → [loop/end?]
                ↓                            ↓                       ↓
               [conversation_ended]         [conversation_ended]   [conversation_ended]
                ↓                            ↓                       ↓
               END                          END                    END/LOOP
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.graph.state import State
from app.agents.greeter import greeter_agent
from app.agents.bouncer import bouncer_agent
from app.agents.specialist import specialist_agent

# Configure logging
logger = logging.getLogger(__name__)


def route_after_greeter(state: State) -> str:
    """Determine next node after Greeter Agent completes.

    Routing Logic:
        - If conversation_ended=True: Route to END (max attempts or database error)
        - If is_authenticated=True: Route to "bouncer" (identity verified and authenticated)
        - Otherwise: Route to END (waiting for next user message)

    Args:
        state: Current conversation state

    Returns:
        "bouncer" if authenticated and ready for tier classification
        END symbol if conversation should terminate or wait for next message

    Examples:
        >>> # Authentication successful
        >>> state = {"is_authenticated": True, "conversation_ended": False}
        >>> route_after_greeter(state)
        'bouncer'

        >>> # Max attempts reached
        >>> state = {"is_authenticated": False, "conversation_ended": True}
        >>> route_after_greeter(state)
        END
        
        >>> # Waiting for next user message
        >>> state = {"is_authenticated": False, "conversation_ended": False}
        >>> route_after_greeter(state)
        END
    """
    conversation_ended = state.get("conversation_ended", False)
    is_authenticated = state.get("is_authenticated", False)

    if conversation_ended:
        logger.info("Conversation ended, routing to END")
        return END

    if is_authenticated:
        logger.info("User authenticated, routing to bouncer")
        return "bouncer"

    # Still waiting for authentication - pause and wait for next user message
    logger.info("Waiting for authentication, pausing conversation")
    return END


def route_after_bouncer(state: State) -> str:
    """Determine next specialist node after Bouncer Agent completes.

    Routing Logic:
        - Returns the tier-specific specialist node based on current_agent state field
        - Valid values: "specialist_standard", "specialist_premium", "specialist_vip"
        - Defensive fallback: defaults to "specialist_standard" for unexpected values

    Args:
        state: Current conversation state

    Returns:
        Node name of the tier-specific specialist

    Examples:
        >>> # Standard tier customer
        >>> state = {"current_agent": "specialist_standard"}
        >>> route_after_bouncer(state)
        'specialist_standard'

        >>> # Premium tier customer
        >>> state = {"current_agent": "specialist_premium"}
        >>> route_after_bouncer(state)
        'specialist_premium'
        
        >>> # VIP tier customer
        >>> state = {"current_agent": "specialist_vip"}
        >>> route_after_bouncer(state)
        'specialist_vip'
        
        >>> # Unexpected value - defensive fallback
        >>> state = {"current_agent": "unknown"}
        >>> route_after_bouncer(state)
        'specialist_standard'
    """
    current_agent = state.get("current_agent", "specialist_standard")
    
    # Validate against the three valid specialist nodes
    valid_specialists = ["specialist_standard", "specialist_premium", "specialist_vip"]
    if current_agent in valid_specialists:
        logger.info(f"Routing to {current_agent}")
        return current_agent
    
    # Defensive fallback for unexpected values
    logger.warning(f"Unexpected current_agent value: {current_agent}, defaulting to specialist_standard")
    return "specialist_standard"


def route_after_specialist(state: State) -> str:
    """Determine next node after Specialist Agent completes.

    Routing Logic:
        - Always route to END. Multi-turn specialist conversations are driven by the
          API layer: each new user message triggers a fresh graph invocation that
          flows greeter → bouncer → specialist again.

    Args:
        state: Current conversation state

    Returns:
        END symbol always
    """
    logger.info("Specialist done, routing to END")
    return END


def build_graph() -> StateGraph:
    """Create and configure the LangGraph pipeline.

    Builds the conversation graph with all agents and routing logic.
    The graph maintains shared state and routes between nodes based on
    conversation progress.

    Graph Structure:
        - 5 Nodes: greeter, bouncer, specialist_standard, specialist_premium, specialist_vip
        - Entry: greeter (first contact point)
        - Edges: Conditional routing based on authentication, tier, and conversation state
        - Interrupt after each node for multi-turn conversation pattern

    Returns:
        Compiled StateGraph ready for invocation with interrupt_after support

    Usage:
        >>> graph = build_graph()
        >>> result = graph.invoke(initial_state)
        >>> final_state = result
    """
    # Initialize graph with State schema
    workflow = StateGraph(State)

    # Add agent nodes - 3 specialist nodes all point to same specialist_agent function
    workflow.add_node("greeter", greeter_agent)
    workflow.add_node("bouncer", bouncer_agent)
    workflow.add_node("specialist_standard", specialist_agent)
    workflow.add_node("specialist_premium", specialist_agent)
    workflow.add_node("specialist_vip", specialist_agent)

    # Set entry point
    workflow.set_entry_point("greeter")

    # Add conditional edge from greeter
    workflow.add_conditional_edges(
        "greeter",
        route_after_greeter,
        {"bouncer": "bouncer", END: END},
    )

    # Add conditional edge from bouncer - routes to tier-specific specialist
    workflow.add_conditional_edges(
        "bouncer",
        route_after_bouncer,
        {
            "specialist_standard": "specialist_standard",
            "specialist_premium": "specialist_premium",
            "specialist_vip": "specialist_vip",
        },
    )
    
    # Add conditional edges from each specialist node - always end
    for specialist_node in ["specialist_standard", "specialist_premium", "specialist_vip"]:
        workflow.add_conditional_edges(
            specialist_node,
            route_after_specialist,
            {END: END},
        )

    # Compile graph — no interrupt_after needed; the API session store handles multi-turn
    graph = workflow.compile()

    logger.info("LangGraph pipeline created successfully with 5 nodes")
    return graph


# Create the default graph instance
graph = build_graph()
