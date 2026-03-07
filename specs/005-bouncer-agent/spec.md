# Spec: Bouncer Agent — DEUS Bank AI Support System

**Feature Branch**: `005-bouncer-agent`  
**Created**: March 7, 2026  
**Status**: Draft

## 1. Description

This spec defines the behaviour of the **Bouncer Agent**, the second node in the LangGraph pipeline. It is activated only after the Greeter Agent has successfully authenticated the customer (`is_authenticated = True`). Its sole responsibilities are to determine the customer's tier, classify their intent, and route them to the correct Specialist Agent. It lives in `app/agents/bouncer.py`.

## 2. Responsibilities

The Bouncer Agent is responsible for:
1. Determining the authenticated customer's tier (`standard`, `premium`, `vip`) from the `verified_user` object.
2. Classifying the customer's intent from their conversation history.
3. Routing the customer to the appropriate specialist by setting `current_agent` in the state.
4. Generating a brief, professional handoff message to the customer.

The Bouncer Agent is **NOT** responsible for:
- Authenticating the customer (that is the Greeter's job).
- Handling any banking operations (that is the Specialist's job).
- Engaging in multi-turn conversation. The Bouncer acts in a **single turn** and immediately hands off.

## 3. Customer Tiers

The Bouncer reads the `tier` field directly from the `verified_user` object (set by the Greeter). The tier determines which Specialist Agent the customer is routed to.

| Tier | Description | Routed To |
| :--- | :--- | :--- |
| `standard` | Regular customer | `specialist_standard` |
| `premium` | High-value customer | `specialist_premium` |
| `vip` | Top-tier customer | `specialist_vip` |

## 4. Intent Classification

The Bouncer uses the LLM to classify the customer's primary intent from the conversation history. The intent is stored in `customer_intent` in the state and is passed to the Specialist Agent as context.

The supported intents are:

| Intent | Description |
| :--- | :--- |
| `account_balance` | Customer wants to check their account balance |
| `transaction_history` | Customer wants to review past transactions |
| `fund_transfer` | Customer wants to transfer money |
| `lost_card` | Customer wants to report a lost or stolen card |
| `general_inquiry` | Customer has a general question not covered above |

If the intent cannot be clearly determined from the conversation history, the Bouncer MUST default to `general_inquiry`.

## 5. Conversation Flow

```
START (is_authenticated = True)
│
▼
[Step 1]: Read verified_user.tier → Set customer_tier in state.
│
▼
[Step 2]: Classify intent from conversation history → Set customer_intent in state.
│
▼
[Step 3]: Set current_agent to the appropriate specialist based on tier.
│
▼
[Step 4]: Generate a brief handoff message (e.g., "Connecting you to your dedicated advisor...").
│
▼
END (hand off to Specialist)
```

## 6. State Interactions

| Action | State Field Modified |
| :--- | :--- |
| Tier determined from `verified_user` | `customer_tier` (set to `"standard"`, `"premium"`, or `"vip"`) |
| Intent classified from history | `customer_intent` (set to one of the supported intents) |
| Routing decision made | `current_agent` (set to `"specialist_standard"`, `"specialist_premium"`, or `"specialist_vip"`) |

**Note**: State updates return new values in a dict; LangGraph merges these updates into the shared state object. The Bouncer does not mutate state directly.

## 7. LLM Behaviour

The Bouncer Agent uses an LLM **only** for:
- Classifying the customer's intent from the conversation history (structured output).
- Generating the brief, professional handoff message.

The agent's system prompt MUST instruct the LLM to:
- Be concise and professional.
- Never ask the customer any questions.
- Never perform any banking operations.
- Classify the intent strictly from the provided list of supported intents.

## 8. Intent Extraction

The Bouncer MUST use LangChain's structured output to extract the intent. The extraction model is:

| Field | Type | Description |
| :--- | :--- | :--- |
| `intent` | `str` | One of the five supported intent strings |
| `confidence` | `float` | Confidence score between 0.0 and 1.0 |

If `confidence < 0.5`, the Bouncer MUST default to `general_inquiry` regardless of the classified intent.

## 9. Clarifications

- The Bouncer MUST only be invoked when `is_authenticated = True`. This will be enforced by the LangGraph conditional edge logic.
- The Bouncer does NOT need to verify the user again. It trusts the state set by the Greeter.
- The handoff message should be warm but brief (one sentence, maximum 150 characters). It should NOT reveal the customer's tier to them.
- The Bouncer is a single-turn agent. It does not loop back to itself.
