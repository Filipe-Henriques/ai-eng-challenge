# Quickstart: Bouncer Agent Implementation

**Feature**: [spec.md](spec.md) | **Data Model**: [data-model.md](data-model.md) | **Contract**: [contracts/agent-interface.md](contracts/agent-interface.md)

## Overview

This guide will walk you through implementing the Bouncer Agent in **30 minutes**. The Bouncer is a single-turn routing agent that classifies customer intent and directs them to the appropriate specialist.

---

## Prerequisites

✅ Greeter Agent is complete (`app/agents/greeter.py`)  
✅ GraphState is defined (`app/graph/state.py`)  
✅ Guardrails are implemented (`app/guardrails/guardrails.py`)  
✅ Python environment set up with dependencies installed

---

## Step 1: Extend GraphState (5 minutes)

**File**: `app/graph/state.py`

Add three new fields to the `GraphState` TypedDict:

```python
from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage
from app.models.database import User

class GraphState(TypedDict):
    # Existing fields...
    is_authenticated: bool
    verified_user: Optional[User]
    messages: List[BaseMessage]
    conversation_ended: bool
    verification_attempts: int
    
    # NEW: Bouncer Agent fields
    customer_tier: Optional[str]        # "standard" | "premium" | "vip"
    customer_intent: Optional[str]      # One of 5 intent strings
    current_agent: str                  # Current active agent name
```

**Test**: Run `pytest tests/test_graph_state.py` (if exists) to verify no regressions.

---

## Step 2: Create ClassifiedIntent Model (5 minutes)

**File**: `app/agents/bouncer.py` (create new file)

Define the Pydantic model for LLM structured output:

```python
"""Bouncer Agent: Intent classification and specialist routing."""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from app.graph.state import GraphState
from app.guardrails.guardrails import run_guardrails

# Intent classification model
class ClassifiedIntent(BaseModel):
    """Structured output for customer intent classification."""
    intent: Literal[
        "account_balance",
        "transaction_history",
        "fund_transfer",
        "lost_card",
        "general_inquiry"
    ] = Field(description="Customer's intent from conversation history")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classification confidence score"
    )

# Tier-to-specialist routing table
TIER_ROUTING = {
    "standard": "specialist_standard",
    "premium": "specialist_premium",
    "vip": "specialist_vip",
}
```

**Test**: Import the model in a Python REPL to verify no syntax errors.

---

## Step 3: Implement Intent Classification (10 minutes)

**File**: `app/agents/bouncer.py` (continue)

Add the main agent function with intent classification:

```python
def bouncer_agent(state: GraphState) -> dict:
    """
    Bouncer Agent: Classify intent and route to specialist.
    
    Single-turn agent that:
    1. Checks input guardrails
    2. Classifies customer intent from history
    3. Determines tier and routes to correct specialist
    4. Generates handoff message
    
    Args:
        state: Current graph state (expects authenticated user)
        
    Returns:
        State updates with customer_tier, customer_intent, current_agent
    """
    # Step 1: Input guardrail check
    latest_message = state['messages'][-1].content
    input_check = run_guardrails(latest_message)
    
    if not input_check['is_safe']:
        # Block unsafe input, do NOT route
        return {
            "messages": [AIMessage(content=input_check['safe_response'])]
        }
    
    # Step 2: Classify intent from conversation history
    conversation_history = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Agent'}: {msg.content}"
        for msg in state['messages']
    ])
    
    system_prompt = """You are a banking support intent classifier.
    
Analyze the conversation history and classify the customer's primary intent.

Supported intents:
- account_balance: Customer wants to check their balance
- transaction_history: Customer wants to review transactions
- fund_transfer: Customer wants to transfer money
- lost_card: Customer reports a lost or stolen card
- general_inquiry: Any other question or unclear intent

Be conservative with your confidence score. If the intent is not clearly one of the above, choose general_inquiry."""

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    structured_llm = llm.with_structured_output(ClassifiedIntent)
    
    try:
        classification = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Conversation:\n{conversation_history}\n\nWhat is the customer's intent?"}
        ])
        
        # Apply confidence threshold
        if classification.confidence < 0.5:
            intent = "general_inquiry"
        else:
            intent = classification.intent
            
    except Exception as e:
        # Fallback on any LLM error
        print(f"[Bouncer] Intent classification failed: {e}")
        intent = "general_inquiry"
    
    # Step 3: Determine tier and routing
    tier = state['verified_user'].tier
    target_agent = TIER_ROUTING.get(tier, "specialist_standard")  # Defensive default
    
    # Step 4: Generate handoff message
    handoff_prompt = f"""Generate a brief, professional handoff message (one sentence) 
for a banking customer being routed to a specialist. The customer's intent is: {intent}.

Do NOT reveal the customer's tier. Be warm and professional."""

    try:
        handoff_response = llm.invoke([
            {"role": "system", "content": handoff_prompt}
        ])
        handoff_message = handoff_response.content
    except Exception as e:
        print(f"[Bouncer] Handoff generation failed: {e}")
        handoff_message = "Connecting you to a specialist..."
    
    # Step 5: Output guardrail check
    output_check = run_guardrails(handoff_message)
    final_message = output_check['sanitised_response']
    
    # Step 6: Return state updates
    return {
        "customer_tier": tier,
        "customer_intent": intent,
        "current_agent": target_agent,
        "messages": [AIMessage(content=final_message)]
    }
```

**Note**: Add `from langchain_core.messages import HumanMessage` to imports.

**Test**: Run `pytest tests/test_bouncer.py -k test_bouncer_classifies_intent` (write test in Step 5).

---

## Step 4: Integrate into LangGraph Pipeline (5 minutes)

**File**: `app/graph/pipeline.py`

Add the Bouncer node and routing edges:

```python
from app.agents.greeter import greeter_agent
from app.agents.bouncer import bouncer_agent  # NEW import

# Build graph
graph = StateGraph(GraphState)

# Add nodes
graph.add_node("greeter", greeter_agent)
graph.add_node("bouncer", bouncer_agent)  # NEW node

# Add conditional edges
def route_from_greeter(state: GraphState) -> str:
    """Route from Greeter to Bouncer or END."""
    if state.get("is_authenticated"):
        return "bouncer"
    elif state.get("conversation_ended"):
        return END
    else:
        return "greeter"

def route_from_bouncer(state: GraphState) -> str:
    """Route from Bouncer to appropriate Specialist."""
    return state["current_agent"]  # Returns specialist name

graph.add_conditional_edges("greeter", route_from_greeter)
graph.add_conditional_edges("bouncer", route_from_bouncer)

# Set entry point
graph.set_entry_point("greeter")
```

**Test**: Run the graph with a mock authenticated state to verify Bouncer is reached.

---

## Step 5: Write Unit Tests (5 minutes)

**File**: `tests/test_bouncer.py` (create new file)

Add core test cases:

```python
"""Unit tests for Bouncer Agent."""

import pytest
from unittest.mock import patch, MagicMock
from app.agents.bouncer import bouncer_agent, ClassifiedIntent, TIER_ROUTING
from app.models.database import User
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def mock_state():
    """Create a mock authenticated state."""
    user = User(
        name="John Doe",
        phone="555-1234",
        iban="DE89370400440532013000",
        tier="premium",
        secret="What is your pet's name?",
        answer="Fluffy"
    )
    return {
        "is_authenticated": True,
        "verified_user": user,
        "messages": [
            AIMessage(content="Welcome! How can I help?"),
            HumanMessage(content="I need to check my account balance"),
        ],
        "conversation_ended": False,
        "verification_attempts": 0,
        "customer_tier": None,
        "customer_intent": None,
        "current_agent": "greeter"
    }

@patch('app.agents.bouncer.ChatOpenAI')
@patch('app.agents.bouncer.run_guardrails')
def test_bouncer_routes_premium_customer(mock_guardrails, mock_llm, mock_state):
    """Test that premium customer routes to specialist_premium."""
    # Mock LLM responses
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value.invoke.return_value = \
        ClassifiedIntent(intent="account_balance", confidence=0.85)
    mock_llm_instance.invoke.return_value.content = "Connecting you to your advisor..."
    mock_llm.return_value = mock_llm_instance
    
    # Mock guardrails
    mock_guardrails.side_effect = [
        {"is_safe": True},  # Input check
        {"sanitised_response": "Connecting you to your advisor..."}  # Output check
    ]
    
    # Run agent
    result = bouncer_agent(mock_state)
    
    # Assertions
    assert result['customer_tier'] == 'premium'
    assert result['customer_intent'] == 'account_balance'
    assert result['current_agent'] == 'specialist_premium'
    assert len(result['messages']) == 1
    assert isinstance(result['messages'][0], AIMessage)

@patch('app.agents.bouncer.ChatOpenAI')
@patch('app.agents.bouncer.run_guardrails')
def test_bouncer_fallback_low_confidence(mock_guardrails, mock_llm, mock_state):
    """Test that low confidence triggers general_inquiry fallback."""
    # Mock LLM with low confidence
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value.invoke.return_value = \
        ClassifiedIntent(intent="fund_transfer", confidence=0.3)  # Low confidence
    mock_llm_instance.invoke.return_value.content = "Let me help you..."
    mock_llm.return_value = mock_llm_instance
    
    mock_guardrails.side_effect = [
        {"is_safe": True},
        {"sanitised_response": "Let me help you..."}
    ]
    
    result = bouncer_agent(mock_state)
    
    # Should override to general_inquiry
    assert result['customer_intent'] == 'general_inquiry'

@patch('app.agents.bouncer.run_guardrails')
def test_bouncer_blocks_unsafe_input(mock_guardrails, mock_state):
    """Test that unsafe input blocks routing."""
    mock_guardrails.return_value = {
        "is_safe": False,
        "safe_response": "I'm here to help with banking questions."
    }
    
    result = bouncer_agent(mock_state)
    
    # Should return safe response without routing
    assert 'current_agent' not in result
    assert 'customer_tier' not in result
    assert result['messages'][0].content == "I'm here to help with banking questions."
```

**Run**: `pytest tests/test_bouncer.py -v`

---

## Step 6: Verify Integration (5 minutes)

**Manual Test**:

1. Start the FastAPI server: `uvicorn app.main:app --reload`
2. Send a test conversation to the `/chat` endpoint:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi, I'm John Doe",
    "session_id": "test-123"
  }'

# Continue authentication...

# After auth, last message should show Bouncer's handoff
```

3. Check logs for `[Bouncer]` entries
4. Verify `"current_agent": "specialist_premium"` in response state (if endpoint returns state)

---

## Troubleshooting

### Issue: "ClassifiedIntent not found"
- **Fix**: Ensure Pydantic model is imported in `bouncer.py`

### Issue: "tier not in TIER_ROUTING"
- **Fix**: Check that `verified_user.tier` is one of: `"standard"`, `"premium"`, `"vip"`

### Issue: LLM always returns low confidence
- **Fix**: Review system prompt; ensure conversation history is formatted correctly

### Issue: Guardrails block all outputs
- **Fix**: Check guardrail configuration; handoff messages should be professional and pass

---

## Next Steps

After implementing the Bouncer:

1. ✅ Run full test suite: `pytest tests/ -v`
2. ✅ Implement Specialist Agents (see `specs/006-specialist-agent/`)
3. ✅ Add LangGraph visualization (optional): `graph.get_graph().print_ascii()`
4. ✅ Configure logging for debugging

---

## Key Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `app/graph/state.py` | Modified | Added 3 new state fields |
| `app/agents/bouncer.py` | Created | Bouncer agent implementation |
| `app/graph/pipeline.py` | Modified | Added Bouncer node + routing edges |
| `tests/test_bouncer.py` | Created | Unit tests for Bouncer |

---

## Estimated Time Breakdown

- Step 1: Extend GraphState → 5 min
- Step 2: Create ClassifiedIntent → 5 min
- Step 3: Implement agent logic → 10 min
- Step 4: Integrate into pipeline → 5 min
- Step 5: Write tests → 5 min
- Step 6: Manual verification → 5 min

**Total**: ~30 minutes for experienced developers

---

## Success Criteria

✅ Bouncer node exists in LangGraph pipeline  
✅ All unit tests pass (`pytest tests/test_bouncer.py`)  
✅ Manual chat flow reaches Bouncer after authentication  
✅ `customer_tier` and `customer_intent` are set correctly  
✅ Routing to correct specialist based on tier  
✅ Handoff message is professional and passes guardrails

---

**Questions?** See [contracts/agent-interface.md](contracts/agent-interface.md) for detailed interface spec.