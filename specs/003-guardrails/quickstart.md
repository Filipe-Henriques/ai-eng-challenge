# Quickstart: Integrating Guardrails

**Feature**: Guardrails System  
**Date**: 2026-03-07  
**Phase**: 1 - Design

## Overview

This guide shows how to integrate the guardrails safety layer into agent nodes. Every agent in the DEUS Bank AI Support System MUST use guardrails to ensure safe, professional, compliant interactions.

---

## Installation

Guardrails are part of the core `app` package. No separate installation required.

```python
from app.guardrails.guardrails import run_guardrails, GuardrailResult
```

---

## Basic Usage

### Step 1: Import

```python
from app.guardrails.guardrails import run_guardrails, GuardrailResult
from app.graph.state import State
from langchain_core.messages import HumanMessage, AIMessage
```

### Step 2: Run Guardrails

```python
def my_agent_node(state: State) -> State:
    """Agent node with guardrail integration."""
    
    # Extract customer message
    customer_message = state["messages"][-1].content
    
    # Generate your agent's response
    proposed_response = "Your account balance is $1,234.56"
    
    # Run guardrails
    result: GuardrailResult = run_guardrails(
        message=customer_message,
        proposed_response=proposed_response,
        is_authenticated=state["is_authenticated"]
    )
    
    # Handle result (see Step 3)
    ...
```

### Step 3: Handle Result

```python
    # Check if message was blocked
    if not result.is_safe:
        # Use the pre-defined safe response
        response_text = result.safe_response
        
        # If toxic, end the conversation
        if result.blocked_reason == "toxic":
            state["conversation_ended"] = True
        
        # Add response to conversation
        state["messages"].append(AIMessage(content=response_text))
        return state
    
    # Message is safe - use sanitized response
    state["messages"].append(AIMessage(content=result.sanitised_response))
    return state
```

---

## Complete Example

```python
from app.guardrails.guardrails import run_guardrails, GuardrailResult
from app.graph.state import State
from langchain_core.messages import AIMessage

def greeter_agent(state: State) -> State:
    """Greeter agent with full guardrail integration."""
    
    # 1. Get customer message
    customer_message = state["messages"][-1].content
    
    # 2. Generate greeting response
    greeting = "Hello! Welcome to DEUS Bank. How can I help you today?"
    
    # 3. Evaluate safety
    result: GuardrailResult = run_guardrails(
        message=customer_message,
        proposed_response=greeting,
        is_authenticated=state.get("is_authenticated", False)
    )
    
    # 4. Handle blocked messages
    if not result.is_safe:
        if result.blocked_reason == "toxic":
            # Toxic language - terminate conversation
            state["conversation_ended"] = True
            state["current_agent"] = "terminated"
        elif result.blocked_reason == "off_topic":
            # Off-topic - politely decline but keep conversation open
            state["current_agent"] = "greeter"
        else:
            # Error - terminate for safety
            state["conversation_ended"] = True
        
        # Return pre-defined safe response
        state["messages"].append(AIMessage(content=result.safe_response))
        return state
    
    # 5. Safe message - return sanitized response
    state["messages"].append(AIMessage(content=result.sanitised_response))
    state["current_agent"] = "bouncer"  # Normal flow continues
    return state
```

---

## Common Patterns

### Pattern 1: Dynamic Response Generation

When your agent generates responses using LLMs:

```python
from langchain_openai import ChatOpenAI

def specialist_agent(state: State) -> State:
    customer_message = state["messages"][-1].content
    
    # Generate LLM response
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_response = llm.invoke(customer_message)
    proposed_response = llm_response.content
    
    # Always run guardrails AFTER generation
    result = run_guardrails(
        message=customer_message,
        proposed_response=proposed_response,
        is_authenticated=state["is_authenticated"]
    )
    
    if not result.is_safe:
        handle_blocked_message(state, result)
        return state
    
    state["messages"].append(AIMessage(content=result.sanitised_response))
    return state
```

### Pattern 2: Pre-Defined Responses

When your agent uses template responses:

```python
def bouncer_agent(state: State) -> State:
    customer_message = state["messages"][-1].content
    
    # Use template response
    proposed_response = (
        f"I found your account under name {state['verified_user'].name}. "
        f"Your secret question is: {state['verified_user'].secret}"
    )
    
    # Guardrails will redact PII if not authenticated
    result = run_guardrails(
        message=customer_message,
        proposed_response=proposed_response,
        is_authenticated=state["is_authenticated"]
    )
    
    if not result.is_safe:
        handle_blocked_message(state, result)
        return state
    
    # For unauthenticated users, [REDACTED] will appear
    state["messages"].append(AIMessage(content=result.sanitised_response))
    return state
```

### Pattern 3: Helper Function

Extract guardrail handling into a reusable helper:

```python
def add_guarded_message(
    state: State,
    proposed_response: str,
    next_agent: str | None = None
) -> State:
    """Add a message with guardrail protection.
    
    Args:
        state: Current conversation state
        proposed_response: Response to evaluate and potentially sanitize
        next_agent: Agent to route to if message is safe (optional)
    
    Returns:
        Updated state with guarded message added
    """
    customer_message = state["messages"][-1].content
    
    result = run_guardrails(
        message=customer_message,
        proposed_response=proposed_response,
        is_authenticated=state.get("is_authenticated", False)
    )
    
    if not result.is_safe:
        # Handle blocked message
        if result.blocked_reason == "toxic":
            state["conversation_ended"] = True
        state["messages"].append(AIMessage(content=result.safe_response))
        return state
    
    # Safe message
    state["messages"].append(AIMessage(content=result.sanitised_response))
    if next_agent:
        state["current_agent"] = next_agent
    return state


# Usage in agent
def my_agent(state: State) -> State:
    response = generate_response(state)
    return add_guarded_message(state, response, next_agent="specialist")
```

---

## Testing Your Integration

### Unit Test with Mocked Guardrails

```python
from unittest.mock import patch
from app.guardrails.guardrails import GuardrailResult

@patch('app.agents.my_agent.run_guardrails')
def test_agent_handles_toxic_message(mock_guardrails):
    """Test that agent properly handles toxic message blocking."""
    
    # Mock guardrails to return blocked result
    mock_guardrails.return_value = GuardrailResult(
        is_safe=False,
        blocked_reason="toxic",
        safe_response="Toxic warning message",
        sanitised_response=""
    )
    
    # Create test state
    state = {
        "messages": [HumanMessage(content="Bad message")],
        "is_authenticated": False,
        "conversation_ended": False
    }
    
    # Run agent
    result_state = my_agent_node(state)
    
    # Verify behavior
    assert result_state["conversation_ended"] == True
    assert "Toxic warning message" in result_state["messages"][-1].content
```

### Integration Test with Real Guardrails

```python
def test_agent_with_real_guardrails():
    """Test agent with actual guardrail evaluation."""
    
    # Create test state with safe message
    state = {
        "messages": [HumanMessage(content="What's my balance?")],
        "is_authenticated": True,
        "conversation_ended": False
    }
    
    # Run agent (guardrails will execute)
    result_state = my_agent_node(state)
    
    # Verify response was added
    assert len(result_state["messages"]) == 2
    assert result_state["conversation_ended"] == False
```

---

## Performance Considerations

### 1. Minimize LLM Calls

```python
# ❌ BAD: Generate response before checking message safety
llm_response = expensive_llm_call(customer_message)
result = run_guardrails(message, llm_response, is_authenticated)

# ✅ GOOD: For simple agents, check message first
# (guardrails short-circuit before expensive response generation)
```

### 2. Batch Operations

If your agent processes multiple messages, call `run_guardrails()` once per message, not once per batch.

### 3. Caching

Don't cache `GuardrailResult` across conversations - authentication status may change.

---

## Troubleshooting

### Issue: PII Not Being Redacted

**Symptom**: Phone numbers or IBANs appear in responses to unauthenticated users.

**Solutions**:
1. Verify `is_authenticated=False` is passed to `run_guardrails()`
2. Check that PII matches regex patterns (uppercase IBANs, international phone format)
3. Confirm you're returning `result.sanitised_response`, not `proposed_response`

### Issue: Legitimate Messages Being Blocked

**Symptom**: Banking terms trigger off-topic filter.

**Solutions**:
1. Review the topic classification prompt in `app/guardrails/guardrails.py`
2. Check if customer message contains explicit banking terminology
3. File bug report with example message for prompt tuning

### Issue: High Latency

**Symptom**: Guardrails taking >500ms consistently.

**Solutions**:
1. Check OpenAI API latency (may be network-related)
2. Verify you're using `gpt-4o-mini`, not larger model
3. Monitor metrics to identify which check is slow (toxicity vs topic)

---

## Best Practices

### ✅ DO

- Call `run_guardrails()` for every agent response
- Handle both `is_safe=True` and `is_safe=False` cases
- Set `conversation_ended=True` for toxic messages
- Use `result.sanitised_response` for safe messages
- Use `result.safe_response` for blocked messages
- Pass correct `is_authenticated` status from state

### ❌ DON'T

- Don't call individual check functions (`check_toxicity`, `check_topic`, `check_pii`)
- Don't skip guardrails for "trusted" inputs
- Don't modify `GuardrailResult` after receiving it
- Don't cache results across different conversations
- Don't log message content in guardrail calls
- Don't retry on `is_safe=False` (respect blocking decision)

---

## Additional Resources

- **API Contract**: [contracts/guardrails.md](contracts/guardrails.md)
- **Data Model**: [data-model.md](data-model.md)
- **Research**: [research.md](research.md)
- **Spec**: [spec.md](spec.md)

---

## Support

For questions or issues:
1. Check this quickstart for common patterns
2. Review the contract document for API details
3. Inspect test cases in `tests/test_guardrails.py` for examples
4. File issues with reproduction steps

---

**You're ready to integrate guardrails!** Start with the basic usage pattern and adapt as needed for your agent's specific requirements.
