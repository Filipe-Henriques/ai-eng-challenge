"""Tests for the Bouncer Agent.

This module contains unit tests for the Bouncer Agent's functionality including:
- Tier-based specialist routing (User Story 1)
- Intent classification from conversation history (User Story 2)
- LLM-generated handoff messages with guardrails (User Story 3)
- Integration with Greeter and Specialist agents
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import State
from app.models.schemas import User
from app.agents.bouncer import ClassifiedIntent
from app.guardrails.guardrails import GuardrailResult

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_standard_user():
    """Create a mock User object with standard tier (John - non-premium account)."""
    return User(
        name="John",
        phone="+1987654321",
        iban="GB29NWBK60161331926819",  # John's IBAN - premium=False in database
        secret="What is your mother's maiden name?",
        answer="Smith",
    )


@pytest.fixture
def mock_premium_user():
    """Create a mock User object with premium tier (Lisa - premium account)."""
    return User(
        name="Lisa",
        phone="+1122334455",
        iban="DE89370400440532013000",  # Lisa's IBAN - premium=True in database
        secret="Which is the name of my dog?",
        answer="Yoda",
    )


@pytest.fixture
def authenticated_state_standard(mock_standard_user):
    """Create an authenticated state with standard tier user (John)."""
    return State(
        messages=[
            HumanMessage(content="Hi, I need help"),
            AIMessage(content="Welcome! Please provide your name, phone, and IBAN."),
            HumanMessage(content="John +1987654321 GB29NWBK60161331926819"),
            AIMessage(content="What is your mother's maiden name?"),
            HumanMessage(content="Smith"),
            AIMessage(content="Authentication successful!"),
        ],
        session_id="test-session-1",
        current_agent="greeter",
        verified_user=mock_standard_user,
        is_authenticated=True,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={
            "name": "John",
            "phone": "+1987654321",
            "iban": "GB29NWBK60161331926819",
        },
        specialist_needed=False,
        conversation_ended=False,
    )


@pytest.fixture
def authenticated_state_premium(mock_premium_user):
    """Create an authenticated state with premium tier user (Lisa)."""
    return State(
        messages=[
            HumanMessage(content="Hello"),
            AIMessage(content="Welcome! Please provide your name, phone, and IBAN."),
            HumanMessage(content="Lisa +1122334455 DE89370400440532013000"),
            AIMessage(content="Which is the name of my dog?"),
            HumanMessage(content="Yoda"),
            AIMessage(content="Authentication successful!"),
        ],
        session_id="test-session-2",
        current_agent="greeter",
        verified_user=mock_premium_user,
        is_authenticated=True,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={
            "name": "Lisa",
            "phone": "+1122334455",
            "iban": "DE89370400440532013000",
        },
        specialist_needed=False,
        conversation_ended=False,
    )


# ============================================================================
# Phase 3: User Story 1 - Basic Tier Routing Tests
# ============================================================================


def test_bouncer_routes_standard_customer(authenticated_state_standard):
    """Test that standard tier customer is routed to specialist_standard.

    Scenario:
        - Authenticated user with tier="standard"
        - Bouncer should route to specialist_standard

    Expected:
        - customer_tier is set to "standard"
        - current_agent is set to "specialist_standard"
    """
    from app.agents.bouncer import bouncer_agent

    # Mock guardrails to pass
    with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
        mock_guardrails.return_value = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="Connecting you to a specialist...",
        )

        # Act
        result = bouncer_agent(authenticated_state_standard)

        # Assert
        assert result["customer_tier"] == "standard"
        assert result["current_agent"] == "specialist_standard"


def test_bouncer_routes_premium_customer(authenticated_state_premium):
    """Test that premium tier customer is routed to specialist_premium.

    Scenario:
        - Authenticated user with tier="premium"
        - Bouncer should route to specialist_premium

    Expected:
        - customer_tier is set to "premium"
        - current_agent is set to "specialist_premium"
    """
    from app.agents.bouncer import bouncer_agent

    # Mock guardrails to pass
    with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
        mock_guardrails.return_value = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="Connecting you to a specialist...",
        )

        # Act
        result = bouncer_agent(authenticated_state_premium)

        # Assert
        assert result["customer_tier"] == "premium"
        assert result["current_agent"] == "specialist_premium"


def test_bouncer_fallback_no_account(authenticated_state_standard):
    """Test that user with no account falls back to specialist_standard.

    Scenario:
        - Authenticated user with IBAN that has no Account record
        - Bouncer should defensively route to specialist_standard

    Expected:
        - customer_tier is set to "standard" (default for no account)
        - current_agent is set to "specialist_standard"
    """
    from app.agents.bouncer import bouncer_agent

    # Use Maria's IBAN (exists in MOCK_USERS but not in MOCK_ACCOUNTS)
    authenticated_state_standard["verified_user"].iban = "FR7630006000011234567890189"

    # Mock guardrails to pass
    with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
        mock_guardrails.return_value = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="Connecting you to a specialist...",
        )

        # Act
        result = bouncer_agent(authenticated_state_standard)

        # Assert
        assert result["customer_tier"] == "standard"
        assert result["current_agent"] == "specialist_standard"


# ============================================================================
# Phase 4: User Story 2 - Intent Classification Tests
# ============================================================================


def test_bouncer_classifies_account_balance(authenticated_state_standard):
    """Test that bouncer correctly classifies account_balance intent."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_standard["messages"].append(
        HumanMessage(content="What is my account balance?")
    )
    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="account_balance", confidence=0.9
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm
        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Connecting...",
            )
            result = bouncer_agent(authenticated_state_standard)
            assert result["customer_intent"] == "account_balance"
            assert result["customer_intent"] == "account_balance"


def test_bouncer_classifies_transaction_history(authenticated_state_premium):
    """Test that bouncer correctly classifies transaction_history intent."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_premium["messages"].append(
        HumanMessage(content="Can you show me my recent transactions?")
    )

    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="transaction_history", confidence=0.85
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Let me connect you...",
            )

            result = bouncer_agent(authenticated_state_premium)
            assert result["customer_intent"] == "transaction_history"


def test_bouncer_classifies_fund_transfer(authenticated_state_standard):
    """Test that bouncer correctly classifies fund_transfer intent."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_standard["messages"].append(
        HumanMessage(content="I need to transfer $500 to my friend")
    )

    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="fund_transfer", confidence=0.95
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Connecting you now...",
            )

            result = bouncer_agent(authenticated_state_standard)
            assert result["customer_intent"] == "fund_transfer"


def test_bouncer_classifies_lost_card(authenticated_state_premium):
    """Test that bouncer correctly classifies lost_card intent."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_premium["messages"].append(
        HumanMessage(content="I lost my credit card, please help!")
    )

    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="lost_card", confidence=0.92
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Let me assist you...",
            )

            result = bouncer_agent(authenticated_state_premium)
            assert result["customer_intent"] == "lost_card"


def test_bouncer_classifies_general_inquiry(authenticated_state_standard):
    """Test that bouncer correctly classifies general_inquiry intent."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_standard["messages"].append(
        HumanMessage(content="What are your business hours?")
    )

    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="general_inquiry", confidence=0.7
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Connecting you...",
            )

            result = bouncer_agent(authenticated_state_standard)
            assert result["customer_intent"] == "general_inquiry"


def test_bouncer_fallback_low_confidence(authenticated_state_premium):
    """Test that low confidence intent falls back to general_inquiry."""
    from app.agents.bouncer import bouncer_agent, ClassifiedIntent

    authenticated_state_premium["messages"].append(
        HumanMessage(content="Hmm, I'm not sure what I need...")
    )

    with patch("app.agents.bouncer.ChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = ClassifiedIntent(
            intent="account_balance", confidence=0.3  # Low confidence!
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm

        with patch("app.agents.bouncer.run_guardrails") as mock_guardrails:
            mock_guardrails.return_value = GuardrailResult(
                is_safe=True,
                blocked_reason=None,
                safe_response=None,
                sanitised_response="Connecting you...",
            )

            result = bouncer_agent(authenticated_state_premium)
            assert result["customer_intent"] == "general_inquiry"  # Fallback!
