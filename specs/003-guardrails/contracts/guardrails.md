# Contract: Guardrails API

**Feature**: Guardrails System  
**Date**: 2026-03-07  
**Phase**: 1 - Design  
**Status**: Draft

## Overview

This document defines the public API contract for the guardrails safety layer. All agent nodes in the LangGraph pipeline MUST use this interface to evaluate message safety and sanitize responses.

---

## Public Interface

### Primary Function: `run_guardrails`

**Purpose**: Orchestrate all safety checks (toxicity, topic, PII) and return unified evaluation result.

**Signature**:

```python
def run_guardrails(
    message: str,
    proposed_response: str,
    is_authenticated: bool
) -> GuardrailResult:
    """Evaluate message safety and sanitize response.
    
    Performs three safety checks in priority order:
    1. Toxicity detection (blocks abusive language)
    2. Topic filtering (blocks off-topic requests)
    3. PII protection (redacts sensitive data for unauthenticated users)
    
    Args:
        message: Customer's incoming message to evaluate for safety.
        proposed_response: Agent's proposed response to check for PII leakage.
        is_authenticated: Whether customer has passed identity verification.
                         If False, PII will be redacted from proposed_response.
    
    Returns:
        GuardrailResult with blocking decision and sanitized response.
        
    Raises:
        Does not raise exceptions. Failures are caught and returned as
        GuardrailResult(is_safe=False, blocked_reason="error", ...).
    
    Examples:
        >>> # Safe message, no PII
        >>> result = run_guardrails(
        ...     message="What's my balance?",
        ...     proposed_response="Your balance is $1,234.56",
        ...     is_authenticated=True
        ... )
        >>> result.is_safe
        True
        >>> result.sanitised_response
        "Your balance is $1,234.56"
        
        >>> # Safe message, PII redacted
        >>> result = run_guardrails(
        ...     message="How do I contact you?",
        ...     proposed_response="Call us at +1122334455",
        ...     is_authenticated=False
        ... )
        >>> result.is_safe
        True
        >>> result.sanitised_response
        "Call us at [REDACTED]"
        
        >>> # Toxic message blocked
        >>> result = run_guardrails(
        ...     message="You're useless!",
        ...     proposed_response="",
        ...     is_authenticated=False
        ... )
        >>> result.is_safe
        False
        >>> result.blocked_reason
        "toxic"
    """
```

**Contract Guarantees**:

1. **Never Raises Exceptions**: All errors are caught and returned as `is_safe=False` with `blocked_reason="error"`
2. **Deterministic PII Detection**: Same input + authentication status always produces same PII redaction
3. **Short-Circuit Evaluation**: If message is blocked (toxic/off-topic), `proposed_response` is not evaluated
4. **Performance**: Completes within 500ms for 95% of calls (per spec SC-001, SC-002)
5. **Immutability**: Does not modify input arguments

**Integration Pattern for Agents**:

```python
from app.guardrails.guardrails import run_guardrails, GuardrailResult
from app.graph.state import State

def my_agent_node(state: State) -> State:
    """Example agent node with guardrail integration."""
    
    # 1. Extract customer message
    customer_message = state["messages"][-1].content
    
    # 2. Generate agent response (LLM call, business logic, etc.)
    proposed_response = generate_response(customer_message)
    
    # 3. Run guardrails
    result: GuardrailResult = run_guardrails(
        message=customer_message,
        proposed_response=proposed_response,
        is_authenticated=state["is_authenticated"]
    )
    
    # 4. Handle result
    if not result.is_safe:
        # Message blocked - return safe response and potentially end conversation
        if result.blocked_reason == "toxic":
            state["conversation_ended"] = True
        return add_message(state, result.safe_response)
    
    # 5. Message safe - return sanitized response
    return add_message(state, result.sanitised_response)
```

---

## Supporting Types

### `GuardrailResult`

See [data-model.md](../data-model.md) for complete definition.

**Fields**:
- `is_safe: bool` - Whether message passed all checks
- `blocked_reason: str | None` - Blocking reason (`"toxic"` | `"off_topic"` | `"error"`) or `None`
- `safe_response: str | None` - Pre-defined message for blocked requests, or `None`
- `sanitised_response: str` - Response with PII redacted (if unauthenticated)

---

## Private Functions (Internal Use Only)

These functions are implementation details and MUST NOT be called directly by agents. They are documented here for completeness.

### `check_toxicity`

```python
def check_toxicity(message: str) -> str | None:
    """Check if message contains toxic language. Returns warning message if toxic, None if safe."""
```

### `check_topic`

```python
def check_topic(message: str) -> str | None:
    """Check if message is on-topic for banking. Returns refusal message if off-topic, None if on-topic."""
```

### `check_pii`

```python
def check_pii(response: str, is_authenticated: bool) -> str:
    """Redact PII from response if user is not authenticated. Returns sanitized response."""
```

**Why Private**: These functions are composed by `run_guardrails()` in the correct order. Direct usage bypasses orchestration logic and may result in incorrect behavior (e.g., skipping toxicity check).

---

## Pre-Defined Messages

All blocking messages are defined as module-level constants:

```python
OFF_TOPIC_REFUSAL = (
    "I'm sorry, I can only assist with banking and account-related queries. "
    "How can I help you with your DEUS Bank account today?"
)

TOXICITY_WARNING = (
    "I'm sorry, but I'm unable to continue this conversation due to inappropriate language. "
    "Please contact our support team at +1800DEUSBANK if you require further assistance."
)

ERROR_MESSAGE = (
    "I'm sorry, but I'm unable to process your request at this time due to a technical issue. "
    "Please contact our support team at +1800DEUSBANK for immediate assistance."
)
```

**Rationale**: Constants ensure consistent messaging and allow future configurability.

---

## Error Handling Contract

### Failure Modes

| Scenario | Behavior |
|----------|----------|
| OpenAI API timeout | Return `GuardrailResult(is_safe=False, blocked_reason="error", safe_response=ERROR_MESSAGE)` |
| OpenAI API error | Same as timeout |
| Network failure | Same as timeout |
| Unexpected exception | Caught and returned as error (fail-closed) |
| Invalid input types | Pydantic validation error (caller's responsibility to provide correct types) |

### No Retries

The guardrails layer does NOT retry failed operations. Rationale:
- Retries add latency (already at 200ms target)
- Customer can re-submit message if needed
- Fail-closed policy means errors favor blocking

### Observability

Guardrails emit basic metrics (see spec FR-014):
- Block counts by type ("toxic", "off_topic")
- PII redaction count (authenticated vs unauthenticated)
- Processing latency (per check type)
- Error rate

Metrics do NOT include message content (privacy/security requirement).

---

## Versioning & Compatibility

**Version**: 1.0.0 (initial implementation)

**Breaking Changes Policy**:
- Function signature changes require major version bump
- `GuardrailResult` field additions are non-breaking (existing consumers ignore new fields)
- `GuardrailResult` field removals are breaking
- Change to pre-defined message text is non-breaking (content, not structure)

**Deprecation**: Not applicable for initial release.

---

## Testing Contract

### Unit Test Requirements

All agent nodes using guardrails MUST mock `run_guardrails()` in unit tests:

```python
from unittest.mock import patch, MagicMock
from app.guardrails.guardrails import GuardrailResult

@patch('app.agents.my_agent.run_guardrails')
def test_agent_handles_blocked_message(mock_guardrails):
    """Test agent behavior when message is blocked."""
    mock_guardrails.return_value = GuardrailResult(
        is_safe=False,
        blocked_reason="toxic",
        safe_response="Warning message",
        sanitised_response=""
    )
    
    result = my_agent_node(test_state)
    
    assert result["conversation_ended"] == True
```

### Integration Test Requirements

Integration tests for the guardrails module itself MUST cover:
1. All three checks (toxicity, topic, PII) independently
2. Orchestration logic (short-circuit evaluation)
3. Error handling (mock timeouts and exceptions)
4. Performance (verify <500ms p95 latency)

---

## Security Considerations

1. **PII Redaction**: `[REDACTED]` replacement is irreversible; original cannot be recovered
2. **No Content Logging**: Guardrail functions MUST NOT log `message` or `proposed_response` content
3. **Fail-Closed**: All errors block conversation; never fail open
4. **Authentication Trust**: Assumes `is_authenticated` flag is correctly set by bouncer agent
5. **Regex Limitations**: PII regex may have false positives (e.g., non-phone numeric codes); this is acceptable (err on side of caution)

---

## Dependencies

- **OpenAI Python SDK**: For `gpt-4o-mini` LLM calls
- **Pydantic v2**: For `GuardrailResult` model
- **Python `re` module**: For PII regex matching

No external services beyond OpenAI API are required.

---

## Summary

**Public API**:
- ✅ `run_guardrails(message, proposed_response, is_authenticated) -> GuardrailResult`

**Guarantees**:
- ✅ Never raises exceptions (fails closed)
- ✅ Deterministic for same inputs
- ✅ <500ms p95 latency
- ✅ <5% false positive rate

**Agent Integration**: Single function call, handle `GuardrailResult`, update state appropriately.

**Next Step**: See [quickstart.md](../quickstart.md) for integration examples.
