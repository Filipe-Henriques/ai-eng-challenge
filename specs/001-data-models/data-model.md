# Data Model Documentation: Data Models & Mock Database

**Feature**: 001-data-models  
**Created**: 2026-03-07  
**Purpose**: Complete schema reference for all Pydantic models and mock database

---

## Overview

This document provides the complete data model specifications for the DEUS Bank AI Support System. All models are defined using Pydantic v2 and serve as the single source of truth for data structures across agents, guardrails, and the API layer.

---

## 1. User Model

**Module**: `app.models.schemas`  
**Class**: `User`  
**Purpose**: Represents a registered bank customer used for identity verification

### Schema

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | `str` | Yes | Customer's full name | `"Lisa"` |
| `phone` | `str` | Yes | Phone number in international format | `"+1122334455"` |
| `iban` | `str` | Yes | IBAN in standard format | `"DE89370400440532013000"` |
| `secret` | `str` | Yes | Security question shown to customer | `"Which is the name of my dog?"` |
| `answer` | `str` | Yes | Correct answer to security question | `"Yoda"` |

### Validation Rules

- All fields are required (no defaults)
- No format validation on phone/IBAN (assumes pre-validated data)
- Secret questions and answers are case-sensitive

### Usage Context

- Used by Bouncer Agent for identity verification
- Lookup via `find_user_by_fields()` with 2-out-of-3 matching
- Secret question displayed after successful identity match
- Answer verified before granting access

### Pydantic Definition

```python
from pydantic import BaseModel

class User(BaseModel):
    """Represents a registered bank customer used for identity verification.
    
    Attributes:
        name: Customer's full name
        phone: Phone number in international format (e.g., +1122334455)
        iban: IBAN in standard format (e.g., DE89370400440532013000)
        secret: Security question shown to the customer
        answer: Correct answer to the security question
    """
    name: str
    phone: str
    iban: str
    secret: str
    answer: str
```

---

## 2. Account Model

**Module**: `app.models.schemas`  
**Class**: `Account`  
**Purpose**: Represents a bank account used to determine customer tier

### Schema

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `iban` | `str` | Yes | Account IBAN (primary key) | `"DE89370400440532013000"` |
| `premium` | `bool` | Yes | Premium tier status | `True` |

### Validation Rules

- All fields are required
- IBAN serves as the lookup key
- Boolean field has no default (must be explicitly True or False)

### Usage Context

- Used by Specialist Agent for routing decisions
- Lookup via `find_account_by_iban()`
- Premium customers routed to premium support
- Regular customers routed to standard support

### Pydantic Definition

```python
from pydantic import BaseModel

class Account(BaseModel):
    """Represents a bank account used to determine customer tier.
    
    Attributes:
        iban: Account IBAN (used as primary key for lookups)
        premium: Whether the account holder is a premium client
    """
    iban: str
    premium: bool
```

---

## 3. ChatRequest Model

**Module**: `app.models.schemas`  
**Class**: `ChatRequest`  
**Purpose**: Request body for the FastAPI chat endpoint

### Schema

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `session_id` | `str` | Yes | Unique conversation identifier | `"sess_abc123"` |
| `message` | `str` | Yes | Customer's input message | `"I need help with my account"` |

### Validation Rules

- All fields are required
- No format constraints on session_id (client-provided)
- Message can be any non-empty string

### Usage Context

- Received by FastAPI chat endpoint
- Session ID used to maintain conversation state in LangGraph
- Message is the user input to be processed by the agent pipeline

### Pydantic Definition

```python
from pydantic import BaseModel

class ChatRequest(BaseModel):
    """Request body for the chat API endpoint.
    
    Attributes:
        session_id: Unique identifier for the conversation session
        message: The customer's input message
    """
    session_id: str
    message: str
```

---

## 4. ChatResponse Model

**Module**: `app.models.schemas`  
**Class**: `ChatResponse`  
**Purpose**: Response body for the FastAPI chat endpoint

### Schema

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `session_id` | `str` | Yes | Matching conversation identifier | `"sess_abc123"` |
| `response` | `str` | Yes | Agent's response message | `"I can help you with that..."` |
| `agent` | `str` | Yes | Name of responding agent | `"greeter"` |

### Validation Rules

- All fields are required
- session_id must match the request session_id
- agent must be one of: `"greeter"`, `"bouncer"`, `"specialist"`

### Usage Context

- Returned by FastAPI chat endpoint
- Response contains the agent's natural language reply
- Agent field indicates which agent in the pipeline produced the response

### Pydantic Definition

```python
from pydantic import BaseModel

class ChatResponse(BaseModel):
    """Response body for the chat API endpoint.
    
    Attributes:
        session_id: The conversation session identifier (matches request)
        response: The agent's response message
        agent: Name of the agent that produced the response (e.g., "greeter", "bouncer", "specialist")
    """
    session_id: str
    response: str
    agent: str
```

---

## 5. Mock Database

**Module**: `app.models.database`  
**Purpose**: In-memory data store for development and testing

### MOCK_USERS

List of 3 User objects representing test customer scenarios:

#### Lisa (Premium Customer with Account)
```python
User(
    name="Lisa",
    phone="+1122334455",
    iban="DE89370400440532013000",
    secret="Which is the name of my dog?",
    answer="Yoda"
)
```

#### John (Regular Customer with Account)
```python
User(
    name="John",
    phone="+1987654321",
    iban="GB29NWBK60161331926819",
    secret="What is your mother's maiden name?",
    answer="Smith"
)
```

#### Maria (Customer without Account)
```python
User(
    name="Maria",
    phone="+1555000111",
    iban="FR7630006000011234567890189",
    secret="What was the name of your first pet?",
    answer="Fluffy"
)
```

**Test Scenarios Covered**:
- Lisa: Premium client with account (tests premium routing)
- John: Regular client with account (tests standard routing)
- Maria: User without bank account (tests non-client flow)

### MOCK_ACCOUNTS

List of 2 Account objects (Maria intentionally excluded):

```python
MOCK_ACCOUNTS = [
    Account(iban="DE89370400440532013000", premium=True),   # Lisa - Premium
    Account(iban="GB29NWBK60161331926819", premium=False),  # John - Regular
]
```

**Coverage**:
- 1 premium account (Lisa)
- 1 regular account (John)
- 1 user with no account (Maria) - tests edge case

---

## 6. Database Functions

### find_user_by_fields

**Signature**: `find_user_by_fields(fields: dict) -> User | None`

**Purpose**: Implements 2-out-of-3 identity verification logic (Constitution Principle III)

**Parameters**:
- `fields`: Dictionary with optional keys: `name`, `phone`, `iban`

**Returns**:
- `User` object if 2 or more fields match
- `None` if fewer than 2 fields match

**Matching Logic**:
1. Iterate over all users in `MOCK_USERS`
2. For each user, count matching fields:
   - `name`: Case-insensitive comparison (`fields['name'].lower() == user.name.lower()`)
   - `phone`: Exact match (`fields['phone'] == user.phone`)
   - `iban`: Exact match (`fields['iban'] == user.iban`)
3. If match count >= 2, return user immediately (first match wins)
4. If no user has 2+ matches, return None

**Example Usage**:
```python
# Success: 2 fields match
user = find_user_by_fields({"name": "Lisa", "phone": "+1122334455"})
# Returns: User(name="Lisa", ...)

# Success: Case-insensitive name
user = find_user_by_fields({"name": "lisa", "phone": "+1122334455"})
# Returns: User(name="Lisa", ...)

# Failure: Only 1 field matches
user = find_user_by_fields({"name": "Lisa", "phone": "WRONG"})
# Returns: None

# Success: All 3 fields match
user = find_user_by_fields({"name": "John", "phone": "+1987654321", "iban": "GB29NWBK60161331926819"})
# Returns: User(name="John", ...)
```

**Security Note**: This function implements the core 2-out-of-3 verification requirement from the constitution. It prevents account access with only 1 piece of information.

### find_account_by_iban

**Signature**: `find_account_by_iban(iban: str) -> Account | None`

**Purpose**: Lookup account by IBAN to determine customer tier

**Parameters**:
- `iban`: IBAN string to search for

**Returns**:
- `Account` object if IBAN matches
- `None` if IBAN not found

**Matching Logic**:
1. Iterate over all accounts in `MOCK_ACCOUNTS`
2. Return first account where `account.iban == iban` (exact match)
3. Return None if no match found

**Example Usage**:
```python
# Premium account (Lisa)
account = find_account_by_iban("DE89370400440532013000")
# Returns: Account(iban="DE89370400440532013000", premium=True)

# Regular account (John)
account = find_account_by_iban("GB29NWBK60161331926819")
# Returns: Account(iban="GB29NWBK60161331926819", premium=False)

# No account (Maria)
account = find_account_by_iban("FR7630006000011234567890189")
# Returns: None

# Unknown IBAN
account = find_account_by_iban("UNKNOWN")
# Returns: None
```

---

## 7. Entity Relationships

```
User (1) -------- (0..1) Account
  |
  | Linked by: iban field
  |
  └─> Some users have accounts (Lisa, John)
  └─> Some users don't (Maria)
```

**Relationship Rules**:
- One user can have zero or one account
- Account is identified by iban (same field in User)
- No foreign key constraints (in-memory mock data)

---

## 8. Data Flow

### Identity Verification Flow
```
1. User provides credentials (name, phone, iban)
   ↓
2. Call find_user_by_fields(credentials)
   ↓
3. If User found (2+ matches):
   → Show user.secret question
   → User provides answer
   → Verify answer == user.answer
   ↓
4. If verified:
   → Call find_account_by_iban(user.iban)
   → Route based on account.premium status
```

### API Request Flow
```
Client → ChatRequest → FastAPI Endpoint
                           ↓
                    LangGraph Pipeline
                    (processes with agents)
                           ↓
                    ChatResponse ← FastAPI Endpoint ← Client
```

---

## 9. Import Patterns

### Models
```python
from app.models.schemas import User, Account, ChatRequest, ChatResponse
```

### Database
```python
from app.models.database import (
    MOCK_USERS,
    MOCK_ACCOUNTS,
    find_user_by_fields,
    find_account_by_iban
)
```

---

## 10. Testing Strategy

### Model Validation Tests
- Test Pydantic validation rejects missing fields
- Test all models can be instantiated with valid data
- Test serialization/deserialization

### Database Function Tests
- **find_user_by_fields**:
  - 2-field match (name + phone) → Success
  - 3-field match (all fields) → Success
  - 1-field match → Failure (None)
  - 0-field match → Failure (None)
  - Case-insensitive name → Success
  - Test all 3 users can be found

- **find_account_by_iban**:
  - Lisa's IBAN → Returns premium account
  - John's IBAN → Returns regular account
  - Maria's IBAN → Returns None
  - Invalid IBAN → Returns None

**Coverage Target**: 100% of database.py module

---

## 11. Constitution Alignment

### ✅ Principle V: Clean Architecture

- Models contain **only data definitions** (no business logic)
- Database functions are **pure data access** (no side effects)
- Located in `app/models/` as mandated
- No dependencies on agents, guardrails, or LangGraph

### ✅ Principle III: Security by Design

- `find_user_by_fields` implements **2-out-of-3 verification**
- Prevents account access with insufficient information
- Case-insensitive name matching (user experience without compromising security)

### ✅ Technology Stack Compliance

- Uses **Pydantic v2** as mandated
- All models inherit from `BaseModel`
- Uses native Python 3.11+ type hints (`str | None`)

---

**End of Data Model Documentation**