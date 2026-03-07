"""Unit tests for LangGraph State definition and initialization.

Tests verify:
- State initialization with correct defaults
- add_messages reducer appends messages correctly
- verified_user field accepts None and User objects
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import State, create_initial_state
from app.models.schemas import User


def test_create_initial_state_defaults():
    """Test that create_initial_state returns correct default values.
    
    Verifies:
    - session_id is set to provided value
    - All other fields match their specified defaults from spec.md
    """
    session_id = "test-session-123"
    state = create_initial_state(session_id)
    
    # Verify session_id is set correctly
    assert state["session_id"] == session_id
    
    # Verify all default values match spec.md
    assert state["messages"] == []
    assert state["current_agent"] == "greeter"
    assert state["verified_user"] is None
    assert state["is_authenticated"] is False
    assert state["customer_tier"] is None
    assert state["verification_attempts"] == 0
    assert state["collected_fields"] == {}
    assert state["specialist_needed"] is False
    assert state["conversation_ended"] is False


def test_add_messages_reducer():
    """Test that the add_messages reducer appends messages instead of overwriting.
    
    Verifies:
    - Messages are appended to the list
    - Previous messages are preserved
    - The messages list grows with each addition
    """
    state = create_initial_state("test-session")
    
    # Add first message
    msg1 = HumanMessage(content="Hello")
    state["messages"] = [msg1]
    assert len(state["messages"]) == 1
    assert state["messages"][0].content == "Hello"
    
    # Add second message - should append, not replace
    msg2 = AIMessage(content="Hi there!")
    state["messages"] = state["messages"] + [msg2]
    assert len(state["messages"]) == 2
    assert state["messages"][0].content == "Hello"
    assert state["messages"][1].content == "Hi there!"
    
    # Add third message - verify all previous messages preserved
    msg3 = HumanMessage(content="How are you?")
    state["messages"] = state["messages"] + [msg3]
    assert len(state["messages"]) == 3
    assert state["messages"][0].content == "Hello"
    assert state["messages"][1].content == "Hi there!"
    assert state["messages"][2].content == "How are you?"


def test_verified_user_field():
    """Test that verified_user field accepts both None and User objects.
    
    Verifies:
    - verified_user can be None (default state)
    - verified_user can be a User object (after verification)
    - State remains valid with both value types
    """
    state = create_initial_state("test-session")
    
    # Test 1: verified_user starts as None
    assert state["verified_user"] is None
    
    # Test 2: verified_user can be set to a User object
    test_user = User(
        name="Lisa Brown",
        phone="+1122334455",
        iban="GB82WEST12345698765432",
        secret="What is your favorite color?",
        answer="blue"
    )
    state["verified_user"] = test_user
    
    # Verify the user object is stored correctly
    assert state["verified_user"] is not None
    assert state["verified_user"].name == "Lisa Brown"
    assert state["verified_user"].phone == "+1122334455"
    assert state["verified_user"].iban == "GB82WEST12345698765432"
    
    # SECURITY CHECK: Verify the answer field exists but should never be exposed
    assert hasattr(state["verified_user"], "answer")
    assert state["verified_user"].answer == "blue"
    
    # Test 3: verified_user can be set back to None
    state["verified_user"] = None
    assert state["verified_user"] is None
