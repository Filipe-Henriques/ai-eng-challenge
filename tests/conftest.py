"""Shared pytest fixtures for DEUS Bank AI Support System tests.

This module provides reusable fixtures for mock data, state initialization,
and LLM response mocking. All fixtures are shared across test files.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.models.schemas import User, Account, Transaction
from app.graph.state import State


# =============================================================================
# Mock User Fixtures (Session-scoped for efficiency)
# =============================================================================


@pytest.fixture(scope="session")
def mock_user() -> User:
    """Mock standard-tier user for tests (John, user_002).
    
    Returns:
        User object for John with standard tier and known credentials.
    """
    return User(
        name="John",
        phone="+1987654321",
        iban="GB29NWBK60161331926819",
        secret="What is your mother's maiden name?",
        answer="Smith",
    )


@pytest.fixture(scope="session")
def mock_vip_user() -> User:
    """Mock VIP-tier user for tests (Lisa, user_001).
    
    Returns:
        User object for Lisa with VIP tier (premium=True) and known credentials.
    """
    return User(
        name="Lisa",
        phone="+1122334455",
        iban="DE89370400440532013000",
        secret="Which is the name of my dog?",
        answer="Yoda",
    )


@pytest.fixture(scope="session")
def mock_account() -> Account:
    """Mock account with balance and transactions for tests.
    
    Returns:
        Account object for user_001 (Lisa) with ~5000 EUR and 3 transactions.
    """
    return Account(
        user_id="user_001",
        iban="DE89370400440532013000",
        premium=True,
        balance=5000.00,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-01", description="Salary Deposit", amount=3000.0),
            Transaction(date="2026-03-02", description="Rent Payment", amount=-1200.0),
            Transaction(date="2026-03-03", description="Grocery Store", amount=-45.20),
        ],
        card_blocked=False,
    )


# =============================================================================
# Mock State Fixtures (Function-scoped to prevent test pollution)
# =============================================================================


@pytest.fixture(scope="function")
def base_state() -> State:
    """Create a minimal GraphState with default values.
    
    Returns:
        State dictionary with default initialization and one HumanMessage.
    """
    return State(
        messages=[HumanMessage(content="Hello")],
        session_id="test-session-001",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={},
        specialist_needed=False,
        conversation_ended=False,
    )


@pytest.fixture(scope="function")
def authenticated_state(mock_user: User) -> State:
    """Create a GraphState with authenticated user.
    
    Args:
        mock_user: Injected mock_user fixture
    
    Returns:
        State dictionary with is_authenticated=True, verified_user set, 
        and current_agent="bouncer".
    """
    return State(
        messages=[
            HumanMessage(content="Hello"),
            AIMessage(content="Welcome! Please provide your details."),
            HumanMessage(content="My name is John and my phone is +1987654321"),
            AIMessage(content=f"Thank you. {mock_user.secret}"),
            HumanMessage(content="Smith"),
        ],
        session_id="test-session-auth",
        current_agent="bouncer",
        verified_user=mock_user,
        is_authenticated=True,
        customer_tier="standard",
        customer_intent=None,
        verification_attempts=0,
        collected_fields={"name": "John", "phone": "+1987654321"},
        specialist_needed=False,
        conversation_ended=False,
    )


# =============================================================================
# Mock LLM Response Factory
# =============================================================================


@pytest.fixture(scope="function")
def mock_llm_response():
    """Factory function for creating mock LLM responses.
    
    Returns:
        Callable that takes a content string and returns a mock LLM response
        object suitable for mocking OpenAI/LangChain LLM calls.
    
    Example:
        >>> response_factory = mock_llm_response()
        >>> mock_response = response_factory("This is a test response")
        >>> mock_response.content
        "This is a test response"
    """
    def make_response(content: str):
        """Create a mock LLM response with given content.
        
        Args:
            content: The response text
        
        Returns:
            Mock object with .content attribute returning the content string.
        """
        class MockLLMResponse:
            def __init__(self, text: str):
                self.content = text
            
            def __str__(self):
                return self.content
        
        return MockLLMResponse(content)
    
    return make_response
