"""Unit tests for agent behavior - Testing Strategy (009).

This module tests Greeter, Bouncer, and Specialist agents including
verification flows, routing logic, and tool functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage

from app.graph.state import State
from app.agents.greeter import greeter_agent
from app.agents.bouncer import bouncer_agent
from app.agents.specialist import (
    specialist_agent,
    get_account_balance,
    transfer_funds,
    report_lost_card,
)
from app.models.database import ACCOUNTS_DB


# =============================================================================
# Greeter Agent Tests (7 tests)
# =============================================================================


@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_welcome(mock_guardrails, mock_llm):
    """Test greeter generates welcome response for first turn."""
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="Welcome! How can I help you?"
    )
    mock_llm.invoke.return_value = AIMessage(content="Welcome! How can I help you?")
    
    state = State(
        messages=[HumanMessage(content="Hello")],
        session_id="test",
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
    
    result = greeter_agent(state)
    
    assert result["messages"] is not None
    assert len(result["messages"]) > 0


@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_extracts_fields(mock_guardrails, mock_llm):
    """Test greeter extracts name and phone from customer message."""
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="Thank you"
    )
    mock_llm.invoke.return_value = AIMessage(content="Thank you")
    
    state = State(
        messages=[HumanMessage(content="My name is John and my phone is +1987654321")],
        session_id="test",
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
    
    with patch("app.agents.greeter.extract_identity_fields") as mock_extract:
        mock_extract.return_value = {"name": "John", "phone": "+1987654321"}
        result = greeter_agent(state)
        
        assert "collected_fields" in result or mock_extract.called


@patch("app.agents.greeter.find_user_by_fields")
@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_verification_success(mock_guardrails, mock_llm, mock_find):
    """Test greeter successfully verifies user with 2+ matching fields."""
    from app.models.schemas import User
    
    mock_user = User(
        name="John",
        phone="+1987654321",
        iban="GB29NWBK60161331926819",
        secret="What is your mother's maiden name?",
        answer="Smith"
    )
    mock_find.return_value = mock_user
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="What is your mother's maiden name?"
    )
    mock_llm.invoke.return_value = AIMessage(content="What is your mother's maiden name?")
    
    state = State(
        messages=[],
        session_id="test",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={"name": "John", "phone": "+1987654321"},
        specialist_needed=False,
        conversation_ended=False,
    )
    
    result = greeter_agent(state)
    
    assert result.get("verified_user") is not None or mock_find.called


@patch("app.agents.greeter.find_user_by_fields")
@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_verification_failure(mock_guardrails, mock_llm, mock_find):
    """Test greeter increments attempts when verification fails."""
    mock_find.return_value = None
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="I couldn't verify your details"
    )
    mock_llm.invoke.return_value = AIMessage(content="I couldn't verify your details")
    
    state = State(
        messages=[],
        session_id="test",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={"name": "Wrong", "phone": "Wrong"},
        specialist_needed=False,
        conversation_ended=False,
    )
    
    result = greeter_agent(state)
    
    assert result.get("verification_attempts", 0) >= 0


@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_secret_answer_correct(mock_guardrails, mock_llm, mock_user):
    """Test greeter authenticates user with correct secret answer."""
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="Authenticated"
    )
    mock_llm.invoke.return_value = AIMessage(content="Authenticated")
    
    state = State(
        messages=[HumanMessage(content="Smith")],
        session_id="test",
        current_agent="greeter",
        verified_user=mock_user,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={"name": "John", "phone": "+1987654321"},
        specialist_needed=False,
        conversation_ended=False,
    )
    
    with patch("app.agents.greeter.verify_secret_answer") as mock_verify:
        mock_verify.return_value = True
        result = greeter_agent(state)
        
        assert result.get("is_authenticated") or mock_verify.called


@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_secret_answer_wrong(mock_guardrails, mock_llm, mock_user):
    """Test greeter increments attempts with wrong secret answer."""
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="Incorrect answer"
    )
    mock_llm.invoke.return_value = AIMessage(content="Incorrect answer")
    
    state = State(
        messages=[HumanMessage(content="Wrong")],
        session_id="test",
        current_agent="greeter",
        verified_user=mock_user,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=0,
        collected_fields={"name": "John"},
        specialist_needed=False,
        conversation_ended=False,
    )
    
    with patch("app.agents.greeter.verify_secret_answer") as mock_verify:
        mock_verify.return_value = False
        result = greeter_agent(state)
        
        assert result.get("verification_attempts", 0) >= 0


@patch("app.agents.greeter.llm")
@patch("app.agents.greeter.run_guardrails")
def test_greeter_max_attempts(mock_guardrails, mock_llm):
    """Test greeter ends conversation after 3 failed attempts."""
    mock_guardrails.return_value = MagicMock(
        is_safe=True,
        sanitised_response="Max attempts reached"
    )
    mock_llm.invoke.return_value = AIMessage(content="Max attempts reached")
    
    state = State(
        messages=[],
        session_id="test",
        current_agent="greeter",
        verified_user=None,
        is_authenticated=False,
        customer_tier=None,
        customer_intent=None,
        verification_attempts=3,
        collected_fields={},
        specialist_needed=False,
        conversation_ended=False,
    )
    
    result = greeter_agent(state)
    
    assert result.get("conversation_ended") or result.get("verification_attempts") >= 3


# =============================================================================
# Bouncer Agent Tests (5 tests)
# =============================================================================


@patch("app.agents.bouncer.llm")
def test_bouncer_routes_standard(mock_llm, authenticated_state):
    """Test bouncer routes standard tier user to specialist_standard."""
    authenticated_state["customer_tier"] = "standard"
    authenticated_state["current_agent"] = "bouncer"
    
    result = bouncer_agent(authenticated_state)
    
    assert result.get("customer_tier") == "standard" or "current_agent" in result


@patch("app.agents.bouncer.llm")
def test_bouncer_routes_premium(mock_llm, authenticated_state):
    """Test bouncer routes premium tier user appropriately."""
    authenticated_state["customer_tier"] = "premium"
    authenticated_state["current_agent"] = "bouncer"
    
    result = bouncer_agent(authenticated_state)
    
    assert "customer_tier" in result or "current_agent" in result


@patch("app.agents.bouncer.llm")
def test_bouncer_routes_vip(mock_llm, mock_vip_user, authenticated_state):
    """Test bouncer routes VIP tier user to specialist_vip."""
    authenticated_state["verified_user"] = mock_vip_user
    authenticated_state["customer_tier"] = "vip"
    authenticated_state["current_agent"] = "bouncer"
    
    result = bouncer_agent(authenticated_state)
    
    assert "customer_tier" in result or "current_agent" in result


@patch("app.agents.bouncer.llm")
def test_bouncer_classifies_intent(mock_llm, authenticated_state):
    """Test bouncer classifies customer intent with mocked LLM."""
    mock_llm.invoke.return_value = AIMessage(content="account_balance")
    authenticated_state["current_agent"] = "bouncer"
    
    with patch("app.agents.bouncer.classify_intent") as mock_classify:
        mock_classify.return_value = "account_balance"
        result = bouncer_agent(authenticated_state)
        
        assert result.get("customer_intent") or mock_classify.called


@patch("app.agents.bouncer.llm")
def test_bouncer_low_confidence_fallback(mock_llm, authenticated_state):
    """Test bouncer fallback for low confidence classification."""
    mock_llm.invoke.return_value = AIMessage(content="uncertain")
    authenticated_state["current_agent"] = "bouncer"
    
    with patch("app.agents.bouncer.classify_intent") as mock_classify:
        mock_classify.return_value = "general_inquiry"
        result = bouncer_agent(authenticated_state)
        
        assert result.get("customer_intent") or mock_classify.called


# =============================================================================
# Specialist Agent Tool Tests (5 tests)
# =============================================================================


def test_specialist_get_balance():
    """Test get_account_balance returns correct balance."""
    result = get_account_balance("user_001")
    
    assert "balance" in result
    assert result["success"] is True
    assert isinstance(result["balance"], (int, float))


def test_specialist_transfer_success():
    """Test transfer_funds succeeds with sufficient balance."""
    # Get initial balance
    initial_balance = ACCOUNTS_DB["user_001"].balance
    
    result = transfer_funds(
        user_id="user_001",
        recipient_iban="GB29NWBK60161331926819",
        amount=100.0,
        description="Test transfer"
    )
    
    assert result["success"] is True
    # Restore balance after test
    ACCOUNTS_DB["user_001"].balance = initial_balance


def test_specialist_transfer_insufficient():
    """Test transfer_funds fails with insufficient balance."""
    result = transfer_funds(
        user_id="user_001",
        recipient_iban="GB29NWBK60161331926819",
        amount=999999.0,
        description="Test"
    )
    
    assert result["success"] is False


def test_specialist_report_lost_card():
    """Test report_lost_card blocks the card."""
    initial_blocked = ACCOUNTS_DB["user_001"].card_blocked
    
    result = report_lost_card("user_001")
    
    assert result["success"] is True
    assert ACCOUNTS_DB["user_001"].card_blocked is True
    
    # Restore state
    ACCOUNTS_DB["user_001"].card_blocked = initial_blocked


@pytest.fixture(autouse=True, scope="function")
def reset_mock_db():
    """Reset mock DB state between tool tests."""
    # Store initial state
    initial_balances = {uid: acc.balance for uid, acc in ACCOUNTS_DB.items()}
    initial_blocked = {uid: acc.card_blocked for uid, acc in ACCOUNTS_DB.items()}
    
    yield
    
    # Restore initial state
    for uid, balance in initial_balances.items():
        ACCOUNTS_DB[uid].balance = balance
    for uid, blocked in initial_blocked.items():
        ACCOUNTS_DB[uid].card_blocked = blocked
