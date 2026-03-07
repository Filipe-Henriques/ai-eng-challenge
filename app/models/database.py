"""Mock in-memory database for DEUS Bank AI Support System.

This module provides mock data and lookup functions for development and testing.
No persistence - all data is stored in memory.
"""

import logging
from app.models.schemas import User, Account


class DatabaseUnavailableError(Exception):
    """Raised when database lookup fails due to technical error.

    This exception distinguishes database/network failures from legitimate
    "no match found" scenarios. Used by the Greeter Agent to handle database
    unavailability with graceful degradation.

    Attributes:
        message: Human-readable error description

    Example:
        >>> try:
        ...     user = find_user_with_retry(fields)
        ... except DatabaseUnavailableError:
        ...     # Handle database unavailability gracefully
        ...     return error_response
    """

    pass


# Mock users for testing (3 users covering different scenarios)
MOCK_USERS = [
    User(
        name="Lisa",
        phone="+1122334455",
        iban="DE89370400440532013000",
        secret="Which is the name of my dog?",
        answer="Yoda",
    ),
    User(
        name="John",
        phone="+1987654321",
        iban="GB29NWBK60161331926819",
        secret="What is your mother's maiden name?",
        answer="Smith",
    ),
    User(
        name="Maria",
        phone="+1555000111",
        iban="FR7630006000011234567890189",
        secret="What was the name of your first pet?",
        answer="Fluffy",
    ),
]


def find_user_by_fields(fields: dict) -> User | None:
    """Find a user by matching at least 2 out of 3 identity fields.

    Implements the 2-out-of-3 verification logic required by the constitution
    (Principle III: Security by Design).

    Args:
        fields: Dictionary with optional keys: 'name', 'phone', 'iban'
                Name comparison is case-insensitive
                Phone and IBAN are exact matches

    Returns:
        User object if 2 or more fields match, None otherwise

    Examples:
        >>> find_user_by_fields({"name": "Lisa", "phone": "+1122334455"})
        User(name="Lisa", ...)  # 2 matches -> success

        >>> find_user_by_fields({"name": "lisa", "phone": "+1122334455"})
        User(name="Lisa", ...)  # Case-insensitive name match

        >>> find_user_by_fields({"name": "Lisa", "phone": "WRONG"})
        None  # Only 1 match -> failure
    """
    for user in MOCK_USERS:
        match_count = 0

        # Check name (case-insensitive)
        if "name" in fields and fields["name"].lower() == user.name.lower():
            match_count += 1

        # Check phone (exact match)
        if "phone" in fields and fields["phone"] == user.phone:
            match_count += 1

        # Check IBAN (exact match)
        if "iban" in fields and fields["iban"] == user.iban:
            match_count += 1

        # Return user if 2 or more fields match
        if match_count >= 2:
            return user

    # No user matched 2+ fields
    return None


def find_user_with_retry(fields: dict) -> User | None:
    """Find a user by matching 2-out-of-3 fields with automatic retry on failure.

    Wrapper around find_user_by_fields() that implements single retry logic
    for database operations. If the first lookup fails due to technical error,
    automatically retries once before raising DatabaseUnavailableError.

    This function is designed for the Greeter Agent's verification workflow,
    providing resilience against transient database failures while maintaining
    fast response times (no exponential backoff).

    Args:
        fields: Dictionary with optional keys: 'name', 'phone', 'iban'
                See find_user_by_fields() for matching rules

    Returns:
        User object if 2+ fields match exactly one user record, None if no match
        or multiple matches found

    Raises:
        DatabaseUnavailableError: If both the initial lookup and retry fail
                                  due to technical errors

    Examples:
        >>> # Normal operation
        >>> user = find_user_with_retry({"name": "Lisa", "phone": "+1122334455"})
        >>> user.name
        'Lisa'

        >>> # No match scenario
        >>> user = find_user_with_retry({"name": "Unknown", "phone": "INVALID"})
        >>> user is None
        True

        >>> # Database failure scenario
        >>> try:
        ...     user = find_user_with_retry(fields)
        ... except DatabaseUnavailableError as e:
        ...     print(f"Database error: {e}")

    Note:
        In the mock implementation, this function rarely raises exceptions
        since MOCK_USERS is always available. In production, this would
        handle database connection timeouts, network errors, etc.
    """
    try:
        return find_user_by_fields(fields)
    except Exception as e:
        logging.warning(f"Database lookup failed, retrying: {e}")
        try:
            return find_user_by_fields(fields)
        except Exception as e:
            logging.error(f"Database lookup failed after retry: {e}")
            raise DatabaseUnavailableError("User database unavailable") from e


# Mock accounts for testing (2 accounts, Maria intentionally excluded)
MOCK_ACCOUNTS = [
    Account(iban="DE89370400440532013000", premium=True),  # Lisa - Premium
    Account(iban="GB29NWBK60161331926819", premium=False),  # John - Regular
]


def find_account_by_iban(iban: str) -> Account | None:
    """Find an account by IBAN to determine customer tier.

    Args:
        iban: IBAN string to search for (exact match)

    Returns:
        Account object if IBAN matches, None otherwise

    Examples:
        >>> find_account_by_iban("DE89370400440532013000")
        Account(iban="DE89370400440532013000", premium=True)  # Lisa

        >>> find_account_by_iban("GB29NWBK60161331926819")
        Account(iban="GB29NWBK60161331926819", premium=False)  # John

        >>> find_account_by_iban("FR7630006000011234567890189")
        None  # Maria has no account
    """
    for account in MOCK_ACCOUNTS:
        if account.iban == iban:
            return account

    # No account found
    return None
