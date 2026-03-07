# Data Model: Bouncer Agent

**Phase**: 1 (Design)  
**Date**: 2026-03-07  
**Feature**: [spec.md](spec.md)

## Overview

This document defines the data structures used by the Bouncer Agent for intent classification, tier routing, and state management.

---

## 1. Core Entities

### 1.1 ClassifiedIntent (Pydantic Model)

**Purpose**: Structured output model for LLM intent classification

**Location**: `app/agents/bouncer.py` (agent-specific model, kept with implementation)

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `intent` | `str` | One of: `account_balance`, `transaction_history`, `fund_transfer`, `lost_card`, `general_inquiry` | The customer's classified intent from conversation history |
| `confidence` | `float` | `0.0 <= confidence <= 1.0` | Confidence score for the classification |

**Validation Rules**:
- `intent` MUST be one of the five supported values (enforced via Literal type or validator)
- `confidence` MUST be between 0.0 and 1.0 (enforced via Pydantic `Field` constraints)

**Example**:
```python
from pydantic import BaseModel, Field
from typing import Literal

class ClassifiedIntent(BaseModel):
    """Structured output from intent classification LLM."""
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
        description="Classification confidence (0.0-1.0)"
    )
```

---

## 2. State Fields (GraphState Extensions)

### 2.1 Existing Fields (Read-Only for Bouncer)

| Field | Type | Source | Usage |
|-------|------|--------|-------|
| `is_authenticated` | `bool` | Greeter Agent | Conditional edge check (must be True) |
| `verified_user` | `User` | Greeter Agent | Source of customer tier |
| `messages` | `List[BaseMessage]` | Conversation history | Input for intent classification |

### 2.2 New Fields (Written by Bouncer)

**Location**: `app/graph/state.py` — add to `GraphState` TypedDict

| Field | Type | Initial Value | Description |
|-------|------|---------------|-------------|
| `customer_tier` | `str` | `None` | Customer tier: `"standard"`, `"premium"`, or `"vip"` |
| `customer_intent` | `str` | `None` | Classified intent or `"general_inquiry"` if confidence < 0.5 |
| `current_agent` | `str` | `"greeter"` | Current active agent; set to specialist name after routing |

**State Update Example**:
```python
return {
    "customer_tier": "premium",
    "customer_intent": "account_balance",
    "current_agent": "specialist_premium",
    "messages": [AIMessage(content="Connecting you to your Premium advisor...")]
}
```

---

## 3. Static Routing Table

### 3.1 TIER_ROUTING

**Purpose**: Maps customer tier to specialist agent name

**Location**: `app/agents/bouncer.py` (module-level constant)

**Type**: `Dict[str, str]`

**Definition**:
```python
TIER_ROUTING = {
    "standard": "specialist_standard",
    "premium": "specialist_premium",
    "vip": "specialist_vip",
}
```

**Usage**:
```python
tier = state['verified_user'].tier
target_agent = TIER_ROUTING.get(tier, "specialist_standard")  # Defensive default
```

---

## 4. Intent Categories

### 4.1 Supported Intents

| Intent Value | Description | Specialist Behavior |
|--------------|-------------|---------------------|
| `account_balance` | Customer wants to check account balance | Specialist will invoke balance lookup tool |
| `transaction_history` | Customer wants to review transactions | Specialist will invoke transaction history tool |
| `fund_transfer` | Customer wants to transfer money | Specialist will invoke transfer tool |
| `lost_card` | Customer reports lost/stolen card | Specialist will invoke card blocking tool |
| `general_inquiry` | Default/catch-all for unclear or low-confidence intents | Specialist will engage in open conversation |

### 4.2 Confidence Threshold
- **Threshold**: `0.5`
- **Rule**: If `confidence < 0.5`, override `intent` to `"general_inquiry"`

---

## 5. Message Types

### 5.1 Input Messages

**Source**: `state['messages']` (LangGraph conversation history)

**Type**: `List[BaseMessage]` (LangChain message types)

**Structure**:
- Last message is `HumanMessage` (customer's latest input)
- History includes all `HumanMessage` and `AIMessage` from Greeter

**Example**:
```python
messages = [
    AIMessage(content="Welcome to DEUS Bank. May I have your name?"),
    HumanMessage(content="John Doe"),
    AIMessage(content="Thank you. Can you provide your phone number?"),
    HumanMessage(content="555-1234. I need to check my balance."),
    AIMessage(content="One moment, verifying..."),
    AIMessage(content="Authentication successful. Let me connect you.")
]
```

### 5.2 Output Message (Handoff)

**Type**: `AIMessage`

**Content**: Brief, professional handoff message (one sentence)

**Examples**:
- "Connecting you to your dedicated advisor..."
- "Routing you to our Premium support team..."
- "One moment, transferring you to a specialist..."

**Constraints**:
- MUST NOT reveal customer tier explicitly
- MUST be warm and professional
- MUST be generated by LLM (not hardcoded)
- MUST pass guardrails output check

---

## 6. Validation & Error Handling

### 6.1 Input Validation

| Check | Action on Failure |
|-------|-------------------|
| `is_authenticated == False` | Should never reach Bouncer (conditional edge prevents this) |
| `verified_user is None` | Log error; default to `specialist_standard` |
| `verified_user.tier not in TIER_ROUTING` | Default to `specialist_standard` |
| `messages` is empty | Log error; return error message to user |

### 6.2 LLM Output Validation

| Check | Action on Failure |
|-------|-------------------|
| `intent` not in supported list | Pydantic validation error → fallback to `general_inquiry` |
| `confidence < 0.5` | Override `intent` to `general_inquiry` |
| LLM call fails (timeout, API error) | Fallback to `general_inquiry` and `specialist_standard` |

### 6.3 Guardrail Checks

| Check | Action on Failure |
|-------|-------------------|
| Input message fails guardrails | Return `safe_response` immediately; do NOT route |
| Output message fails guardrails | Use `sanitised_response` instead of raw LLM output |

---

## 7. Relationships

### 7.1 Dependencies

```
Bouncer Agent
├── Reads: verified_user.tier (from Greeter)
├── Reads: messages (from GraphState)
├── Reads: is_authenticated (from Greeter)
├── Writes: customer_tier (to GraphState)
├── Writes: customer_intent (to GraphState)
├── Writes: current_agent (to GraphState)
└── Appends: handoff message (to messages)
```

### 7.2 Data Flow

```
Greeter Agent
    ↓
    verified_user.tier
    is_authenticated = True
    ↓
Bouncer Agent (this feature)
    │
    ├─→ Read tier → Set customer_tier
    ├─→ Classify intent → Set customer_intent
    ├─→ Determine specialist → Set current_agent
    └─→ Generate handoff → Append to messages
    ↓
Specialist Agent (future)
    ↓
    Reads: customer_tier, customer_intent
    Executes: Banking operations
```

---

## 8. Schema Evolution

### Current Version: 1.0

**Changes in this version**:
- Added `ClassifiedIntent` model
- Extended `GraphState` with three new fields
- Defined intent categories and routing table

### Future Considerations
- **Intent Expansion**: If new intents are added, update `ClassifiedIntent` Literal type and Specialist handling
- **Tier Expansion**: If new tiers are added (e.g., "corporate"), update `TIER_ROUTING`
- **Confidence Tuning**: Threshold may be adjusted based on production metrics

---

## Summary

✅ **ClassifiedIntent** model defined for LLM structured output  
✅ **GraphState** extensions documented (3 new fields)  
✅ **TIER_ROUTING** static mapping defined  
✅ **Intent categories** specified (5 supported intents)  
✅ **Message types** documented (input history, output handoff)  
✅ **Validation rules** and error handling defined  
✅ **Data flow** relationships mapped  

**Status**: Data model complete. Ready for contract definition.