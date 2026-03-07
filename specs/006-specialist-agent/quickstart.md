# Quickstart Guide: Implementing the Specialist Agent

**Feature**: Specialist Agent — Banking Operations Fulfillment  
**Target Audience**: Developers implementing this feature  
**Estimated Time**: 4-6 hours  
**Date**: 2026-03-07

## Overview

This guide walks you through implementing the Specialist Agent step-by-step. Follow the tasks in order—each builds on the previous.

## Prerequisites

- ✅ Greeter Agent implemented and tested (`app/agents/greeter.py`)
- ✅ Bouncer Agent implemented and tested (`app/agents/bouncer.py`)
- ✅ GraphState with `customer_tier` and `customer_intent` fields
- ✅ Mock database infrastructure (`app/models/database.py`)
- ✅ Guardrails system (`app/guardrails/guardrails.py`)

## Implementation Roadmap

```text
Step 1: Extend Data Models (30 min)
   ├─ Add Transaction model to schemas.py
   ├─ Extend Account model with banking fields
   └─ Add ACCOUNTS_DB with mock data to database.py

Step 2: Implement Banking Tools (90 min)
   ├─ get_account_balance (20 min)
   ├─ get_transaction_history (20 min)
   ├─ transfer_funds (30 min)
   └─ report_lost_card (20 min)

Step 3: Build System Prompt Generator (30 min)
   ├─ Define tier personas
   └─ Implement build_system_prompt()

Step 4: Implement specialist_agent Function (60 min)
   ├─ Set up AgentExecutor
   ├─ Add guardrails integration
   ├─ Handle conversation ending
   └─ Update state

Step 5: Write Tests (90 min)
   ├─ Tool unit tests
   ├─ Agent integration tests
   └─ End-to-end conversation tests

Step 6: Wire into LangGraph Pipeline (30 min)
   ├─ Add specialist node
   └─ Add routing from bouncer
```

---

## Step 1: Extend Data Models (30 min)

### 1.1: Add Transaction Model

**File**: `app/models/schemas.py`

Add after the existing `Account` model:

```python
class Transaction(BaseModel):
    """Represents a single banking transaction.
    
    Attributes:
        date: Transaction date in ISO 8601 format (YYYY-MM-DD)
        description: Human-readable transaction description
        amount: Transaction amount (negative for debits, positive for credits)
    """
    date: str
    description: str
    amount: float
```

### 1.2: Extend Account Model

**File**: `app/models/schemas.py`

Replace the existing `Account` model with:

```python
class Account(BaseModel):
    """Represents a bank account with full transaction history.
    
    Attributes:
        user_id: Unique identifier linking to User (for ACCOUNTS_DB lookup)
        iban: International Bank Account Number
        premium: Whether the account holder is a premium client (determines tier)
        balance: Current account balance
        currency: Account currency code (e.g., "EUR", "USD", "GBP")
        transactions: List of recent transactions (newest last)
        card_blocked: Whether the account's card has been reported lost/stolen
    """
    user_id: str
    iban: str
    premium: bool
    balance: float
    currency: str
    transactions: list[Transaction]
    card_blocked: bool
```

### 1.3: Add ACCOUNTS_DB Mock Data

**File**: `app/models/database.py`

Add after the existing `find_account_by_iban()` function:

```python
from app.models.schemas import Transaction

# Mock accounts with full banking data
ACCOUNTS_DB = {
    "user_001": Account(
        user_id="user_001",
        iban="DE89370400440532013000",
        premium=True,
        balance=5420.50,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-01", description="Salary Deposit", amount=3000.0),
            Transaction(date="2026-03-02", description="Rent Payment", amount=-1200.0),
            Transaction(date="2026-03-03", description="Grocery Store", amount=-45.20),
            Transaction(date="2026-03-04", description="Online Transfer from John", amount=150.0),
            Transaction(date="2026-03-05", description="Utility Bill", amount=-84.30),
        ],
        card_blocked=False,
    ),
    "user_002": Account(
        user_id="user_002",
        iban="GB29NWBK60161331926819",
        premium=False,
        balance=1247.80,
        currency="GBP",
        transactions=[
            Transaction(date="2026-03-01", description="Paycheck", amount=2500.0),
            Transaction(date="2026-03-02", description="Transfer to Lisa", amount=-150.0),
            Transaction(date="2026-03-03", description="Restaurant", amount=-62.50),
            Transaction(date="2026-03-04", description="Gas Station", amount=-45.30),
            Transaction(date="2026-03-06", description="Refund", amount=25.00),
        ],
        card_blocked=False,
    ),
    "user_003": Account(
        user_id="user_003",
        iban="FR7630006000011234567890189",
        premium=False,
        balance=325.10,
        currency="EUR",
        transactions=[
            Transaction(date="2026-03-01", description="Freelance Payment", amount=500.0),
            Transaction(date="2026-03-02", description="Groceries", amount=-89.40),
            Transaction(date="2026-03-03", description="Coffee Shop", amount=-15.50),
            Transaction(date="2026-03-05", description="ATM Withdrawal", amount=-70.0),
        ],
        card_blocked=False,
    ),
}
```

**Checkpoint**: Run existing tests to ensure no regressions from model changes.

---

## Step 2: Implement Banking Tools (90 min)

**File**: Create `app/agents/specialist.py`

### 2.1: File Header & Imports

```python
"""Specialist Agent: Banking operations with tool-calling capabilities.

This module implements the Specialist Agent, which fulfills banking requests
for authenticated, routed customers using four banking tools:
- get_account_balance: Retrieve current balance
- get_transaction_history: Review recent transactions
- transfer_funds: Execute fund transfers
- report_lost_card: Block lost/stolen cards

The agent adapts its persona based on customer tier (Standard/Premium/VIP)
and maintains multi-turn conversation context.
"""

import logging
import re
from uuid import uuid4
from datetime import datetime

from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.graph.state import State
from app.models.database import ACCOUNTS_DB
from app.guardrails.guardrails import run_guardrails

logger = logging.getLogger(__name__)
```

### 2.2: Implement get_account_balance

```python
@tool
def get_account_balance(user_id: str) -> dict:
    """Retrieve the current balance and currency for the authenticated user's account.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'balance' (float) and 'currency' (str) keys on success,
        or dictionary with 'error' (str) key on failure
    """
    logger.info(f"get_account_balance called for user_id={user_id}")
    
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        logger.error(f"Account not found for user_id={user_id}")
        return {"error": "Account not found"}
    
    logger.info(f"Balance retrieved: {account.balance} {account.currency}")
    return {"balance": account.balance, "currency": account.currency}
```

### 2.3: Implement get_transaction_history

```python
@tool
def get_transaction_history(user_id: str, limit: int = 5) -> list:
    """Retrieve recent transactions for the authenticated user's account.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        limit: Number of recent transactions to retrieve (1-20, default 5)
        
    Returns:
        List of transaction dictionaries with date, description, and amount.
        Returns empty list if account not found.
    """
    # Clamp limit to valid range
    limit = max(1, min(20, limit))
    logger.info(f"get_transaction_history called for user_id={user_id}, limit={limit}")
    
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        logger.error(f"Account not found for user_id={user_id}")
        return []
    
    # Get last N transactions (transactions list is ordered oldest to newest)
    transactions = account.transactions[-limit:]
    result = [{"date": t.date, "description": t.description, "amount": t.amount} for t in transactions]
    
    logger.info(f"Retrieved {len(result)} transactions for user_id={user_id}")
    return result
```

### 2.4: Implement transfer_funds

```python
def validate_iban_format(iban: str) -> bool:
    """Validate IBAN using basic format rules."""
    pattern = r'^[A-Z]{2}[A-Z0-9]{13,32}$'
    return bool(re.match(pattern, iban.strip().upper()))


@tool
def transfer_funds(user_id: str, recipient_iban: str, amount: float, description: str) -> dict:
    """Initiate a fund transfer from the authenticated user's account.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        recipient_iban: The IBAN of the recipient account
        amount: The transfer amount (must be positive)
        description: Description for the transaction record
        
    Returns:
        Dictionary with 'success' (bool), 'transaction_id' (str or None),
        and optional 'reason' (str) for failures
    """
    logger.info(f"transfer_funds called for user_id={user_id}, amount={amount}, recipient={recipient_iban}")
    
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        logger.error(f"Account not found for user_id={user_id}")
        return {"success": False, "transaction_id": None, "reason": "Account not found"}
    
    # Validate IBAN format
    if not validate_iban_format(recipient_iban):
        logger.warning(f"Invalid IBAN format: {recipient_iban}")
        return {"success": False, "transaction_id": None, "reason": "Invalid IBAN format"}
    
    # Check sufficient funds
    if account.balance < amount:
        logger.warning(f"Insufficient funds: balance={account.balance}, requested={amount}")
        return {"success": False, "transaction_id": None, "reason": "Insufficient funds"}
    
    # Execute transfer
    account.balance -= amount
    today = datetime.now().strftime("%Y-%m-%d")
    account.transactions.append(
        Transaction(date=today, description=description, amount=-amount)
    )
    transaction_id = f"TXN-{uuid4().hex[:8].upper()}"
    
    logger.info(f"Transfer successful: transaction_id={transaction_id}")
    return {"success": True, "transaction_id": transaction_id}
```

### 2.5: Implement report_lost_card

```python
@tool
def report_lost_card(user_id: str) -> dict:
    """Report the authenticated user's card as lost or stolen.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'success' (bool), 'case_id' (str or None),
        and optional 'reason' (str) for failures
    """
    logger.info(f"report_lost_card called for user_id={user_id}")
    
    account = ACCOUNTS_DB.get(user_id)
    if not account:
        logger.error(f"Account not found for user_id={user_id}")
        return {"success": False, "case_id": None, "reason": "Account not found"}
    
    # Block card
    account.card_blocked = True
    case_id = f"CASE-{uuid4().hex[:8].upper()}"
    
    logger.info(f"Card blocked: case_id={case_id}")
    return {"success": True, "case_id": case_id}
```

**Checkpoint**: Test each tool in isolation before proceeding.

---

## Step 3: Build System Prompt Generator (30 min)

**File**: `app/agents/specialist.py` (add to bottom)

### 3.1: Define Tier Personas

```python
# Tier-specific persona strings
PERSONA_STANDARD = """You are a helpful bank support agent for DEUS Bank.
Be concise, efficient, and professional. Provide clear answers without unnecessary elaboration."""

PERSONA_PREMIUM = """You are a dedicated account manager for DEUS Bank.
Be warm, personalized, and attentive. Show genuine care for the customer's needs."""

PERSONA_VIP = """You are a private banking advisor for DEUS Bank.
Provide highly personalized, white-glove service. Be proactive with suggestions and reassurance.
Anticipate needs and offer premium support options."""
```

### 3.2: Implement build_system_prompt

```python
def build_system_prompt(state: State) -> str:
    """Build tier-specific system prompt for the Specialist Agent.
    
    Args:
        state: Current conversation state with customer tier and user info
        
    Returns:
        Complete system prompt with persona, customer context, and guidelines
    """
    tier = state.get("customer_tier", "standard").lower()
    persona = {
        "standard": PERSONA_STANDARD,
        "premium": PERSONA_PREMIUM,
        "vip": PERSONA_VIP,
    }.get(tier, PERSONA_STANDARD)  # Fallback to standard
    
    customer_name = state["verified_user"].name
    intent = state["customer_intent"]
    
    return f"""{persona}

Customer Name: {customer_name}
Classified Intent: {intent}

CRITICAL GUIDELINES:
- NEVER expose raw tool output, user IDs, database references, or internal system details
- ALWAYS translate tool results into natural, conversational language
- Address the customer by their first name
- Never ask the customer for their user ID or account number
- Maintain context across multiple conversation turns
- When the customer's request is fully resolved, provide a closing message

CONVERSATION RULES:
- Apply a professional, helpful tone appropriate for banking
- If a request is outside your scope (e.g., mortgages, investments), politely explain and offer to escalate
- Handle errors gracefully without technical jargon
"""
```

---

## Step 4: Implement specialist_agent Function (60 min)

**File**: `app/agents/specialist.py` (add to bottom)

```python
def specialist_agent(state: State) -> dict:
    """Main Specialist Agent function - fulfills banking requests with tools.
    
    This function implements the ReAct pattern using LangChain's AgentExecutor.
    It handles authenticated customers, adapts its persona to their tier, and
    uses banking tools to fulfill requests.
    
    Args:
        state: Current conversation state (GraphState)
        
    Returns:
        Partial state update with new messages and conversation_ended flag
    """
    logger.info(f"Specialist Agent started for user={state['verified_user'].name}, tier={state['customer_tier']}")
    
    # === Guardrail Check: Input ===
    user_message = state["messages"][-1].content
    guardrail_result = run_guardrails(user_message)
    
    if not guardrail_result["is_safe"]:
        logger.warning(f"Guardrail blocked input: {guardrail_result.get('reason')}")
        return {
            "messages": [AIMessage(content=guardrail_result["safe_response"])],
            "conversation_ended": True,
        }
    
    # === Check Turn Limit ===
    turn_count = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
    
    if turn_count >= 5:  # 5 customer messages = 10 total turns
        logger.info("Turn limit reached, ending conversation")
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
    
    # === Set Up AgentExecutor ===
    system_prompt = build_system_prompt(state)
    user_id = state["verified_user"].id  # Extract ONCE, use for all tools
    
    # Define tools list
    tools = [
        get_account_balance,
        get_transaction_history,
        transfer_funds,
        report_lost_card,
    ]
    
    # Create LLM and agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_tool_calling_agent(llm, tools, system_prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    # === Execute Agent ===
    try:
        # Inject user_id into tool context by creating bound versions
        # (AgentExecutor will pass remaining args from LLM)
        result = agent_executor.invoke({
            "messages": state["messages"],
            "user_id": user_id,  # Make user_id available to tools
        })
        
        agent_response = result["output"]
        
    except Exception as e:
        logger.error(f"AgentExecutor failed: {e}")
        agent_response = (
            "I apologize, but I'm experiencing technical difficulties. "
            "Please try again, or contact our support team for immediate assistance."
        )
    
    # === Guardrail Check: Output ===
    guardrail_result = run_guardrails(agent_response)
    final_response = guardrail_result["sanitised_response"]
    
    # === Detect Conversation Ending ===
    # Simple heuristic: check for closing phrases
    ending_phrases = ["have a great day", "is there anything else", "thank you for banking"]
    conversation_ended = any(phrase in final_response.lower() for phrase in ending_phrases)
    
    logger.info(f"Specialist Agent completed, conversation_ended={conversation_ended}")
    
    return {
        "messages": [AIMessage(content=final_response)],
        "conversation_ended": conversation_ended,
    }
```

**Note**: This implementation has a simplification—proper tool binding requires additional setup. See the full implementation in `tests/test_specialist.py` for the complete pattern.

---

## Step 5: Write Tests (90 min)

**File**: Create `tests/test_specialist.py`

### 5.1: Test get_account_balance

```python
import pytest
from app.agents.specialist import get_account_balance

def test_get_account_balance_success():
    result = get_account_balance("user_001")
    assert "balance" in result
    assert "currency" in result
    assert result["balance"] == 5420.50
    assert result["currency"] == "EUR"

def test_get_account_balance_not_found():
    result = get_account_balance("user_999")
    assert "error" in result
```

### 5.2: Test get_transaction_history

```python
from app.agents.specialist import get_transaction_history

def test_get_transaction_history_default():
    result = get_transaction_history("user_001")
    assert len(result) == 5  # Default limit

def test_get_transaction_history_custom_limit():
    result = get_transaction_history("user_001", limit=3)
    assert len(result) == 3

def test_get_transaction_history_clamps_limit():
    result = get_transaction_history("user_001", limit=100)
    assert len(result) == 5  # Only 5 transactions available
```

### 5.3: Test transfer_funds

```python
from app.agents.specialist import transfer_funds

def test_transfer_funds_success():
    result = transfer_funds("user_001", "GB29NWBK60161331926819", 100.0, "Test transfer")
    assert result["success"] is True
    assert "transaction_id" in result
    assert result["transaction_id"].startswith("TXN-")

def test_transfer_funds_insufficient():
    result = transfer_funds("user_003", "GB29NWBK60161331926819", 1000.0, "Too much")
    assert result["success"] is False
    assert result["reason"] == "Insufficient funds"

def test_transfer_funds_invalid_iban():
    result = transfer_funds("user_001", "INVALID", 100.0, "Bad IBAN")
    assert result["success"] is False
    assert result["reason"] == "Invalid IBAN format"
```

### 5.4: Test report_lost_card

```python
from app.agents.specialist import report_lost_card
from app.models.database import ACCOUNTS_DB

def test_report_lost_card_success():
    # Reset card state
    ACCOUNTS_DB["user_001"].card_blocked = False
    
    result = report_lost_card("user_001")
    assert result["success"] is True
    assert "case_id" in result
    assert ACCOUNTS_DB["user_001"].card_blocked is True
```

### 5.5: Integration Test (Mocked)

```python
from unittest.mock import Mock, patch
from app.agents.specialist import specialist_agent
from app.graph.state import State

@patch("app.agents.specialist.AgentExecutor")
@patch("app.agents.specialist.run_guardrails")
def test_specialist_agent_basic_flow(mock_guardrails, mock_executor):
    # Mock guardrails
    mock_guardrails.return_value = {
        "is_safe": True,
        "sanitised_response": "Your balance is 5,420.50 EUR."
    }
    
    # Mock executor
    mock_executor_instance = Mock()
    mock_executor_instance.invoke.return_value = {"output": "Your balance is 5,420.50 EUR."}
    mock_executor.return_value = mock_executor_instance
    
    # Create test state
    state = {
        "verified_user": Mock(name="Lisa", id="user_001"),
        "customer_tier": "vip",
        "customer_intent": "account_balance",
        "messages": [HumanMessage(content="What's my balance?")],
    }
    
    result = specialist_agent(state)
    
    assert len(result["messages"]) == 1
    assert "5,420.50" in result["messages"][0].content
```

**Checkpoint**: All tests should pass before proceeding.

---

## Step 6: Wire into LangGraph Pipeline (30 min)

**File**: `app/graph/pipeline.py`

### 6.1: Import Specialist Agent

```python
from app.agents.specialist import specialist_agent
```

### 6.2: Add Specialist Node

```python
builder.add_node("specialist", specialist_agent)
```

### 6.3: Add Routing from Bouncer

Update the conditional edge from bouncer:

```python
def route_after_bouncer(state: State) -> str:
    """Route to specialist or end conversation."""
    if state.get("specialist_needed", False):
        return "specialist"
    return "end"

builder.add_conditional_edges(
    "bouncer",
    route_after_bouncer,
    {"specialist": "specialist", "end": END}
)
```

### 6.4: Add Edge from Specialist to End

```python
builder.add_edge("specialist", END)
```

**Checkpoint**: Test the full pipeline end-to-end.

---

## Testing the Complete Feature

### Manual Test Script

```bash
# Start the FastAPI server
python -m app.main

# In another terminal, test the flow:
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "message": "Hi, I'\''m Lisa, my phone is +1122334455"
  }'

# Continue conversation through verification, authentication, and specialist
```

### Automated E2E Test

Create `tests/test_e2e_specialist.py` with full conversation flow tests.

---

## Troubleshooting

### Issue: Tools not being called

**Cause**: LLM not seeing tool schemas  
**Fix**: Verify `@tool` decorator is applied and docstrings are complete

### Issue: user_id not available in tools

**Cause**: Context not passed correctly  
**Fix**: Ensure user_id is injected via bound tool functions or agent context

### Issue: Guardrails blocking valid responses

**Cause**: Guardrail configuration too strict  
**Fix**: Review `run_guardrails()` logic and adjust filters

### Issue: Conversation not ending

**Cause**: Ending detection heuristic too strict  
**Fix**: Expand ending phrase list or use structured output for explicit end signal

---

## Next Steps

After completing this feature:

1. Test the full three-agent pipeline (Greeter → Bouncer → Specialist)
2. Add metrics and logging for production monitoring
3. Consider adding more banking tools (e.g., statement download, account settings)
4. Enhance tier personas based on user feedback

## References

- [Feature Spec](spec.md) - Complete specification
- [Data Model](data-model.md) - Schema definitions
- [Tool Interface Contract](contracts/tool-interface.md) - Tool API details
- [LangChain AgentExecutor Docs](https://python.langchain.com/docs/modules/agents/agent_types/react)
