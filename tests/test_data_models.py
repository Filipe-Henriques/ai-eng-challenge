"""Unit tests for data models and database functions.

This module tests all Pydantic models and mock database functions
to ensure validation, lookup logic, and edge cases work correctly.
"""

import pytest
from pydantic import ValidationError
from app.models.schemas import ChatRequest, ChatResponse, User, Account
from app.models.database import (
    MOCK_USERS, 
    MOCK_ACCOUNTS,
    find_user_by_fields,
    find_account_by_iban
)


# ============================================================================
# Phase 3: User Story 1 - API Data Exchange (ChatRequest/ChatResponse)
# ============================================================================

def test_chat_request_valid():
    """Test ChatRequest with valid data."""
    request = ChatRequest(
        session_id="sess_abc123",
        message="I need help with my account"
    )
    assert request.session_id == "sess_abc123"
    assert request.message == "I need help with my account"


def test_chat_request_missing_field():
    """Test ChatRequest raises ValidationError when message is missing."""
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(session_id="sess_abc123")
    assert "message" in str(exc_info.value)


def test_chat_response_valid():
    """Test ChatResponse with valid data."""
    response = ChatResponse(
        session_id="sess_abc123",
        response="I can help you with that...",
        agent="greeter"
    )
    assert response.session_id == "sess_abc123"
    assert response.response == "I can help you with that..."
    assert response.agent == "greeter"


def test_chat_response_missing_field():
    """Test ChatResponse raises ValidationError when agent is missing."""
    with pytest.raises(ValidationError) as exc_info:
        ChatResponse(
            session_id="sess_abc123",
            response="I can help you with that..."
        )
    assert "agent" in str(exc_info.value)


# ============================================================================
# Phase 4: User Story 2 - Customer Identity Verification (User model)
# ============================================================================

def test_find_user_by_fields_two_matches():
    """Test find_user_by_fields with 2 matching fields (name + phone)."""
    user = find_user_by_fields({"name": "Lisa", "phone": "+1122334455"})
    assert user is not None
    assert user.name == "Lisa"
    assert user.phone == "+1122334455"
    assert user.iban == "DE89370400440532013000"


def test_find_user_by_fields_three_matches():
    """Test find_user_by_fields with all 3 fields matching."""
    user = find_user_by_fields({
        "name": "John",
        "phone": "+1987654321",
        "iban": "GB29NWBK60161331926819"
    })
    assert user is not None
    assert user.name == "John"
    assert user.phone == "+1987654321"
    assert user.iban == "GB29NWBK60161331926819"


def test_find_user_by_fields_one_match():
    """Test find_user_by_fields with only 1 matching field returns None."""
    user = find_user_by_fields({"name": "Lisa", "phone": "WRONG"})
    assert user is None


def test_find_user_by_fields_no_match():
    """Test find_user_by_fields with no matching fields returns None."""
    user = find_user_by_fields({
        "name": "Unknown",
        "phone": "000",
        "iban": "000"
    })
    assert user is None


def test_find_user_by_fields_case_insensitive():
    """Test find_user_by_fields with case-insensitive name matching."""
    user = find_user_by_fields({"name": "lisa", "phone": "+1122334455"})
    assert user is not None
    assert user.name == "Lisa"
    
    # Also test with uppercase
    user = find_user_by_fields({"name": "MARIA", "iban": "FR7630006000011234567890189"})
    assert user is not None
    assert user.name == "Maria"


def test_user_model_missing_field():
    """Test User model raises ValidationError when a required field is missing."""
    with pytest.raises(ValidationError) as exc_info:
        User(
            name="Test",
            phone="+1234567890",
            iban="DE89370400440532013000",
            secret="What is your favorite color?"
            # Missing 'answer' field
        )
    assert "answer" in str(exc_info.value)


# ============================================================================
# Phase 5: User Story 3 - Account Tier Determination (Account model)
# ============================================================================

def test_find_account_by_iban_premium():
    """Test find_account_by_iban returns premium account for Lisa."""
    account = find_account_by_iban("DE89370400440532013000")
    assert account is not None
    assert account.iban == "DE89370400440532013000"
    assert account.premium is True


def test_find_account_by_iban_regular():
    """Test find_account_by_iban returns non-premium account for John."""
    account = find_account_by_iban("GB29NWBK60161331926819")
    assert account is not None
    assert account.iban == "GB29NWBK60161331926819"
    assert account.premium is False


def test_find_account_by_iban_not_found():
    """Test find_account_by_iban returns None for Maria (no account)."""
    account = find_account_by_iban("FR7630006000011234567890189")
    assert account is None


def test_find_account_by_iban_unknown():
    """Test find_account_by_iban returns None for invalid IBAN."""
    account = find_account_by_iban("UNKNOWN_IBAN")
    assert account is None


