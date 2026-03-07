"""LangGraph State definition for DEUS Bank AI Support System.

This module defines the shared state structure that flows through all nodes
in the conversation graph. Every agent reads from and writes to this state.
"""

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from app.models.schemas import User


class State(TypedDict):
    """The shared data structure for the entire agent pipeline.
    
    This TypedDict defines all state fields that agents can read from and write to.
    The state is passed through each node in the LangGraph pipeline and maintains
    the full conversation context and customer information.
    
    Fields:
        messages: Full conversation history using LangGraph's add_messages reducer.
                 Messages are appended, never overwritten.
        session_id: Unique identifier for the current conversation session.
        current_agent: Name of the agent currently handling the conversation.
                      Used for routing and response metadata.
        verified_user: The User object from the database once identity is verified
                      (2/3 fields matched). None until verification passes.
                      SECURITY: Never expose the 'answer' field in responses.
        is_authenticated: True only after customer correctly answers secret question.
        customer_tier: Customer classification - "premium", "regular", or "non_client".
                      Set by the Bouncer Agent.
        verification_attempts: Count of failed identity verification attempts.
                              Used to limit retries and prevent brute-force.
        collected_fields: Dictionary of identity fields collected from customer
                         (e.g., {"name": "Lisa", "phone": "+1122334455"}).
                         Keys: field names (name, phone, iban).
                         Values: customer-provided strings.
        specialist_needed: True if customer request requires Specialist Agent routing.
                          Set by the Bouncer Agent.
        conversation_ended: True when conversation reaches terminal state
                          (resolved, rejected, max attempts exceeded).
                          Used as the graph's termination condition.
    """
    
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    current_agent: str
    verified_user: User | None
    is_authenticated: bool
    customer_tier: str | None
    verification_attempts: int
    collected_fields: dict[str, str]
    specialist_needed: bool
    conversation_ended: bool


def create_initial_state(session_id: str) -> State:
    """Create a fresh State dictionary with default values for a new conversation.
    
    This factory function initializes all state fields to their default values,
    ensuring every new conversation session starts with a clean, predictable state.
    
    Args:
        session_id: Unique identifier for the conversation session.
        
    Returns:
        A State dictionary with all fields set to their default values:
        - messages: Empty list
        - session_id: Provided session ID
        - current_agent: "greeter" (first agent in pipeline)
        - verified_user: None (no verification yet)
        - is_authenticated: False (not authenticated yet)
        - customer_tier: None (not classified yet)
        - verification_attempts: 0 (no attempts yet)
        - collected_fields: Empty dict (no fields collected yet)
        - specialist_needed: False (no routing decision yet)
        - conversation_ended: False (conversation just started)
    
    Example:
        >>> state = create_initial_state("session-123")
        >>> state["session_id"]
        "session-123"
        >>> state["current_agent"]
        "greeter"
    """
    return State(
        messages=[],
        session_id=session_id,
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={},
        specialist_needed=False,
        conversation_ended=False,
    )
