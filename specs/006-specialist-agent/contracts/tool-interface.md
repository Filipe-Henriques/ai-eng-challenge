# Tool Interface Contract: Specialist Agent Banking Tools

**Feature**: Specialist Agent — Banking Operations Fulfillment  
**Phase**: Phase 1 (Public Interface Definition)  
**Date**: 2026-03-07

## Overview

This document defines the public interface contract for the four banking tools exposed by the Specialist Agent. These tools are decorated with LangChain's `@tool` decorator and are callable by the LLM via the AgentExecutor's function-calling mechanism.

## Tool 1: get_account_balance

**Purpose**: Retrieve the current account balance and currency for an authenticated user

**Signature**:
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
```

**Input Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | str | Yes | Unique customer identifier from `verified_user.id` in state |

**Return Value**:

Success response:
```json
{
  "balance": 5420.50,
  "currency": "EUR"
}
```

Error response:
```json
{
  "error": "Account not found"
}
```

**Behavior**:
1. Look up account in `ACCOUNTS_DB` by `user_id`
2. If found: return current balance and currency
3. If not found: return error dictionary

**Execution Time**: <500ms (in-memory lookup)

**Side Effects**: None (read-only operation)

---

## Tool 2: get_transaction_history

**Purpose**: Retrieve recent transactions for an authenticated user's account

**Signature**:
```python
@tool
def get_transaction_history(user_id: str, limit: int = 5) -> list:
    """Retrieve recent transactions for the authenticated user's account.
    
    The LLM can request a specific number of transactions by changing the limit parameter.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        limit: Number of recent transactions to retrieve (1-20, default 5)
        
    Returns:
        List of transaction dictionaries, each with 'date' (str), 'description' (str),
        and 'amount' (float) keys. Returns empty list if account not found.
    """
```

**Input Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | str | Yes | — | Unique customer identifier |
| `limit` | int | No | 5 | Number of transactions to retrieve (clamped to 1-20) |

**Return Value**:

Success response (list of transactions):
```json
[
  {"date": "2026-03-05", "description": "Utility Bill", "amount": -84.30},
  {"date": "2026-03-04", "description": "Online Transfer", "amount": 150.0},
  {"date": "2026-03-03", "description": "Grocery Store", "amount": -45.20}
]
```

Empty response (account not found or no transactions):
```json
[]
```

**Behavior**:
1. Clamp `limit` to range [1, 20]: `limit = max(1, min(20, limit))`
2. Look up account in `ACCOUNTS_DB` by `user_id`
3. If found: return last `limit` transactions from `account.transactions`
4. If not found: return empty list
5. Transactions ordered newest last (so slice `[-limit:]` gets most recent)

**Execution Time**: <500ms (in-memory lookup and slicing)

**Side Effects**: None (read-only operation)

---

## Tool 3: transfer_funds

**Purpose**: Execute a fund transfer from the authenticated user's account to a recipient IBAN

**Signature**:
```python
@tool
def transfer_funds(user_id: str, recipient_iban: str, amount: float, description: str) -> dict:
    """Initiate a fund transfer from the authenticated user's account.
    
    The transfer will only succeed if:
    1. The recipient IBAN is valid (basic format check)
    2. The account has sufficient balance
    
    Args:
        user_id: The unique identifier of the authenticated customer
        recipient_iban: The IBAN of the recipient account
        amount: The transfer amount (must be positive)
        description: Description for the transaction record
        
    Returns:
        Dictionary with 'success' (bool), 'transaction_id' (str or None), and
        optional 'reason' (str) for failures
    """
```

**Input Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | str | Yes | Unique customer identifier |
| `recipient_iban` | str | Yes | Recipient's IBAN (validated) |
| `amount` | float | Yes | Transfer amount (must be > 0) |
| `description` | str | Yes | Transaction description |

**Return Value**:

Success response:
```json
{
  "success": true,
  "transaction_id": "TXN-A3F8B91C"
}
```

Failure responses:
```json
{
  "success": false,
  "transaction_id": null,
  "reason": "Insufficient funds"
}
```

```json
{
  "success": false,
  "transaction_id": null,
  "reason": "Invalid IBAN format"
}
```

```json
{
  "success": false,
  "transaction_id": null,
  "reason": "Account not found"
}
```

**Behavior**:
1. Look up account in `ACCOUNTS_DB` by `user_id`
2. If account not found: return failure with reason "Account not found"
3. Validate `recipient_iban` format using basic pattern (15-34 chars, starts with 2 letters)
4. If IBAN invalid: return failure with reason "Invalid IBAN format"
5. Check if `account.balance >= amount`
6. If insufficient funds: return failure with reason "Insufficient funds"
7. If valid:
   - Deduct `amount` from `account.balance`
   - Append transaction record: `Transaction(date=today, description=description, amount=-amount)`
   - Generate mock transaction ID: `f"TXN-{uuid4().hex[:8].upper()}"`
   - Return success with transaction_id

**Execution Time**: <3s (includes validation, balance check, and update)

**Side Effects**: 
- Modifies `account.balance` (deduction)
- Appends to `account.transactions` (new debit entry)

**IBAN Validation Pattern**: `^[A-Z]{2}[A-Z0-9]{13,32}$`

---

## Tool 4: report_lost_card

**Purpose**: Flag a user's card as lost or stolen and generate a case reference

**Signature**:
```python
@tool
def report_lost_card(user_id: str) -> dict:
    """Report the authenticated user's card as lost or stolen.
    
    This immediately blocks the card and provides a case reference for tracking.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'success' (bool), 'case_id' (str or None), and
        optional 'reason' (str) for failures
    """
```

**Input Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | str | Yes | Unique customer identifier |

**Return Value**:

Success response:
```json
{
  "success": true,
  "case_id": "CASE-7D92E4A1"
}
```

Failure response:
```json
{
  "success": false,
  "case_id": null,
  "reason": "Account not found"
}
```

**Behavior**:
1. Look up account in `ACCOUNTS_DB` by `user_id`
2. If not found: return failure with reason "Account not found"
3. Set `account.card_blocked = True`
4. Generate mock case ID: `f"CASE-{uuid4().hex[:8].upper()}"`
5. Return success with case_id

**Execution Time**: <2s (in-memory update)

**Side Effects**: 
- Modifies `account.card_blocked` (set to `True`)

**Idempotency**: Calling this tool multiple times on the same account is safe—card remains blocked, new case ID generated each time

---

## Common Patterns

### Error Handling

All tools follow a consistent error handling pattern:

```python
try:
    # Tool logic
    return success_response
except Exception as e:
    logger.error(f"Tool failed: {e}")
    # Retry once per FR-019
    try:
        # Tool logic (retry)
        return success_response
    except Exception as e:
        logger.error(f"Tool failed after retry: {e}")
        return {"error": "system_error", "message": "Service temporarily unavailable"}
```

### Logging

All tools log key events:
- Tool invocation with parameters (excluding sensitive data)
- Success/failure outcomes
- Errors and retries

Example:
```python
logger.info(f"get_account_balance called for user_id={user_id}")
logger.info(f"Balance retrieved: {balance} {currency}")
logger.error(f"Account not found for user_id={user_id}")
```

### User ID Source

**CRITICAL**: The `user_id` parameter MUST always come from `state["verified_user"].id`, never from user input. The Specialist Agent extracts this from state before calling tools.

Bad pattern (never do this):
```python
# ❌ DON'T extract user_id from conversation
user_id = extract_from_message(user_message)  # WRONG
```

Good pattern:
```python
# ✅ Always read from state
user_id = state["verified_user"].id  # CORRECT
tools_with_context = [
    lambda: get_account_balance(user_id),
    # ...
]
```

## LLM Integration

### Tool Schemas

LangChain automatically generates JSON schemas from the tool function signatures and docstrings:

```json
{
  "name": "get_account_balance",
  "description": "Retrieve the current balance and currency for the authenticated user's account.",
  "parameters": {
    "type": "object",
    "properties": {
      "user_id": {
        "type": "string",
        "description": "The unique identifier of the authenticated customer"
      }
    },
    "required": ["user_id"]
  }
}
```

The LLM sees these schemas and decides which tool to call based on the user's request.

### Tool Result Handling

After tool execution, the AgentExecutor:
1. Receives the tool's return value (dict or list)
2. Formats it as a ToolMessage in the conversation history
3. Passes it back to the LLM for natural language generation

The LLM then generates a conversational response like:
- ✅ "Your current balance is 5,420.50 EUR."
- ❌ NOT: `{"balance": 5420.50, "currency": "EUR"}` (raw output)

## Testing Contract

### Unit Test Structure

```python
def test_get_account_balance_success():
    result = get_account_balance("user_001")
    assert "balance" in result
    assert "currency" in result
    assert isinstance(result["balance"], float)

def test_get_account_balance_not_found():
    result = get_account_balance("user_999")
    assert "error" in result
    assert result["error"] == "Account not found"
```

### Integration Test Structure

```python
def test_specialist_agent_balance_inquiry(mock_agent_executor, mock_guardrails):
    state = create_test_state(
        verified_user=User(id="user_001", name="Lisa", ...),
        customer_tier="vip",
        customer_intent="account_balance",
        messages=[HumanMessage(content="What's my balance?")],
    )
    
    result = specialist_agent(state)
    
    assert "5,420.50" in result["messages"][-1].content  # LLM formatted response
    assert "EUR" in result["messages"][-1].content
    assert mock_guardrails.run_guardrails.call_count == 2  # Input + output
```

## Versioning & Compatibility

**Version**: 1.0 (Initial implementation)

**Breaking Changes**: None (new tools, no existing interfaces modified)

**Deprecation Policy**: N/A (first version)

## Security Considerations

1. **No PII in Logs**: Never log full IBANs, balances, or transaction details at INFO level (use DEBUG)
2. **User ID Validation**: Always verify `user_id` exists in ACCOUNTS_DB before operations
3. **Balance Checks**: Always validate sufficient funds before transfers
4. **IBAN Validation**: Basic format check prevents obviously invalid inputs
5. **Guardrails**: All tool results pass through guardrails before presentation to customer

## Performance SLAs

| Tool | Target Latency | Max Retries |
|------|----------------|-------------|
| get_account_balance | <500ms | 1 |
| get_transaction_history | <500ms | 1 |
| transfer_funds | <3s | 1 |
| report_lost_card | <2s | 1 |

**Total conversation turn time** (including LLM): <5s (95th percentile)
