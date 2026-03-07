# Contract: Greeter Agent Interface

**Feature**: 004-greeter-agent  
**Date**: 2026-03-07  
**Purpose**: Define the public interface contract for integrating the Greeter Agent into the LangGraph pipeline

---

## 1. Node Function Signature

```python
def greeter_agent(state: State) -> dict:
    """Greeter Agent node for customer identity verification and authentication.
    
    This is the entry point to the DEUS Bank AI Support System. The agent welcomes
    customers, collects their identifying information incrementally, verifies their
    identity using the 2-out-of-3 rule, and authenticates them via a secret question.
    
    Args:
        state: The current LangGraph State containing conversation history,
               collected fields, verification attempts, and user information
    
    Returns:
        dict: Partial state updates to be merged into the graph state.
              May include: messages, collected_fields, verification_attempts,
              verified_user, is_authenticated, current_agent, conversation_ended
    
    Behavior:
        - Reads latest user message from state["messages"][-1]
        - Applies input guardrails (rejects unsafe/off-topic messages)
        - Extracts identity fields (name, phone, iban) using LLM structured output
        - Attempts 2/3 verification when >= 2 fields collected
        - Asks secret question after identity verified
        - Checks secret answer (case-insensitive)
        - Applies output guardrails before returning response
        - Enforces max 3 attempts (verification + authentication failures combined)
        - Handles database failures with single retry
    
    Termination Conditions:
        - is_authenticated set to True → hands off to Bouncer (current_agent="bouncer")
        - verification_attempts >= 3 → ends conversation (conversation_ended=True)
        - Database failure after retry → ends conversation (conversation_ended=True)
    
    Side Effects:
        - Calls run_guardrails() for input/output safety checks
        - Calls find_user_by_fields() for database lookups (with retry)
        - Uses OpenAI LLM (gpt-4o-mini) for response generation and field extraction
    
    Raises:
        No exceptions raised (all errors handled internally with conversation_ended)
    """
    pass
```

---

## 2. Input Contract (State Fields Read)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `list[BaseMessage]` | ✅ Yes | Conversation history. Agent reads `messages[-1]` for latest user message. |
| `collected_fields` | `dict[str, str \| None]` | ⚠️ Initialize if missing | Identity fields collected so far. Keys: "name", "phone", "iban". |
| `verification_attempts` | `int` | ⚠️ Default to 0 | Count of failed verification/authentication attempts. |
| `verified_user` | `User \| None` | ⚠️ Default to None | User object from database (set after 2/3 match). |
| `is_authenticated` | `bool` | ⚠️ Default to False | True only after secret question answered correctly. |

**Initialization Pattern**:
```python
collected_fields = state.get("collected_fields", {"name": None, "phone": None, "iban": None})
verification_attempts = state.get("verification_attempts", 0)
verified_user = state.get("verified_user")
is_authenticated = state.get("is_authenticated", False)
```

---

## 3. Output Contract (State Fields Written)

| Field | Type | When Updated | Description |
|-------|------|--------------|-------------|
| `messages` | `list[BaseMessage]` | Always | Agent's response appended via `add_messages` |
| `collected_fields` | `dict[str, str \| None]` | When fields extracted | Merged with newly extracted fields (non-None only) |
| `verification_attempts` | `int` | On verification/auth failure | Incremented by 1 |
| `verified_user` | `User` | On successful 2/3 match | Set to matched User object from database |
| `is_authenticated` | `bool` | On correct secret answer | Set to `True` |
| `current_agent` | `str` | On authentication success | Set to `"bouncer"` |
| `conversation_ended` | `bool` | On termination | Set to `True` (max attempts or database failure) |

**Return Value Example** (successful verification):
```python
return {
    "messages": [AIMessage(content="Great! Which is the name of your dog?")],
    "collected_fields": {"name": "Lisa", "phone": "+1122334455", "iban": None},
    "verified_user": User(name="Lisa", phone="+1122334455", iban="DE89...", secret="Which is the name of your dog?", answer="Yoda")
}
```

**Return Value Example** (authentication success):
```python
return {
    "messages": [AIMessage(content="Perfect! Let me connect you with the right team.")],
    "is_authenticated": True,
    "current_agent": "bouncer"
}
```

**Return Value Example** (max attempts):
```python
return {
    "messages": [AIMessage(content="I'm sorry, but I wasn't able to verify your identity. Please contact our support team at...")],
    "conversation_ended": True
}
```

---

## 4. Integration with LangGraph

**Graph Registration**:
```python
from langgraph.graph import StateGraph
from app.graph.state import State
from app.agents.greeter import greeter_agent

# Build graph
builder = StateGraph(State)
builder.add_node("greeter", greeter_agent)  # Node name: "greeter"
builder.set_entry_point("greeter")          # First node in pipeline

# Routing logic (conditional edge)
builder.add_conditional_edges(
    "greeter",
    route_after_greeter,  # Function: State -> "bouncer" | "end"
    {
        "bouncer": "bouncer",
        "end": END
    }
)
```

**Routing Function**:
```python
def route_after_greeter(state: State) -> str:
    """Determine next node after Greeter Agent.
    
    Returns:
        "bouncer" if authenticated (hand off to Bouncer Agent)
        "end" if conversation ended (max attempts or database failure)
    """
    if state.get("conversation_ended", False):
        return "end"
    if state.get("is_authenticated", False):
        return "bouncer"
    return "end"  # Fallback (should not reach)
```

---

## 5. Dependencies

**External Services**:
- OpenAI API (gpt-4o-mini) — LLM calls via `langchain_openai.ChatOpenAI`

**Internal Modules**:
```python
from app.graph.state import State
from app.models.schemas import User
from app.models.database import find_user_by_fields
from app.guardrails.guardrails import run_guardrails
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
```

**Environment Variables**:
- `OPENAI_API_KEY` — Required for LLM operations

---

## 6. Error Handling Contract

**No Exceptions Raised**: All errors handled internally

**Error Scenarios**:
1. **Guardrail Rejection (Input)**: Return safe response, may set `conversation_ended=True`
2. **Database Lookup Failure**: Retry once, then return error message and set `conversation_ended=True`
3. **Max Attempts (3)**: Return final message and set `conversation_ended=True`
4. **LLM API Failure**: Should propagate (not caught) — handled by LangGraph retry mechanism

---

## 7. Testing Contract

**Unit Test Requirements**:
- Test field extraction with mocked LLM
- Test 2/3 verification logic with mocked database
- Test secret answer comparison (correct/incorrect)
- Test max attempts enforcement
- Test database failure + retry logic
- Test guardrail integration (input/output)

**Mock Targets**:
```python
from unittest.mock import patch

with patch('app.agents.greeter.ChatOpenAI') as mock_llm:
    # Mock LLM responses...

with patch('app.agents.greeter.find_user_by_fields') as mock_db:
    # Mock database lookups...

with patch('app.agents.greeter.run_guardrails') as mock_guardrails:
    # Mock guardrail checks...
```

---

## 8. Performance SLA

**Response Time**:
- Target: <2s per turn (including LLM and database calls)
- Max: 5s (with database retry)

**LLM Token Usage**:
- Estimated: ~500 tokens/turn (system prompt + user message + extraction + response)

---

## 9. Security Contract

**PII Protection**:
- ✅ `verified_user.secret` — OK to expose after verification
- ⚠️ `verified_user.answer` — NEVER expose or log
- ⚠️ Database connection errors — Log without exposing internal details to user

**Guardrails**:
- Input: Reject off-topic, toxic, or unsafe messages
- Output: Sanitize any PII that might leak from LLM

---

## Summary

The Greeter Agent is a stateless, pure function that:
- Accepts `State` TypedDict
- Returns `dict` of partial state updates
- Never raises exceptions (handles errors internally)
- Integrates via LangGraph `add_node("greeter", greeter_agent)`
- Routes to Bouncer on authentication or END on termination

**Public API**: Just the `greeter_agent(state: State) -> dict` function
**No CLI, REST endpoints, or exports** — internal LangGraph node only
