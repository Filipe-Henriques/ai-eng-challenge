# Spec: LangGraph State — DEUS Bank AI Support System

**Feature Branch**: `002-graph-state`  
**Created**: March 7, 2026  
**Status**: Draft  

## 1. Description

This spec defines the LangGraph `State` object for the DEUS Bank AI Support System. The `State` is the single shared data structure that flows through every node in the graph. It is the backbone of the entire pipeline — every agent reads from it and writes to it. It lives in `app/graph/state.py`.

## 2. State Definition

The `State` class MUST be implemented as a `TypedDict` using LangGraph's `Annotated` fields where applicable.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `messages` | `Annotated[list[BaseMessage], add_messages]` | `[]` | The full conversation history. Uses LangGraph's `add_messages` reducer to append new messages rather than overwrite. |
| `session_id` | `str` | `""` | The unique identifier for the current conversation session. |
| `current_agent` | `str` | `"greeter"` | The name of the agent currently handling the conversation. Used for routing and response metadata. |
| `verified_user` | `User \| None` | `None` | The `User` object from the mock database once the customer has been successfully identified (2/3 fields matched). `None` until verification passes. |
| `is_authenticated` | `bool` | `False` | Set to `True` only after the customer has correctly answered their secret question. |
| `customer_tier` | `str \| None` | `None` | The customer's classification: `"premium"`, `"regular"`, or `"non_client"`. Set by the Bouncer Agent. |
| `verification_attempts` | `int` | `0` | Tracks the number of failed identity verification attempts. Used to limit retries and prevent brute-force. |
| `collected_fields` | `dict[str, str]` | `{}` | A dictionary of the identity fields collected so far from the customer (e.g., `{"name": "Lisa", "phone": "+1122334455"}`). Keys are field names (`name`, `phone`, `iban`); values are customer-provided strings. Populated incrementally by the Greeter Agent. |
| `specialist_needed` | `bool` | `False` | Set to `True` by the Bouncer Agent if the customer's request requires routing to the Specialist Agent. |
| `conversation_ended` | `bool` | `False` | Set to `True` when the conversation has reached a terminal state (resolved, rejected, or max attempts exceeded). Used as the graph's termination condition. |

## 3. State Transitions

The following table describes how each agent is expected to modify the state:

| Agent | Fields Written |
| :--- | :--- |
| **Greeter** | `messages`, `collected_fields`, `verified_user`, `is_authenticated`, `verification_attempts`, `current_agent` |
| **Bouncer** | `messages`, `customer_tier`, `specialist_needed`, `current_agent` |
| **Specialist** | `messages`, `conversation_ended`, `current_agent` |
| **Guardrails** | `messages`, `conversation_ended` |

## 4. Routing Logic (Summary)

The conditional edges of the LangGraph pipeline will use the following state fields to determine the next node:

- After **Greeter**: if `is_authenticated == True` → route to **Bouncer**; else → stay at **Greeter**.
- After **Bouncer**: if `specialist_needed == True` → route to **Specialist**; else → route to **END**.
- After **Specialist**: route to **END**.
- If `conversation_ended == True` at any point → route to **END**.
- If `verification_attempts >= 3` → route to **END** (too many failed attempts).

## 5. Clarifications

- The `messages` field uses LangGraph's built-in `add_messages` reducer, which means new messages are **appended** to the list rather than replacing it. This is what enables conversation history.
- **SECURITY**: The `verified_user` field holds the full `User` object from the mock database. Agents MUST be careful never to expose the `answer` field of this object in any response message. This field contains the customer's secret question answer and must remain confidential.
- The `collected_fields` dictionary is used by the Greeter Agent to incrementally collect identity information across multiple turns, before attempting the 2/3 verification check.
- All fields with a default value MUST be initialised with that default when the graph is first invoked.
