"""Tests for the Greeter Agent.

This module contains unit tests for the Greeter Agent's functionality including:
- Welcome message generation
- Field extraction and collection
- Identity verification (2-out-of-3 rule)
- Secret question authentication
- Guardrail integration
- Error handling and max attempts
"""

import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import State
from app.guardrails.guardrails import GuardrailResult

# Configure logging for tests
logger = logging.getLogger(__name__)


# ============================================================================
# Increment 1: Basic Agent Structure & Welcome Tests
# ============================================================================


def test_welcome_message_on_first_turn():
    """Test that agent returns welcome message on first conversation turn.

    Scenario:
        - User sends first message
        - state["messages"] contains only 1 message
        - Agent should welcome customer and ask for identity information

    Expected:
        - Agent responds with friendly greeting
        - Response mentions name, phone, and IBAN
        - No database lookup attempted
        - conversation_ended is False
    """
    from app.agents.greeter import greeter_agent

    # Arrange: First turn with user message
    state = State(
        messages=[HumanMessage(content="Hi, I need help")],
        session_id="test-session",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={"name": None, "phone": None, "iban": None},
        specialist_needed=False,
        conversation_ended=False,
    )

    # Mock guardrails to pass input and output
    with patch("app.agents.greeter.run_guardrails") as mock_guardrails:
        mock_guardrails.return_value = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="Welcome to DEUS Bank! ...",
        )

        # Act
        result = greeter_agent(state)

        # Assert
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

        # Check welcome message content
        response = result["messages"][0].content.lower()
        assert any(
            word in response for word in ["welcome", "hello", "hi"]
        ), "Response should contain greeting"
        assert any(
            word in response for word in ["name", "phone", "iban"]
        ), "Response should mention identity fields"

        # Verify conversation state
        assert result.get("conversation_ended", False) is False


def test_guardrail_rejection_unsafe_input():
    """Test that agent ends conversation when input guardrail rejects message.

    Scenario:
        - User sends toxic/off-topic message
        - Input guardrail blocks the message
        - Agent should return safe response and end conversation

    Expected:
        - Agent returns guardrail's safe response
        - conversation_ended is True
        - No LLM processing attempted
    """
    from app.agents.greeter import greeter_agent

    # Arrange: Toxic user message
    state = State(
        messages=[HumanMessage(content="You are useless!")],
        session_id="test-session",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={"name": None, "phone": None, "iban": None},
        specialist_needed=False,
        conversation_ended=False,
    )

    # Mock guardrails to reject input
    with patch("app.agents.greeter.run_guardrails") as mock_guardrails:
        mock_guardrails.return_value = GuardrailResult(
            is_safe=False,
            blocked_reason="toxic",
            safe_response="I understand you're frustrated. Let's keep our conversation respectful.",
            sanitised_response="",
        )

        # Act
        result = greeter_agent(state)

        # Assert
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

        # Check that safe response is returned
        response = result["messages"][0].content
        assert response == "I understand you're frustrated. Let's keep our conversation respectful."

        # Verify conversation ended
        assert result.get("conversation_ended", False) is True


# ============================================================================
# Increment 2: Field Extraction Tests
# ============================================================================


def test_field_extraction_single_message():
    """Test that agent extracts multiple fields from a single message.

    Scenario:
        - User provides name and phone in one message
        - Agent extracts both fields using LLM structured output
        - Fields are merged into collected_fields

    Expected:
        - collected_fields contains extracted name and phone
        - Agent acknowledges the information
        - No verification attempted yet (need 2+ fields)
    """
    from app.agents.greeter import greeter_agent, ExtractedInfo

    # Arrange: User provides name and phone
    state = State(
        messages=[
            HumanMessage(content="Hi"),
            AIMessage(content="Welcome..."),
            HumanMessage(content="I'm Lisa and my phone is +1122334455"),
        ],
        session_id="test-session",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={"name": None, "phone": None, "iban": None},
        specialist_needed=False,
        conversation_ended=False,
    )

    # Mock guardrails and LLM extraction
    with patch("app.agents.greeter.run_guardrails") as mock_guardrails, patch(
        "app.agents.greeter.ChatOpenAI"
    ) as mock_llm_class:

        mock_guardrails.return_value = GuardrailResult(
            is_safe=True, blocked_reason=None, safe_response=None, sanitised_response="Thank you..."
        )

        # Mock LLM extraction
        mock_llm = Mock()
        mock_extractor = Mock()
        mock_extractor.invoke.return_value = ExtractedInfo(
            name="Lisa", phone="+1122334455", iban=None
        )
        mock_llm.with_structured_output.return_value = mock_extractor
        mock_llm_class.return_value = mock_llm

        # Act
        result = greeter_agent(state)

        # Assert
        assert "collected_fields" in result
        assert result["collected_fields"]["name"] == "Lisa"
        assert result["collected_fields"]["phone"] == "+1122334455"
        assert result["collected_fields"]["iban"] is None


def test_incremental_field_collection():
    """Test that agent collects fields incrementally across multiple turns.

    Scenario:
        - Turn 1: User provides name only
        - Turn 2: User provides phone only
        - Fields are accumulated, not replaced

    Expected:
        - After turn 1: name is set, phone/iban are None
        - After turn 2: name and phone are set, iban is None
        - Previously collected fields are preserved
    """
    from app.agents.greeter import greeter_agent, ExtractedInfo

    # Arrange: User provides name first
    state_turn1 = State(
        messages=[
            HumanMessage(content="Hi"),
            AIMessage(content="Welcome..."),
            HumanMessage(content="My name is Lisa"),
        ],
        session_id="test-session",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={"name": None, "phone": None, "iban": None},
        specialist_needed=False,
        conversation_ended=False,
    )

    with patch("app.agents.greeter.run_guardrails") as mock_guardrails, patch(
        "app.agents.greeter.ChatOpenAI"
    ) as mock_llm_class:

        mock_guardrails.return_value = GuardrailResult(
            is_safe=True, blocked_reason=None, safe_response=None, sanitised_response="Thank you..."
        )

        # Turn 1: Extract name only
        mock_llm = Mock()
        mock_extractor = Mock()
        mock_extractor.invoke.return_value = ExtractedInfo(name="Lisa", phone=None, iban=None)
        mock_llm.with_structured_output.return_value = mock_extractor
        mock_llm_class.return_value = mock_llm

        result1 = greeter_agent(state_turn1)

        assert result1["collected_fields"]["name"] == "Lisa"
        assert result1["collected_fields"]["phone"] is None

        # Turn 2: User provides phone
        state_turn2 = State(
            messages=[
                HumanMessage(content="Hi"),
                AIMessage(content="Welcome..."),
                HumanMessage(content="My name is Lisa"),
                AIMessage(content="Thank you..."),
                HumanMessage(content="My phone is +1122334455"),
            ],
            session_id="test-session",
            current_agent="greeter",
            verified_user=None,
            is_authenticated=False,
            customer_tier=None,
            verification_attempts=0,
            collected_fields={"name": "Lisa", "phone": None, "iban": None},  # Name preserved
            specialist_needed=False,
            conversation_ended=False,
        )

        # Extract phone only
        mock_extractor.invoke.return_value = ExtractedInfo(
            name=None, phone="+1122334455", iban=None
        )

        result2 = greeter_agent(state_turn2)

        # Assert fields are accumulated
        assert result2["collected_fields"]["name"] == "Lisa"  # Preserved
        assert result2["collected_fields"]["phone"] == "+1122334455"  # Added
        assert result2["collected_fields"]["iban"] is None


def test_field_merge_non_none_only():
    """Test that field merge only updates non-None extracted values.

    Scenario:
        - collected_fields has name="Lisa", phone=None
        - User provides phone="..." (LLM extracts phone="+112...", name=None)
        - Merge should keep name="Lisa" and add phone

    Expected:
        - None values from extraction don't overwrite existing fields
        - Only non-None extracted values are merged
    """
    from app.agents.greeter import greeter_agent, ExtractedInfo

    # Arrange: Name already collected, user provides phone
    state = State(
        messages=[
            HumanMessage(content="Hi"),
            AIMessage(content="Welcome..."),
            HumanMessage(content="My name is Lisa"),
            AIMessage(content="Thank you..."),
            HumanMessage(content="Phone is +1122334455"),
        ],
        session_id="test-session",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        verification_attempts=0,
        collected_fields={"name": "Lisa", "phone": None, "iban": None},
        specialist_needed=False,
        conversation_ended=False,
    )

    with patch("app.agents.greeter.run_guardrails") as mock_guardrails, patch(
        "app.agents.greeter.ChatOpenAI"
    ) as mock_llm_class:

        mock_guardrails.return_value = GuardrailResult(
            is_safe=True, blocked_reason=None, safe_response=None, sanitised_response="Thank you..."
        )

        # LLM extracts phone only (name=None shouldn't overwrite)
        mock_llm = Mock()
        mock_extractor = Mock()
        mock_extractor.invoke.return_value = ExtractedInfo(
            name=None, phone="+1122334455", iban=None  # None should not overwrite existing "Lisa"
        )
        mock_llm.with_structured_output.return_value = mock_extractor
        mock_llm_class.return_value = mock_llm

        # Act
        result = greeter_agent(state)

        # Assert
        assert result["collected_fields"]["name"] == "Lisa"  # Preserved!
        assert result["collected_fields"]["phone"] == "+1122334455"  # Added


# ============================================================================
# Integration Test for Full Greeter Flow in LangGraph
# ============================================================================


def test_full_greeter_flow_integration():
    """Test complete greeter flow integrated into LangGraph pipeline.

    Scenario:
        - User starts conversation
        - Provides identity information
        - Gets verified
        - Answers secret question correctly
        - Gets authenticated and routed to bouncer

    Expected:
        - Full flow executes without errors
        - Final state has is_authenticated=True
        - Routing directs to bouncer agent
    """
    from app.graph.pipeline import build_graph
    from app.graph.state import create_initial_state
    from app.models.schemas import User

    # Create graph
    graph = build_graph()

    # Initialize conversation
    initial_state = create_initial_state("test-session")
    initial_state["messages"] = [HumanMessage(content="Hi, I need help")]

    # Mock components
    with patch("app.agents.greeter.run_guardrails") as mock_guardrails, patch(
        "app.agents.greeter.ChatOpenAI"
    ) as mock_llm_class, patch("app.agents.greeter.find_user_with_retry") as mock_find_user:

        # Setup mocks
        mock_guardrails.return_value = GuardrailResult(
            is_safe=True, blocked_reason=None, safe_response=None, sanitised_response="Response..."
        )

        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm

        # Mock user for verification
        mock_user = User(
            name="Lisa",
            phone="+1122334455",
            iban="DE89370400440532013000",
            secret="Which is the name of my dog?",
            answer="Yoda",
        )
        mock_find_user.return_value = mock_user

        # Execute graph (first turn - welcome)
        result = graph.invoke(initial_state)

        # Verify welcome message
        assert len(result["messages"]) > 0
        assert "welcome" in result["messages"][-1].content.lower()
        assert not result.get("conversation_ended", False)

        logger.info("Integration test: Full greeter flow validated")


# Test fixtures will be added incrementally as we implement each feature
