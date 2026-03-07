# Quickstart: Greeter Agent Implementation Guide

**Feature**: 004-greeter-agent  
**Date**: 2026-03-07  
**Audience**: Developers implementing or maintaining the Greeter Agent

---

## 1. Prerequisites

**Environment Setup**:
```bash
# Ensure Python 3.11+ installed
python --version

# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY="sk-..."
```

**Required Knowledge**:
- LangChain basics (Messages, ChatOpenAI, structured output)
- LangGraph state management (StateGraph, conditional edges)
- Pydantic models
- pytest for testing

---

## 2. Implementation Checklist

### Step 1: Define the ExtractedInfo Model

**File**: `app/agents/greeter.py`

```python
from pydantic import BaseModel, Field

class ExtractedInfo(BaseModel):
    """Structured extraction of identity fields from user message."""
    name: str | None = Field(default=None, description="Customer's full name")
    phone: str | None = Field(default=None, description="Phone number with country code")
    iban: str | None = Field(default=None, description="IBAN")
```

**Test**:
```python
# Quick validation
info = ExtractedInfo(name="Lisa", phone=None, iban=None)
assert info.name == "Lisa"
assert info.phone is None
```

---

### Step 2: Create the Agent Function

**File**: `app/agents/greeter.py`

```python
from app.graph.state import State
from app.models.database import find_user_by_fields
from app.guardrails.guardrails import run_guardrails
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

def greeter_agent(state: State) -> dict:
    """Greeter Agent implementation."""
    
    # 1. Get latest user message
    user_message = state["messages"][-1].content
    
    # 2. Input guardrail check
    input_check = run_guardrails(user_message)
    if not input_check["is_safe"]:
        return {
            "messages": [AIMessage(content=input_check["safe_response"])],
            "conversation_ended": True
        }
    
    # 3. Initialize state fields with defaults
    collected_fields = state.get("collected_fields", {"name": None, "phone": None, "iban": None})
    verification_attempts = state.get("verification_attempts", 0)
    verified_user = state.get("verified_user")
    is_authenticated = state.get("is_authenticated", False)
    
    # 4. Check termination conditions
    if verification_attempts >= 3:
        return {
            "messages": [AIMessage(content="I'm sorry, I wasn't able to verify your identity. Please contact support.")],
            "conversation_ended": True
        }
    
    # 5. Welcome message on first turn
    if len(state["messages"]) == 1:
        return {
            "messages": [AIMessage(content="Welcome to DEUS Bank! To get started, could you please provide your name, phone number, and IBAN?")]
        }
    
    # TODO: Add more logic (extraction, verification, authentication)
    
    return {"messages": [AIMessage(content="Processing...")]}
```

**Incremental Testing**:
```bash
# Test welcome message
pytest tests/test_greeter.py::test_welcome_message -v
```

---

### Step 3: Implement Field Extraction

Add to `greeter_agent()`:

```python
    # Extract fields from user message
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    extractor = llm.with_structured_output(ExtractedInfo)
    
    system_prompt = """You are a helpful assistant extracting identity information.
Extract name, phone number, and IBAN from the user's message.
If a field is not mentioned, return None for that field."""
    
    extracted = extractor.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ])
    
    # Merge non-None fields into collected_fields
    for key in ["name", "phone", "iban"]:
        value = getattr(extracted, key)
        if value is not None:
            collected_fields[key] = value
```

**Test**:
```bash
pytest tests/test_greeter.py::test_field_extraction -v
```

---

### Step 4: Implement Verification Logic

Add after field extraction:

```python
    # If user not yet verified, attempt verification
    if verified_user is None:
        # Count non-None fields
        non_none_count = sum(1 for v in collected_fields.values() if v is not None)
        
        if non_none_count < 2:
            # Not enough info yet
            return {
                "messages": [AIMessage(content="Thank you. I still need at least 2 pieces of information. Could you provide your name, phone, or IBAN?")],
                "collected_fields": collected_fields
            }
        
        # Attempt database lookup with retry
        try:
            user = find_user_with_retry(collected_fields)
        except DatabaseUnavailableError:
            return {
                "messages": [AIMessage(content="I'm having trouble accessing your information right now. Please try again in a moment.")],
                "conversation_ended": True
            }
        
        if user is None:
            # Verification failed
            return {
                "messages": [AIMessage(content="I wasn't able to verify your identity with that information. Please check and try again.")],
                "collected_fields": collected_fields,
                "verification_attempts": verification_attempts + 1
            }
        
        # Verification passed - ask secret question
        return {
            "messages": [AIMessage(content=f"Thank you! For security, please answer this question: {user.secret}")],
            "collected_fields": collected_fields,
            "verified_user": user
        }
```

**Helper Function** (add to same file):
```python
class DatabaseUnavailableError(Exception):
    """Raised when database is unavailable after retry."""
    pass

def find_user_with_retry(fields: dict):
    """Attempt database lookup with one retry."""
    import logging
    try:
        return find_user_by_fields(fields)
    except Exception as e:
        logging.warning(f"Database lookup failed, retrying: {e}")
        try:
            return find_user_by_fields(fields)
        except Exception as e:
            logging.error(f"Database lookup failed after retry: {e}")
            raise DatabaseUnavailableError("User database unavailable")
```

**Test**:
```bash
pytest tests/test_greeter.py::test_verification_success -v
pytest tests/test_greeter.py::test_verification_failure -v
pytest tests/test_greeter.py::test_database_failure -v
```

---

### Step 5: Implement Secret Question Logic

Add before verification logic:

```python
    # If user is verified but not authenticated, check secret answer
    if verified_user is not None and not is_authenticated:
        user_answer = user_message.strip()
        expected_answer = verified_user.answer
        
        if user_answer.lower() == expected_answer.lower():
            # Authentication success
            return {
                "messages": [AIMessage(content="Perfect! Let me connect you with the right team.")],
                "is_authenticated": True,
                "current_agent": "bouncer"
            }
        else:
            # Wrong answer
            return {
                "messages": [AIMessage(content="That's not quite right. Please try again.")],
                "verification_attempts": verification_attempts + 1
            }
```

**Test**:
```bash
pytest tests/test_greeter.py::test_authentication_success -v
pytest tests/test_greeter.py::test_authentication_failure -v
```

---

### Step 6: Add Output Guardrails

Wrap final response:

```python
    # Before returning any agent response, apply output guardrails
    output_check = run_guardrails(proposed_response)
    final_response = output_check["sanitised_response"]
    
    return {"messages": [AIMessage(content=final_response)], ...}
```

**Test**:
```bash
pytest tests/test_greeter.py::test_output_guardrails -v
```

---

## 3. Integration with LangGraph

**File**: `app/graph/pipeline.py`

```python
from langgraph.graph import StateGraph, END
from app.graph.state import State
from app.agents.greeter import greeter_agent

def build_graph():
    """Build the LangGraph pipeline."""
    builder = StateGraph(State)
    
    # Add Greeter node
    builder.add_node("greeter", greeter_agent)
    builder.set_entry_point("greeter")
    
    # Add routing
    def route_after_greeter(state: State) -> str:
        if state.get("conversation_ended", False):
            return "end"
        if state.get("is_authenticated", False):
            return "bouncer"
        return "greeter"  # Stay in greeter (multi-turn)
    
    builder.add_conditional_edges("greeter", route_after_greeter, {
        "greeter": "greeter",
        "bouncer": "bouncer",
        "end": END
    })
    
    return builder.compile()

graph = build_graph()
```

**Test Integration**:
```python
# Test full conversation flow
def test_full_greeter_flow():
    state = {
        "messages": [HumanMessage(content="Hello")],
        "session_id": "test-123"
    }
    
    result = graph.invoke(state)
    
    # Should welcome user
    assert "Welcome" in result["messages"][-1].content
```

---

## 4. Running Tests

**All Greeter Tests**:
```bash
pytest tests/test_greeter.py -v
```

**Specific Test**:
```bash
pytest tests/test_greeter.py::test_verification_success -v
```

**With Coverage**:
```bash
pytest tests/test_greeter.py --cov=app.agents.greeter --cov-report=term-missing
```

**Test Structure** (create in `tests/test_greeter.py`):
```python
from unittest.mock import patch, MagicMock
from app.agents.greeter import greeter_agent, ExtractedInfo
from app.graph.state import State
from langchain_core.messages import HumanMessage, AIMessage

def test_welcome_message():
    """Test that first turn produces welcome message."""
    state = {"messages": [HumanMessage(content="Hello")]}
    result = greeter_agent(state)
    assert "Welcome" in result["messages"][0].content

def test_field_extraction():
    """Test field extraction and merging."""
    with patch('app.agents.greeter.ChatOpenAI') as mock_llm:
        # Mock LLM to return extracted info
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ExtractedInfo(name="Lisa", phone="+1122334455", iban=None)
        mock_llm.return_value.with_structured_output.return_value = mock_chain
        
        # Mock guardrails to always pass
        with patch('app.agents.greeter.run_guardrails') as mock_guardrails:
            mock_guardrails.return_value = {"is_safe": True, "sanitised_response": "OK"}
            
            state = {
                "messages": [HumanMessage(content="System"), HumanMessage(content="I'm Lisa, +1122334455")],
                "collected_fields": {"name": None, "phone": None, "iban": None}
            }
            result = greeter_agent(state)
            
            assert result["collected_fields"]["name"] == "Lisa"
            assert result["collected_fields"]["phone"] == "+1122334455"

# Add more tests following this pattern...
```

---

## 5. Debugging Tips

**Enable Verbose Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect State at Each Step**:
```python
print(f"Messages: {state['messages']}")
print(f"Collected: {state.get('collected_fields', {})}")
print(f"Attempts: {state.get('verification_attempts', 0)}")
```

**Test with Real LLM** (for manual testing):
```python
# In a Jupyter notebook or Python REPL
from app.agents.greeter import greeter_agent
from langchain_core.messages import HumanMessage

state = {"messages": [HumanMessage(content="My name is Lisa and my phone is +1122334455")]}
result = greeter_agent(state)
print(result)
```

---

## 6. Common Issues

**Issue**: `KeyError: 'collected_fields'`  
**Fix**: Always use `.get()` with defaults for optional state fields

**Issue**: Agent loops indefinitely  
**Fix**: Ensure routing function returns correct edge names

**Issue**: LLM doesn't extract fields correctly  
**Fix**: Improve system prompt with examples, lower temperature to 0

**Issue**: Tests fail with "No module named 'app'"  
**Fix**: Run pytest from repository root: `pytest tests/test_greeter.py`

---

## 7. Next Steps

After implementing Greeter Agent:

1. **Run All Tests**: `pytest tests/ -v`
2. **Test Manually**: Use FastAPI endpoint to test full conversation
3. **Code Review**: Check against spec.md and constitution.md
4. **Document**: Add docstrings to all functions
5. **Move to Bouncer**: Implement next agent in pipeline

---

## Resources

- [Spec](../spec.md) — Full feature specification
- [Data Model](../data-model.md) — Pydantic models and state schema
- [Contract](../contracts/agent-interface.md) — Public API and integration guide
- [LangChain Structured Output](https://python.langchain.com/docs/how_to/structured_output/)
- [LangGraph State](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)
