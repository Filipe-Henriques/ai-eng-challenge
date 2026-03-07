# Data Model: Specialist Agent

**Feature**: Specialist Agent — Banking Operations Fulfillment  
**Phase**: Phase 1 (Data Design)  
**Date**: 2026-03-07

## Overview

This document defines the data models required for the Specialist Agent's banking tools. The primary addition is extending the existing `Account` model to support balance inquiries, transaction history, fund transfers, and card blocking operations.

## Extended Account Model

### Account (Pydantic Model)

**Location**: `app/models/schemas.py`

**Purpose**: Represents a customer's bank account with all data required for banking operations

**Schema**:
```python
from pydantic import BaseModel
from datetime import datetime

class Transaction(BaseModel):
    """Represents a single banking transaction.
    
    Attributes:
        date: Transaction date in ISO 8601 format (YYYY-MM-DD)
        description: Human-readable transaction description
        amount: Transaction amount (negative for debits, positive for credits)
    """
    date: str
    description: str
    amount: float


class Account(BaseModel):
    """Represents a bank account with full transaction history.
    
    This model extends the original Account (iban + premium) to support
    the Specialist Agent's banking tools.
    
    Attributes:
        user_id: Unique identifier linking to User (for ACCOUNTS_DB lookup)
        iban: International Bank Account Number
        premium: Whether the account holder is a premium client (determines tier)
        balance: Current account balance
        currency: Account currency code (e.g., "EUR", "USD", "GBP")
        transactions: List of recent transactions (newest last)
        card_blocked: Whether the account's card has been reported lost/stolen
    """
    user_id: str
    iban: str
    premium: bool  # Existing field from current Account model
    balance: float
    currency: str
    transactions: list[Transaction]
    card_blocked: bool
```

**Key Design Decisions**:

1. **user_id as Primary Key**: Accounts are looked up by `user_id` (from `verified_user.id` in state), not IBAN, to match the tool signatures
2. **Transaction List**: Stored in chronological order (oldest first) so slicing `[-N:]` gets the most recent N transactions
3. **Negative Amounts**: Debits are negative, credits are positive—standard accounting convention
4. **card_blocked Flag**: Simple boolean sufficient for the challenge (production would have more states: active, blocked, expired, etc.)
5. **Currency String**: ISO 4217 codes (EUR, USD, GBP) rather than enum for simplicity

## Mock Database Structure

### ACCOUNTS_DB (Dictionary)

**Location**: `app/models/database.py`

**Structure**: `dict[str, Account]` where keys are `user_id` strings

**Mock Data**:
```python
ACCOUNTS_DB = {
    "user_001": Account(
        user_id="user_001",
        iban="DE89370400440532013000",  # Lisa
        premium=True,  # VIP tier
        balance=5420.50,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-01", description="Salary Deposit", amount=3000.0),
            Transaction(date="2026-03-02", description="Rent Payment", amount=-1200.0),
            Transaction(date="2026-03-03", description="Grocery Store", amount=-45.20),
            Transaction(date="2026-03-04", description="Online Transfer from John", amount=150.0),
            Transaction(date="2026-03-05", description="Utility Bill", amount=-84.30),
        ],
        card_blocked=False,
    ),
    "user_002": Account(
        user_id="user_002",
        iban="GB29NWBK60161331926819",  # John
        premium=False,  # Standard tier
        balance=1247.80,
        currency="GBP",
        transactions=[
            Transaction(date="2026-03-01", description="Paycheck", amount=2500.0),
            Transaction(date="2026-03-02", description="Transfer to Lisa", amount=-150.0),
            Transaction(date="2026-03-03", description="Restaurant", amount=-62.50),
            Transaction(date="2026-03-04", description="Gas Station", amount=-45.30),
            Transaction(date="2026-03-06", description="Refund", amount=25.00),
        ],
        card_blocked=False,
    ),
    "user_003": Account(
        user_id="user_003",
        iban="FR7630006000011234567890189",  # Maria
        premium=False,  # Standard tier
        balance=325.10,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-01", description="Freelance Payment", amount=500.0),
            Transaction(date="2026-03-02", description="Groceries", amount=-89.40),
            Transaction(date="2026-03-03", description="Coffee Shop", amount=-15.50),
            Transaction(date="2026-03-05", description="ATM Withdrawal", amount=-70.0),
        ],
        card_blocked=False,
    ),
}
```

**Design Notes**:
- Lisa (user_001) has high balance (VIP tier, can make large transfers)
- John (user_002) has moderate balance (Standard tier, typical transactions)
- Maria (user_003) has low balance (tests insufficient funds scenarios)
- All accounts have 4-5 transactions for history testing
- No cards are pre-blocked (clean slate for card blocking tests)

## Tier Mapping

The `customer_tier` field in GraphState is derived from the `Account.premium` field:

| Account.premium | customer_tier (State) | Persona |
|-----------------|----------------------|---------|
| `True` | `"vip"` | Highly personalized, white-glove service |
| `False` | `"standard"` | Concise, efficient support |

**Note**: The spec mentions 3 tiers (Standard, Premium, VIP), but the current codebase only distinguishes `premium` (boolean). For this implementation:
- `premium=False` → "standard" tier
- `premium=True` → "vip" tier
- "premium" tier can be added later if needed by changing `premium` from bool to enum

## Tool Data Models

### Tool Input Types

All tools receive `user_id: str` as their primary parameter. The user_id comes from `state["verified_user"].id` (extracted by the Specialist Agent, never asked from the customer).

**Tool Signatures**:
```python
def get_account_balance(user_id: str) -> dict
def get_transaction_history(user_id: str, limit: int = 5) -> list
def transfer_funds(user_id: str, recipient_iban: str, amount: float, description: str) -> dict
def report_lost_card(user_id: str) -> dict
```

### Tool Output Types

Tools return dictionaries or lists (JSON-serializable) rather than Pydantic models. This keeps the tool interface simple and LLM-friendly.

**Output Examples**:
```python
# get_account_balance success
{"balance": 5420.50, "currency": "EUR"}

# get_account_balance failure
{"error": "Account not found"}

# get_transaction_history success
[
    {"date": "2026-03-05", "description": "Utility Bill", "amount": -84.30},
    {"date": "2026-03-04", "description": "Online Transfer", "amount": 150.0},
    # ...
]

# get_transaction_history failure
[]  # Empty list if account not found

# transfer_funds success
{"success": True, "transaction_id": "TXN-A3F8B91C"}

# transfer_funds failure (insufficient funds)
{"success": False, "transaction_id": None, "reason": "Insufficient funds"}

# transfer_funds failure (invalid IBAN)
{"success": False, "transaction_id": None, "reason": "Invalid IBAN format"}

# report_lost_card success
{"success": True, "case_id": "CASE-7D92E4A1"}

# report_lost_card failure
{"success": False, "case_id": None, "reason": "Account not found"}
```

## State Schema (No Changes)

The Specialist Agent uses existing fields in `GraphState` (defined in `app/graph/state.py`):

**Reads**:
- `verified_user` (User) — for user_id and customer name
- `customer_tier` (str) — "standard", "premium", or "vip"
- `customer_intent` (str) — classified intent from Bouncer
- `messages` (list[BaseMessage]) — conversation history

**Writes**:
- `messages` (list[BaseMessage]) — appends agent responses and tool results
- `conversation_ended` (bool) — sets to True when conversation resolved or turn limit reached

## Validation Rules

### IBAN Validation

**Pattern**: `^[A-Z]{2}[A-Z0-9]{13,32}$`

**Rules**:
1. Must start with exactly 2 uppercase letters (country code)
2. Followed by 13-32 alphanumeric characters
3. Total length: 15-34 characters

**Examples**:
- ✅ Valid: `DE89370400440532013000` (22 chars, starts with DE)
- ✅ Valid: `GB29NWBK60161331926819` (22 chars, starts with GB)
- ❌ Invalid: `DE123` (too short)
- ❌ Invalid: `1234567890123456` (doesn't start with letters)
- ❌ Invalid: `de89370400440532013000` (lowercase letters)

### Transfer Amount Validation

**Rules**:
1. Amount must be positive (`amount > 0`)
2. Amount must not exceed account balance
3. Precision: 2 decimal places (standard currency precision)

### Transaction History Limit Validation

**Rules**:
1. Minimum limit: 1
2. Maximum limit: 20
3. Default limit: 5

**Clamping**: `limit = max(1, min(20, limit))`

## Error Handling

All tools follow a consistent error handling pattern:

1. **Account Not Found**: Return error indicator (empty list or error dict)
2. **Validation Failure**: Return `success=False` with descriptive `reason`
3. **System Error**: Log error, retry once, then return system_error indicator

The Specialist Agent translates these error indicators into natural language responses appropriate for the customer's tier.

## Testing Scenarios

### Data-Driven Test Cases

1. **Balance Inquiry**:
   - user_001 → `{"balance": 5420.50, "currency": "EUR"}`
   - user_999 (non-existent) → `{"error": "Account not found"}`

2. **Transaction History**:
   - user_001, limit=3 → 3 most recent transactions
   - user_002, limit=10 → 5 transactions (only 5 available)
   - user_999, limit=5 → `[]` (empty list)

3. **Fund Transfer**:
   - user_001, 100 EUR → Success (has 5420.50 balance)
   - user_003, 500 EUR → Failure (has only 325.10 balance)
   - user_001, invalid IBAN → Failure (IBAN validation)

4. **Card Blocking**:
   - user_001 → Success, `card_blocked=True` after call
   - user_002 → Success, `card_blocked=True` after call
   - user_999 → Failure (account not found)

## Migration Notes

**No migration required** — this is additive work:
- Extend `Account` model in `schemas.py`
- Add `ACCOUNTS_DB` dictionary in `database.py`
- Add `Transaction` model in `schemas.py`

Existing `find_account_by_iban()` function can remain unchanged (used by Bouncer Agent for tier lookup).
