# Research: Bouncer Agent

**Phase**: 0 (Research & Decision Making)  
**Date**: 2026-03-07  
**Feature**: [spec.md](spec.md)

## Overview

This document captures research findings and technology decisions for the Bouncer Agent implementation. The Bouncer is responsible for tier determination and intent classification in the DEUS Bank support pipeline.

---

## 1. Intent Classification with LangChain Structured Output

### Decision
Use LangChain's `with_structured_output()` method with Pydantic models for intent classification.

### Rationale
- **Type Safety**: Pydantic v2 ensures runtime validation of LLM outputs
- **Consistency**: Already used in the project (see `app/models/schemas.py`)
- **Confidence Scoring**: Allows explicit confidence field for threshold-based fallback
- **OpenAI Native**: Works seamlessly with `gpt-4o-mini` function calling

### Implementation Pattern
```python
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

class ClassifiedIntent(BaseModel):
    intent: str = Field(description="One of: account_balance, transaction_history, fund_transfer, lost_card, general_inquiry")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")

llm = ChatOpenAI(model="gpt-4o-mini")
structured_llm = llm.with_structured_output(ClassifiedIntent)
result = structured_llm.invoke(messages)
```

### Alternatives Considered
- **LangChain Output Parsers**: Rejected – less robust than function calling
- **Manual JSON parsing**: Rejected – error-prone, no validation
- **Instructor Library**: Rejected – adds unnecessary dependency

### Reference
- LangChain Structured Output: https://python.langchain.com/docs/how_to/structured_output
- OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling

---

## 2. Confidence Threshold Selection

### Decision
Use confidence threshold of **0.5** with fallback to `general_inquiry`.

### Rationale
- **Conservative**: Prevents misrouting on uncertain intents
- **User Experience**: `general_inquiry` is the safest catch-all for Specialist agents
- **Empirical**: 0.5 is a standard threshold in binary classification tasks
- **Adjustable**: Can be tuned based on production metrics

### Threshold Behavior
| Confidence | Action |
|------------|--------|
| >= 0.5 | Use classified intent |
| < 0.5 | Override to `general_inquiry` |

### Alternatives Considered
- **0.7 threshold**: Rejected – too strict, would trigger too many fallbacks
- **0.3 threshold**: Rejected – too permissive, risks misrouting
- **Dynamic threshold**: Rejected – premature optimization for MVP

---

## 3. Tier-to-Specialist Routing

### Decision
Use a static dictionary mapping for tier-to-agent routing.

### Rationale
- **Simplicity**: Three tiers → three specialists, no complex logic needed
- **Clarity**: Explicit mapping is immediately readable
- **Fast**: O(1) lookup with dict
- **Testable**: Easy to mock and verify

### Mapping
```python
TIER_ROUTING = {
    "standard": "specialist_standard",
    "premium": "specialist_premium",
    "vip": "specialist_vip",
}
```

### Defensive Programming
- If `tier` not in mapping → default to `specialist_standard`
- Prevents runtime errors if data model changes

### Alternatives Considered
- **Dynamic routing function**: Rejected – overkill for 3 tiers
- **Enum-based routing**: Rejected – dict is more pythonic here
- **Graph-based routing in LangGraph**: Rejected – keep routing logic in node

---

## 4. Guardrail Integration

### Decision
Apply guardrails at **input** (customer message) and **output** (handoff message).

### Rationale
- **Constitution Principle II**: Safety First applies to all agent nodes
- **Input Safety**: Prevent prompt injection or toxic input from reaching LLM
- **Output Safety**: Ensure handoff message is professional and safe
- **Consistency**: Matches pattern from Greeter Agent (004)

### Integration Points
```python
# Input guardrail
input_check = run_guardrails(state['messages'][-1])
if not input_check['is_safe']:
    return {"messages": [AIMessage(content=input_check['safe_response'])]}

# Output guardrail (after generating handoff message)
output_check = run_guardrails(handoff_message)
final_message = output_check['sanitised_response']
```

### Reference
- See `app/guardrails/guardrails.py`
- See `specs/003-guardrails/spec.md`

---

## 5. Single-Turn Constraint

### Decision
Bouncer MUST NOT engage in conversation. It executes once and hands off immediately.

### Rationale
- **Separation of Concerns**: Bouncer is a router, not a conversational agent
- **Predictability**: Single-turn execution is easier to test and debug
- **Performance**: Reduces latency by minimizing LLM calls
- **Constitution Principle I**: Each agent has a single, well-defined responsibility

### Implementation Strategy
- No loops in `bouncer_agent()` function
- No recursive calls
- Return state update immediately after classification + routing
- LangGraph handles the handoff to next node

### Error Handling
- If guardrail blocks input → return immediately with safe response (do NOT route)
- If intent classification fails → default to `general_inquiry` (still route)
- If tier lookup fails → default to `specialist_standard` (still route)

---

## 6. State Updates

### Decision
Bouncer updates three state fields:
1. `customer_tier` (str)
2. `customer_intent` (str)
3. `current_agent` (str)

### Rationale
- **Explicit State Transitions**: Makes graph behavior auditable
- **Downstream Context**: Specialist agents need tier and intent for personalization
- **Routing Signal**: `current_agent` enables conditional edge logic in LangGraph

### State Dependencies
- **Reads**: `verified_user`, `messages`, `is_authenticated`
- **Writes**: `customer_tier`, `customer_intent`, `current_agent`, `messages` (handoff)

### Reference
- See `app/graph/state.py` for GraphState definition
- See `specs/002-graph-state/spec.md`

---

## 7. LLM Configuration

### Decision
Use `gpt-4o-mini` with:
- **Temperature**: 0.3 (low variance for consistent classification)
- **Max tokens**: 150 (short handoff message + structured output)
- **Structured output**: Yes (for intent classification)
- **Free-form**: Yes (for handoff message generation)

### Rationale
- **Cost**: gpt-4o-mini is 60% cheaper than gpt-4o
- **Speed**: Faster inference for single-turn routing
- **Quality**: Sufficient for intent classification task
- **Consistency**: Low temperature ensures reproducible routing decisions

### Alternatives Considered
- **gpt-4o**: Rejected – overkill for this task
- **gpt-3.5-turbo**: Rejected – OpenAI recommends gpt-4o-mini over 3.5
- **Local model**: Rejected – requires infrastructure, increases complexity

---

## 8. Testing Strategy

### Decision
Unit test with mocked LLM and guardrails.

### Key Test Cases
1. **Tier Routing**: Verify each tier maps to correct specialist
2. **Intent Classification**: Verify each intent sets correct state field
3. **Confidence Fallback**: Verify low confidence triggers `general_inquiry`
4. **Guardrail Block**: Verify early return when input is unsafe
5. **Handoff Message**: Verify message appended to conversation history
6. **Single-Turn Execution**: Verify no loops or recursive calls

### Mocking Strategy
```python
@patch('app.agents.bouncer.ChatOpenAI')
@patch('app.agents.bouncer.run_guardrails')
def test_bouncer_routes_premium_customer(mock_guardrails, mock_llm):
    mock_llm.return_value.with_structured_output.return_value.invoke.return_value = \
        ClassifiedIntent(intent="account_balance", confidence=0.85)
    mock_guardrails.return_value = {"is_safe": True, "sanitised_response": "Connecting you..."}
    
    result = bouncer_agent(state)
    assert result['current_agent'] == 'specialist_premium'
```

### Reference
- See `tests/test_greeter.py` for similar agent test patterns

---

## Summary: All NEEDS CLARIFICATION Resolved

✅ All technical decisions documented  
✅ LangChain structured output pattern selected  
✅ Confidence threshold set to 0.5  
✅ Tier routing via static dictionary  
✅ Guardrails integrated at input/output  
✅ Single-turn constraint enforced  
✅ State fields defined  
✅ LLM configuration specified  
✅ Testing strategy established  

**Status**: Ready for Phase 1 (Design)