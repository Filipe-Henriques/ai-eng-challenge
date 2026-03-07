"""Unit tests for data models and mock database - Testing Strategy (009).

This module tests User and Account model creation, as well as the 2-of-3
verification logic in find_user_by_fields function.
"""

import pytest
from app.models.schemas import User, Account, Transaction
from app.models.database import find_user_by_fields, MOCK_USERS


# =============================================================================
# Test Cases: User and Account Model Creation
# =============================================================================


def test_user_creation():
    """Test creating a User object with valid fields.
    
    Validates that all User fields are set correctly when creating
    a new User instance with valid data.
    """
    user = User(
        name="Test User",
        phone="+1234567890",
        iban="DE89370400440532013000",
        secret="What is your favorite color?",
        answer="Blue",
    )
    
    assert user.name == "Test User"
    assert user.phone == "+1234567890"
    assert user.iban == "DE89370400440532013000"
    assert user.secret == "What is your favorite color?"
    assert user.answer == "Blue"


def test_account_creation():
    """Test creating an Account object with valid fields.
    
    Validates that all Account fields including nested Transaction objects
    are set correctly when creating a new Account instance.
    """
    transactions = [
        Transaction(date="2026-03-01", description="Salary", amount=3000.0),
        Transaction(date="2026-03-02", description="Rent", amount=-1200.0),
    ]
    
    account = Account(
        user_id="user_test",
        iban="DE89370400440532013000",
        premium=True,
        balance=5000.00,
        currency="EUR",
        transactions=transactions,
        card_blocked=False,
    )
    
    assert account.user_id == "user_test"
    assert account.iban == "DE89370400440532013000"
    assert account.premium is True
    assert account.balance == 5000.00
    assert account.currency == "EUR"
    assert len(account.transactions) == 2
    assert account.transactions[0].description == "Salary"
    assert account.card_blocked is False


# =============================================================================
# Test Cases: 2-of-3 Verification Logic
# =============================================================================


def test_find_user_2_of_3_name_phone():
    """Test find_user_by_fields with correct name and phone (2 of 3).
    
    Validates that providing 2 correct fields (name + phone) successfully
    returns the matching User from the mock database.
    """
    user = find_user_by_fields({"name": "Lisa", "phone": "+1122334455"})
    
    assert user is not None
    assert user.name == "Lisa"
    assert user.phone == "+1122334455"
    assert user.iban == "DE89370400440532013000"


def test_find_user_2_of_3_name_iban():
    """Test find_user_by_fields with correct name and IBAN (2 of 3).
    
    Validates that providing 2 correct fields (name + IBAN) successfully
    returns the matching User from the mock database.
    """
    user = find_user_by_fields({"name": "John", "iban": "GB29NWBK60161331926819"})
    
    assert user is not None
    assert user.name == "John"
    assert user.iban == "GB29NWBK60161331926819"
    assert user.phone == "+1987654321"


def test_find_user_2_of_3_phone_iban():
    """Test find_user_by_fields with correct phone and IBAN (2 of 3).
    
    Validates that providing 2 correct fields (phone + IBAN) successfully
    returns the matching User even without providing the name.
    """
    user = find_user_by_fields(
        {"phone": "+1555000111", "iban": "FR7630006000011234567890189"}
    )
    
    assert user is not None
    assert user.name == "Maria"
    assert user.phone == "+1555000111"
    assert user.iban == "FR7630006000011234567890189"


def test_find_user_1_of_3_fails():
    """Test find_user_by_fields with only 1 correct field returns None.
    
    Validates that the 2-of-3 verification requirement is enforced:
    providing only 1 correct field should not authenticate the user.
    """
    # Only name is correct, phone and IBAN are wrong
    user = find_user_by_fields(
        {"name": "Lisa", "phone": "WRONG_PHONE", "iban": "WRONG_IBAN"}
    )
    
    assert user is None


def test_find_user_wrong_fields_fails():
    """Test find_user_by_fields with all wrong fields returns None.
    
    Validates that providing no correct fields returns None as expected.
    """
    user = find_user_by_fields(
        {"name": "Unknown Person", "phone": "+9999999999", "iban": "XX0000000000"}
    )
    
    assert user is None
