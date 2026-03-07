# Research & Discovery: Specialist Agent

**Feature**: Specialist Agent — Banking Operations Fulfillment  
**Phase**: Phase 0 (Technical Research)  
**Date**: 2026-03-07

## Overview

This document captures technical research and design decisions for implementing the Specialist Agent with tool-calling capabilities, tier-based persona adaptation, and multi-turn conversation support.

## Key Technical Decisions

### Decision 1: LangChain AgentExecutor with ReAct Pattern

**Choice**: Use `create_tool_calling_agent()` + `AgentExecutor` for tool-calling loop

**Rationale**:
- LangChain's AgentExecutor implements the ReAct (Reasoning + Acting) pattern where the LLM decides which tools to call based on user requests
- Built-in support for tool result observation and multi-step reasoning
- Handles tool invocation, result processing, and response generation automatically
- Integrates cleanly with OpenAI's function-calling API (used by gpt-4o-mini)

**Implementation Pattern**:
```python
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.tools import tool

@tool
def get_account_balance(user_id: str) -> dict:
    """Retrieve account balance for authenticated user."""
    # Implementation...
    return {"balance": 1000.0, "currency": "EUR"}

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [get_account_balance, ...]  # List of tool functions
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

result = agent_executor.invoke({"messages": conversation_history})
```

**Alternatives Considered**:
- **LangGraph Tool Node**: More explicit control but requires manual tool routing—overkill for single-agent scenario
- **Raw OpenAI Function Calling**: Lower-level, requires manual implementation of ReAct loop
- **LlamaIndex Agent**: Different framework, introduces additional dependency

### Decision 2: Inline Tool Definitions with @tool Decorator

**Choice**: Define all four banking tools inline within `specialist.py` using LangChain's `@tool` decorator

**Rationale**:
- Tools are tightly coupled to the Specialist Agent—no other agent needs them
- `@tool` decorator provides automatic schema generation for LLM function calling
- Keeps related logic colocated for easier maintenance
- Simple function signature → automatic JSON schema conversion

**Implementation Pattern**:
```python
from langchain.tools import tool
from app.models.database import ACCOUNTS_DB

@tool
def get_account_balance(user_id: str) -> dict:
    """Retrieve the current balance and currency for the authenticated user's account.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'balance' (float) and 'currency' (str) keys
    """
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        return {"error": "Account not found"}
    return {"balance": account.balance, "currency": account.currency}
```

**Key Points**:
- Docstring becomes the tool description seen by the LLM—must be clear and specific
- Type hints drive schema generation (user_id: str → LLM knows to pass string)
- Return dict for structured output, not raw strings

**Alternatives Considered**:
- **Separate tools/ module**: Adds unnecessary indirection for agent-specific tools
- **BaseTool subclasses**: More verbose, no added benefit for simple functions

### Decision 3: Tier-Based System Prompt with String Templates

**Choice**: Use Python f-strings with tier-specific persona constants for dynamic system prompts

**Rationale**:
- Simple, readable, no template engine dependency required
- Easy to test and modify persona strings
- Explicit tier handling with fallback to Standard ensures robustness

**Implementation Pattern**:
```python
PERSONA_STANDARD = """You are a helpful bank support agent. Be concise and efficient."""

PERSONA_PREMIUM = """You are a dedicated account manager. Be warm and personalized."""

PERSONA_VIP = """You are a private banking advisor. Provide white-glove service with proactive suggestions."""

def build_system_prompt(state: State) -> str:
    tier = state.get("customer_tier", "standard").lower()
    persona = {
        "standard": PERSONA_STANDARD,
        "premium": PERSONA_PREMIUM,
        "vip": PERSONA_VIP,
    }.get(tier, PERSONA_STANDARD)  # Fallback to standard
    
    customer_name = state["verified_user"].name
    intent = state["customer_intent"]
    
    return f"""{persona}

Customer: {customer_name}
Intent: {intent}

IMPORTANT:
- Never expose raw tool output, user IDs, or database references
- Translate all tool results into natural, conversational language
- Maintain context across multiple turns
- Set conversation as ended when customer's issue is resolved
"""
```

**Alternatives Considered**:
- **Jinja2 templates**: Overkill for simple string interpolation
- **Single prompt with conditional logic**: Less readable, harder to test individual personas

### Decision 4: Extended Account Model for Banking Data

**Choice**: Extend `Account` Pydantic model with balance, currency, transactions list, and card_blocked flag

**Rationale**:
- Centralizes all account-related data in one model
- Pydantic provides automatic validation and serialization
- In-memory mock database can store rich account objects
- Supports all four tool operations (balance, transactions, transfers, card blocking)

**Extended Schema**:
```python
from pydantic import BaseModel
from datetime import datetime

class Transaction(BaseModel):
    date: str  # ISO 8601 format
    description: str
    amount: float  # Negative for debits, positive for credits

class Account(BaseModel):
    user_id: str  # Links to User.id
    iban: str
    premium: bool  # Existing field (determines tier)
    balance: float
    currency: str
    transactions: list[Transaction]
    card_blocked: bool
```

**Mock Data Pattern**:
```python
ACCOUNTS_DB = {
    "user_001": Account(
        user_id="user_001",
        iban="DE89370400440532013000",
        premium=True,
        balance=5420.50,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-05", description="Salary", amount=3000.0),
            Transaction(date="2026-03-04", description="Grocery Store", amount=-45.20),
            # ...
        ],
        card_blocked=False,
    ),
    # ...
}
```

### Decision 5: IBAN Validation Strategy

**Choice**: Basic format check only (15-34 characters, alphanumeric, starts with 2 letters)

**Rationale** (from spec clarification):
- Mock banking system—no real transfers executed
- Full checksum validation adds complexity without value for the challenge
- Basic validation provides realistic UX without external validation services

**Implementation**:
```python
import re

def validate_iban_format(iban: str) -> bool:
    """Validate IBAN using basic format rules."""
    pattern = r'^[A-Z]{2}[A-Z0-9]{13,32}$'
    return bool(re.match(pattern, iban.strip().upper()))
```

### Decision 6: Tool Failure Handling with Retry

**Choice**: Single retry attempt, then escalate to human advisor (from spec clarification)

**Rationale**:
- Handles transient errors (most common failure mode)
- Avoids frustrating customers with multiple retries
- Maintains conversation flow with clear escalation path

**Implementation Pattern**:
```python
def call_tool_with_retry(tool_func, *args, **kwargs):
    try:
        return tool_func(*args, **kwargs)
    except Exception as e:
        logging.warning(f"Tool {tool_func.__name__} failed, retrying: {e}")
        try:
            return tool_func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Tool {tool_func.__name__} failed after retry: {e}")
            # Return error indicator—agent will escalate
            return {"error": "system_error", "message": "Service temporarily unavailable"}
```

### Decision 7: Conversation Ending Detection

**Choice**: Detect ending at turn 10 with automatic termination (from spec clarification)

**Rationale**:
- 10 turns (5 customer messages, 5 agent responses) covers 95% of typical banking interactions
- Automatic ending prevents resource drain from circular conversations
- Polite explanation + callback offer maintains service quality

**Implementation Pattern**:
```python
def specialist_agent(state: State) -> dict:
    # ... (tool calling logic)
    
    turn_count = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
    
    if turn_count >= 5:  # 5 customer messages = 10 total turns
        closing_message = (
            f"Thank you for using DEUS Bank, {state['verified_user'].name}. "
            f"We've reached the session limit. If you need further assistance, "
            f"our team is available via phone or you can start a new chat session. "
            f"Have a great day!"
        )
        return {
            "messages": [AIMessage(content=closing_message)],
            "conversation_ended": True,
        }
    
    # ... (continue conversation)
```

### Decision 8: Transaction History Limits

**Choice**: Default 5 transactions, allow 1-20 on request (from spec clarification)

**Rationale**:
- 5 transactions handle most "recent activity" requests
- 20-transaction ceiling prevents overwhelming conversation UI
- LLM can extract specific limit from user request ("last 10 transactions")

**Implementation**:
```python
@tool
def get_transaction_history(user_id: str, limit: int = 5) -> list:
    """Retrieve recent transactions for the authenticated user.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        limit: Number of recent transactions to retrieve (1-20, default 5)
        
    Returns:
        List of transaction dictionaries with date, description, and amount
    """
    limit = max(1, min(20, limit))  # Clamp to [1, 20]
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        return []
    return [t.dict() for t in account.transactions[-limit:]]
```

## Technology Stack Validation

| Component | Technology | Status |
|-----------|------------|--------|
| Agent Framework | LangGraph | ✅ Existing (Greeter/Bouncer) |
| Tool Calling | LangChain AgentExecutor | ✅ Available |
| LLM | OpenAI gpt-4o-mini | ✅ Existing |
| Data Validation | Pydantic v2 | ✅ Existing |
| Testing | pytest | ✅ Existing |
| Guardrails | Custom `run_guardrails()` | ✅ Existing |

## Integration Points

1. **LangGraph Pipeline**: Add `specialist` node, route from `bouncer` when `specialist_needed=True`
2. **State Management**: Read `verified_user`, `customer_tier`, `customer_intent`, `messages` | Write `messages`, `conversation_ended`
3. **Database**: Access `ACCOUNTS_DB` (new) for all tool operations
4. **Guardrails**: Call `run_guardrails()` on both user input and agent output on every turn

## Performance Considerations

- **Tool Execution Time**: <1s for balance/card operations (in-memory lookup), <3s for transfers (includes validation + DB write)
- **LLM Latency**: ~1-2s for gpt-4o-mini completion with tool schema
- **Total Response Time**: <5s end-to-end for tool-based requests (within spec requirement)

## Testing Strategy

1. **Tool Unit Tests**: Test each tool in isolation with mock ACCOUNTS_DB
2. **Tier Persona Tests**: Verify different prompts for Standard/Premium/VIP
3. **Transfer Validation Tests**: Insufficient funds, invalid IBAN, successful transfer
4. **Conversation Flow Tests**: Mock AgentExecutor to verify multi-turn context maintenance
5. **Guardrails Integration Tests**: Verify guardrails called on every turn

## Blockers & Risks

**None identified**. All dependencies available, patterns established by Greeter and Bouncer agents.

## Next Steps

Proceed to Phase 1: Design the extended Account model, define tool interfaces, and create implementation quickstart guide.
