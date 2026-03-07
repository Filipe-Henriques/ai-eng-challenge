# Research: Greeter Agent Implementation

**Feature**: 004-greeter-agent  
**Date**: 2026-03-07  
**Purpose**: Document technical decisions, patterns, and best practices for implementing the Greeter Agent

---

## 1. LangChain Structured Output for Field Extraction

**Decision**: Use LangChain's `with_structured_output()` method with Pydantic models

**Rationale**:
- Type-safe extraction of user information (name, phone, IBAN)
- Built-in validation via Pydantic
- Cleaner than manual JSON parsing or regex

**Pattern**:
```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

class ExtractedInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    iban: str | None = None

llm = ChatOpenAI(model="gpt-4o-mini")
extractor = llm.with_structured_output(ExtractedInfo)
result = extractor.invoke("My name is Lisa and my phone is +1122334455")
# result.name == "Lisa", result.phone == "+1122334455", result.iban == None
```

**Alternatives Considered**:
- Manual prompt engineering with JSON output → Rejected: fragile, requires parsing
- LangChain JsonOutputParser → Rejected: less type-safe than Pydantic integration

**References**:
- LangChain docs: https://python.langchain.com/docs/how_to/structured_output/
- Pydantic v2 docs: https://docs.pydantic.dev/latest/

---

## 2. LangGraph Node Implementation Pattern

**Decision**: Agent function signature: `def agent_name(state: State) -> dict`

**Rationale**:
- LangGraph expects nodes to accept state and return partial state updates
- Return dict is merged into state (not replacement)
- Clean separation: node logic doesn't need full state mutation

**Pattern**:
```python
from app.graph.state import State

def greeter_agent(state: State) -> dict:
    """Greeter Agent node for LangGraph pipeline."""
    # Read from state
    messages = state["messages"]
    collected_fields = state.get("collected_fields", {"name": None, "phone": None, "iban": None})
    
    # Agent logic here...
    
    # Return partial updates (merged into state)
    return {
        "messages": [AIMessage(content=response)],
        "collected_fields": updated_fields,
        "verification_attempts": state.get("verification_attempts", 0) + 1
    }
```

**Key Practices**:
- Always use `.get()` with defaults for optional state fields
- Return only changed fields (don't copy entire state)
- Use `add_messages` annotation for message appending (defined in State)

**References**:
- LangGraph State Management: https://langchain-ai.github.io/langgraph/concepts/low_level/#state

---

## 3. Database Failure Retry Strategy

**Decision**: Single immediate retry on database lookup failure, then graceful termination

**Rationale**:
- Handles transient network/connection errors without excessive latency
- Prevents infinite retry loops
- Clear user communication on persistent failure

**Pattern**:
```python
def find_user_with_retry(fields: dict) -> User | None:
    """Attempt database lookup with one retry."""
    try:
        return find_user_by_fields(fields)
    except Exception as e:
        # Log first failure
        logging.warning(f"Database lookup failed, retrying: {e}")
        try:
            return find_user_by_fields(fields)
        except Exception as e:
            # Log second failure
            logging.error(f"Database lookup failed after retry: {e}")
            raise DatabaseUnavailableError("Cannot access user database")
```

**Error Handling**:
- Catch `DatabaseUnavailableError` in agent
- Set `conversation_ended = True`
- Return message: "I'm having trouble accessing your information right now. Please try again in a moment."

**Alternatives Considered**:
- Exponential backoff → Rejected: adds latency, user is waiting
- No retry → Rejected: fails on transient errors
- Multiple retries → Rejected: poor UX (user waiting)

**References**:
- Resilience patterns: https://learn.microsoft.com/en-us/azure/architecture/patterns/retry

---

## 4. Case-Insensitive String Matching

**Decision**: Use `.lower()` for name comparison, exact match for phone/IBAN

**Rationale**:
- Names have natural case variations ("Lisa" vs "lisa")
- Phone and IBAN are structured identifiers requiring exact match
- Simple, predictable, no regex complexity

**Pattern**:
```python
def matches_user(fields: dict, user: User) -> int:
    """Count how many fields match (2/3 rule)."""
    matches = 0
    
    if fields.get("name") and fields["name"].lower() == user.name.lower():
        matches += 1
    if fields.get("phone") and fields["phone"] == user.phone:
        matches += 1
    if fields.get("iban") and fields["iban"] == user.iban:
        matches += 1
    
    return matches
```

**Note**: This logic is already implemented in `find_user_by_fields()` in `app/models/database.py`. Agent just calls that function.

---

## 5. Testing LLM-Based Agents

**Decision**: Mock LLM responses using `unittest.mock.patch` or `pytest-mock`

**Rationale**:
- Unit tests must be fast and deterministic
- No real API calls in CI/CD
- Test agent logic independent of LLM behavior

**Pattern**:
```python
from unittest.mock import patch, MagicMock

def test_field_extraction():
    """Test that agent extracts and merges fields correctly."""
    
    # Mock the LLM to return specific extracted info
    with patch('app.agents.greeter.ChatOpenAI') as mock_llm:
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = ExtractedInfo(
            name="Lisa",
            phone="+1122334455",
            iban=None
        )
        mock_llm.return_value.with_structured_output.return_value = mock_chain
        
        # Run agent
        state = {
            "messages": [HumanMessage(content="I'm Lisa, +1122334455")],
            "collected_fields": {"name": None, "phone": None, "iban": None}
        }
        result = greeter_agent(state)
        
        # Assert fields merged correctly
        assert result["collected_fields"]["name"] == "Lisa"
        assert result["collected_fields"]["phone"] == "+1122334455"
        assert result["collected_fields"]["iban"] is None
```

**Test Categories**:
1. **Field extraction**: Mock LLM, verify state updates
2. **Verification logic**: Mock database, test 2/3 matching
3. **Secret question**: Mock verified_user, test answer comparison
4. **Guardrails**: Mock guardrail responses, verify rejection flow
5. **Max attempts**: Test `conversation_ended` flag after 3 failures

**References**:
- pytest-mock: https://pytest-mock.readthedocs.io/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html

---

## 6. Guardrails Integration Pattern

**Decision**: Apply guardrails to both input and output within agent function

**Rationale**:
- Input guardrails prevent processing of harmful/off-topic messages
- Output guardrails sanitize agent responses before user sees them
- Centralized in agent (not duplicated across multiple nodes)

**Pattern**:
```python
from app.guardrails.guardrails import run_guardrails

def greeter_agent(state: State) -> dict:
    user_message = state["messages"][-1].content
    
    # Input guardrail
    input_check = run_guardrails(user_message)
    if not input_check["is_safe"]:
        return {
            "messages": [AIMessage(content=input_check["safe_response"])],
            "conversation_ended": True
        }
    
    # Agent logic generates proposed_response...
    
    # Output guardrail
    output_check = run_guardrails(proposed_response)
    final_response = output_check["sanitised_response"]
    
    return {"messages": [AIMessage(content=final_response)]}
```

**Note**: According to Constitution Principle II, guardrails are mandatory at every agent node.

---

## Summary

All technical unknowns resolved. Ready to proceed to Phase 1 (data-model.md, contracts/, quickstart.md).

**Key Technologies**:
- LangChain `with_structured_output()` for field extraction
- LangGraph node pattern: `(State) -> dict`
- Retry-once pattern for database errors
- Mock-based testing for LLM agents
- Dual guardrails (input + output)

**No Blockers**: All dependencies available, patterns established, implementation path clear.
