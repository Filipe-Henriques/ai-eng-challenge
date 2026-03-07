# Data Model: Greeter Agent

**Feature**: 004-greeter-agent  
**Date**: 2026-03-07  
**Purpose**: Define all data structures (Pydantic models, TypedDict extensions) used by the Greeter Agent

---

## 1. Overview

The Greeter Agent operates on the shared `State` TypedDict (defined in `app/graph/state.py`) and introduces one new internal model for structured LLM output.

**State Fields Used by Greeter**:
- `messages`: Conversation history (read latest user message, append agent responses)
- `collected_fields`: Dict of extracted identity fields `{"name": str | None, "phone": str | None, "iban": str | None}`
- `verification_attempts`: Int counter for failed verification/authentication attempts
- `verified_user`: User object from database (set after 2/3 match succeeds)
- `is_authenticated`: Boolean flag (set after secret question answered correctly)
- `current_agent`: String agent name (set to "bouncer" after authentication)
- `conversation_ended`: Boolean flag (set on max attempts or database failure)

---

## 2. ExtractedInfo Model (Internal)

**Location**: `app/agents/greeter.py` (defined within agent file, not exported)

**Purpose**: Pydantic model for LangChain structured output. Extracts identity fields from user's free-text message.

**Definition**:
```python
from pydantic import BaseModel, Field

class ExtractedInfo(BaseModel):
    """Structured extraction of identity fields from user message.
    
    Used with LangChain's with_structured_output() to parse user-provided
    identifying information. All fields are optional because the user may
    provide them incrementally across multiple turns.
    
    Attributes:
        name: Customer's full name, or None if not mentioned in message
        phone: Customer's phone number with country code (e.g., "+1122334455"),
               or None if not mentioned
        iban: Customer's IBAN (International Bank Account Number), or None if
              not mentioned
    """
    name: str | None = Field(
        default=None,
        description="Customer's full name as mentioned in the message"
    )
    phone: str | None = Field(
        default=None,
        description="Phone number with country code (e.g., '+1122334455')"
    )
    iban: str | None = Field(
        default=None,
        description="IBAN (International Bank Account Number)"
    )
```

**Validation**:
- No format validation (accept whatever user provides)
- Rationale: Flexible input, validation happens during database lookup
- LLM is responsible for extracting values as user intended

**Usage**:
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
extractor = llm.with_structured_output(ExtractedInfo)

# Example: user says "I'm Lisa and my phone is +1122334455"
result = extractor.invoke([
    SystemMessage(content="Extract name, phone, and IBAN from the user's message"),
    HumanMessage(content="I'm Lisa and my phone is +1122334455")
])

# result.name == "Lisa"
# result.phone == "+1122334455"
# result.iban == None
```

---

## 3. State Field: collected_fields

**Type**: `dict[str, str | None]`

**Structure**:
```python
{
    "name": str | None,   # Customer name (case-insensitive matching)
    "phone": str | None,  # Phone number (exact match required)
    "iban": str | None    # IBAN (exact match required)
}
```

**Initialization**: All keys present with `None` values at session start

**Update Pattern**: Merge non-None extracted fields
```python
# Current state
collected_fields = {"name": None, "phone": None, "iban": None}

# User provides: "My name is Lisa"
extracted = ExtractedInfo(name="Lisa", phone=None, iban=None)

# Merge (only update non-None)
for key in ["name", "phone", "iban"]:
    if getattr(extracted, key) is not None:
        collected_fields[key] = getattr(extracted, key)

# Result: {"name": "Lisa", "phone": None, "iban": None}
```

**Rationale**: 
- Preserves previously collected fields
- Supports incremental collection across multiple turns
- User can provide all three at once or one at a time

---

## 4. User Model (Existing)

**Location**: `app/models/schemas.py` (already defined)

**Fields Used by Greeter**:
```python
class User(BaseModel):
    name: str          # For 2/3 verification (case-insensitive)
    phone: str         # For 2/3 verification (exact match)
    iban: str          # For 2/3 verification (exact match)
    secret: str        # Secret question text (shown after verification)
    answer: str        # Expected answer (case-insensitive comparison)
```

**Security Note**: 
- ✅ `secret` field is revealed to user after verification passes
- ⚠️ `answer` field MUST NEVER be exposed to user or logged
- LLM system prompt enforces: never mention the expected answer

---

## 5. Database Exceptions (New)

**Location**: `app/models/database.py` (add to existing file)

**Purpose**: Distinguish database failures from "no match" scenarios

**Definition**:
```python
class DatabaseUnavailableError(Exception):
    """Raised when database lookup fails due to technical error."""
    pass
```

**Usage**:
```python
def find_user_with_retry(fields: dict) -> User | None:
    """Attempt user lookup with one retry on failure."""
    try:
        return find_user_by_fields(fields)
    except Exception as e:
        logging.warning(f"Database lookup failed, retrying: {e}")
        try:
            return find_user_by_fields(fields)
        except Exception as e:
            logging.error(f"Database lookup failed after retry: {e}")
            raise DatabaseUnavailableError("User database unavailable") from e
```

**Handling in Agent**:
```python
try:
    user = find_user_with_retry(collected_fields)
    # Process user...
except DatabaseUnavailableError:
    return {
        "messages": [AIMessage(content="I'm having trouble accessing your information...")],
        "conversation_ended": True
    }
```

---

## 6. Summary

**New Models**:
1. `ExtractedInfo` (Pydantic) — Internal to greeter.py
2. `DatabaseUnavailableError` (Exception) — Added to database.py

**Existing Models Used**:
1. `State` (TypedDict) — Read/write multiple fields
2. `User` (Pydantic) — Returned by database lookup

**No State Schema Changes**: All required fields already exist in `app/graph/state.py`

**Data Flow**:
```
User Message → ExtractedInfo (LLM) → collected_fields (State)
collected_fields → find_user_by_fields() → User | None
User → verified_user (State)
User.secret → Show to user
User.answer → Compare with user's response (never expose)
```
