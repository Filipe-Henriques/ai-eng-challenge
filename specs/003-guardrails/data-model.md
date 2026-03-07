# Data Model: Guardrails System

**Feature**: Guardrails System  
**Date**: 2026-03-07  
**Phase**: 1 - Design

## Overview

This document defines the data structures used by the guardrails system. The primary model is `GuardrailResult`, which encapsulates the outcome of all safety evaluations.

---

## Core Entities

### GuardrailResult

**Purpose**: Structured output from guardrail evaluation that encapsulates blocking decisions and sanitized content.

**Usage**: Returned by `run_guardrails()` orchestrator function. Consumed by agent nodes to determine conversation flow and response delivery.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_safe` | `bool` | Yes | `True` if message passed all guardrails checks and conversation can proceed; `False` if message was blocked |
| `blocked_reason` | `str \| None` | Yes | Reason for blocking (`"toxic"`, `"off_topic"`, or `"error"`); `None` if `is_safe=True` |
| `safe_response` | `str \| None` | Yes | Pre-defined message to return when blocked (warning for toxic, refusal for off-topic, error message for failures); `None` if `is_safe=True` |
| `sanitised_response` | `str` | Yes | Agent's proposed response after PII redaction; equals `proposed_response` if user is authenticated or no PII detected |

**Validation Rules**:

- If `is_safe=False`, then `blocked_reason` MUST NOT be `None`
- If `is_safe=False`, then `safe_response` MUST NOT be `None`
- If `is_safe=True`, then `blocked_reason` MUST be `None`
- If `is_safe=True`, then `safe_response` MUST be `None`
- `sanitised_response` is always present (even when blocked, though may be empty string)

**Example Instances**:

```python
# Safe message, no PII
GuardrailResult(
    is_safe=True,
    blocked_reason=None,
    safe_response=None,
    sanitised_response="Your account balance is $1,234.56"
)

# Safe message, PII redacted
GuardrailResult(
    is_safe=True,
    blocked_reason=None,
    safe_response=None,
    sanitised_response="Please call us at [REDACTED] for assistance"
)

# Blocked, toxic language
GuardrailResult(
    is_safe=False,
    blocked_reason="toxic",
    safe_response="I'm sorry, but I'm unable to continue this conversation due to inappropriate language. Please contact our support team at +1800DEUSBANK if you require further assistance.",
    sanitised_response=""
)

# Blocked, off-topic
GuardrailResult(
    is_safe=False,
    blocked_reason="off_topic",
    safe_response="I'm sorry, I can only assist with banking and account-related queries. How can I help you with your DEUS Bank account today?",
    sanitised_response=""
)

# Blocked, system error
GuardrailResult(
    is_safe=False,
    blocked_reason="error",
    safe_response="I'm sorry, but I'm unable to process your request at this time due to a technical issue. Please contact our support team at +1800DEUSBANK for immediate assistance.",
    sanitised_response=""
)
```

---

## Relationships

```
┌─────────────────┐
│  Agent Node     │
│                 │
│  1. Generate    │
│     response    │
└────────┬────────┘
         │
         │ calls
         ▼
┌──────────────────────────────┐
│  run_guardrails()            │
│                              │
│  Inputs:                     │
│  - message: str              │
│  - proposed_response: str    │
│  - is_authenticated: bool    │
└────────┬─────────────────────┘
         │
         │ returns
         ▼
┌─────────────────────────────┐
│  GuardrailResult            │
│                             │
│  - is_safe: bool            │
│  - blocked_reason: str|None │
│  - safe_response: str|None  │
│  - sanitised_response: str  │
└────────┬────────────────────┘
         │
         │ used by agent to decide:
         │
         ├─ if is_safe=False → return safe_response, update state
         │
         └─ if is_safe=True → return sanitised_response
```

---

## State Integration

The guardrails system is **stateless** - it does not read from or write to the LangGraph `State` object directly. However, agents use guardrail results to update state:

**When Blocked**:
- Agent returns `safe_response` from `GuardrailResult`
- If `blocked_reason="toxic"`, agent sets `state.conversation_ended = True`
- `state.current_agent` remains unchanged (conversation ends or declines)

**When Safe**:
- Agent returns `sanitised_response` from `GuardrailResult`
- Conversation proceeds normally
- PII protection is applied transparently (customer never sees `[REDACTED]` unless they're unauthenticated)

---

## Implementation Notes

### Pydantic Model Definition

```python
from pydantic import BaseModel, field_validator

class GuardrailResult(BaseModel):
    """Result of guardrail safety evaluation.
    
    Encapsulates blocking decisions and sanitized responses from the
    guardrail orchestrator. Agents use this to determine conversation flow.
    
    Attributes:
        is_safe: True if message passed all checks.
        blocked_reason: Why message was blocked ("toxic"|"off_topic"|"error"), or None.
        safe_response: Message to return if blocked, or None if safe.
        sanitised_response: Agent response with PII redacted (if unauthenticated).
    """
    
    is_safe: bool
    blocked_reason: str | None
    safe_response: str | None
    sanitised_response: str
    
    @field_validator('blocked_reason', 'safe_response')
    @classmethod
    def check_blocking_fields(cls, v, info):
        """Validate that blocking fields are consistent with is_safe flag."""
        # Validation logic here
        pass
```

### Design Rationale

1. **Explicit over Implicit**: Separate fields for blocking vs sanitization (vs single "response" field)
2. **Type Safety**: `str | None` makes nullable fields explicit
3. **Single Responsibility**: Model only represents result data; no logic
4. **Immutability**: Pydantic models are immutable by default (frozen=True optional)

---

## Alternatives Considered

### Single "response" Field
**Rejected**: Would require agents to check `is_safe` flag and choose between two meanings of "response", adding complexity and error potential.

### Confidence Scores
**Rejected**: Binary blocking is sufficient for MVP; confidence scores would add complexity without clear value.

### Separate Models per Check Type
**Rejected**: Single unified model is simpler for agents; orchestrator handles composition internally.

---

## Summary

- **1 Primary Entity**: `GuardrailResult`
- **4 Required Fields**: All fields are required (though some nullable)
- **Validation**: Pydantic validators ensure `is_safe` flag consistency
- **Usage**: Single-use by agents after guardrail evaluation
- **State Impact**: Stateless evaluation; agents update state based on results

Ready for contract definition (Phase 1 continued).
