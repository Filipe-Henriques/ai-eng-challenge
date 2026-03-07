# Spec: Greeter Agent — DEUS Bank AI Support System

## 1. Description

This spec defines the behaviour of the **Greeter Agent**, the first node in the LangGraph pipeline. It is the friendly face of DEUS Bank. Its sole responsibilities are to welcome the customer, incrementally collect their identifying information, verify their identity using the 2-out-of-3 rule, and authenticate them via their secret question. It lives in `app/agents/greeter.py`.

The agent requires access to a User database where each User record contains: `name` (str), `phone` (str), `iban` (str), `secret` (str for the secret question), and `answer` (str for the expected secret answer).

## 2. Responsibilities

The Greeter Agent is responsible for:
1. Welcoming the customer on the first turn of the conversation.
2. Asking for identifying information (`name`, `phone`, `iban`) across one or more turns.
3. Attempting identity verification once enough fields have been collected.
4. Asking the secret question once identity is verified.
5. Confirming authentication once the secret answer is correct.
6. Handling failed verification attempts gracefully, up to a maximum of 3 attempts.

The Greeter Agent is **NOT** responsible for:
- Classifying the customer's tier (that is the Bouncer's job).
- Routing to a specialist (that is the Bouncer's job).
- Any actions after `is_authenticated` is set to `True`.

## 3. Conversation Flow

START
│
▼
[Turn 1]: # "Welcome the customer. Ask for their name, phone, and IBAN."
│
▼
[Turn N]: # "Collect fields incrementally. Attempt 2/3 verification when >= 2 fields are collected."
│
├── [Verification FAILS] → Increment verification_attempts.
│       ├── attempts < 3 → Ask the customer to try again.
│       └── attempts >= 3 → Set conversation_ended = True. Politely end the conversation.
│
├── [Database Lookup FAILS] → Retry once immediately.
│       ├── Retry succeeds → Continue with verification result.
│       └── Retry fails → Set conversation_ended = True. Respond: "I'm having trouble accessing your information right now. Please try again in a moment."
│
└── [Verification PASSES] → Set verified_user. Ask the secret question.
│
▼
[Customer answers secret question]
├── [Answer CORRECT] → Set is_authenticated = True. Hand off to Bouncer.
└── [Answer WRONG] → Increment verification_attempts. Ask again (max 3 total attempts).


## 4. State Interactions

The `collected_fields` state field is a dictionary structure: `{"name": str | None, "phone": str | None, "iban": str | None}`, initialized with all keys set to `None`. Extracted values are merged in by updating only the non-None fields.

| Action | State Field Modified |
| :--- | :--- |
| Customer provides identifying fields | `collected_fields` (merge non-None extracted fields) |
| 2/3 verification passes (at least 2 fields match exactly one user; name is case-insensitive, phone/iban exact) | `verified_user` (set to matched `User` object) |
| Secret question answered correctly | `is_authenticated` (set to `True`), `current_agent` (set to `"bouncer"`) |
| Verification or secret answer fails | `verification_attempts` (increment by 1) |
| Database lookup fails after retry | `conversation_ended` (set to `True`) |
| Max attempts reached | `conversation_ended` (set to `True`) |

## 5. LLM Behaviour

The Greeter Agent uses an LLM to:
- Generate natural, friendly, and professional responses.
- Extract identifying fields (`name`, `phone`, `iban`) from the customer's free-text messages using structured output (Pydantic model).
- Determine if the customer's secret answer matches the expected answer (case-insensitive comparison is sufficient; no LLM needed for this step).

The agent's system prompt MUST instruct the LLM to:
- Always be polite, professional, and empathetic.
- Never reveal that it is checking a database or performing a lookup.
- Never confirm or deny which specific fields matched during verification.
- Never expose the `answer` field of the `User` object.

## 6. Field Extraction

The agent MUST use LangChain's structured output to extract identifying fields from the customer's message. The extraction model is:

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | `str \| None` | Extracted customer name, or `None` if not mentioned |
| `phone` | `str \| None` | Extracted phone number, or `None` if not mentioned |
| `iban` | `str \| None` | Extracted IBAN, or `None` if not mentioned |

Extracted fields MUST be merged into `collected_fields` in the state, not replace it.

## 7. Clarifications

### Session 2026-03-07

- Q: The spec mentions a "2-out-of-3 rule" but doesn't specify the exact matching behavior. → A: At least 2 fields must exactly match one user record. Multiple or zero user matches = failure.
- Q: The spec mentions merging extracted fields into `collected_fields` but doesn't define its structure. → A: Dict with optional values: `{"name": str | None, "phone": str | None, "iban": str | None}`
- Q: When verifying identity, should field matching be case-sensitive or case-insensitive? → A: Case-insensitive for name only; exact match required for phone and IBAN
- Q: What should happen if the database lookup fails due to a technical error (e.g., connection timeout, database unavailable)? → A: Retry once immediately; if both fail, end conversation with technical difficulty message
- Q: The agent verifies against a User object but doesn't specify what fields it requires. → A: User model requires: name, phone, iban, question, answer (all strings)

### Original Requirements

- The agent should attempt verification as soon as `collected_fields` contains at least 2 non-None values.
- Identity verification requires at least 2 of the 3 fields (name, phone, iban) to exactly match the corresponding fields of exactly one user record in the database. If zero users match or multiple users match, verification fails.
- Field matching rules: name is case-insensitive (e.g., "john doe" matches "John Doe"), while phone and IBAN require exact character-by-character matches including case and formatting.
- The secret answer comparison MUST be case-insensitive (e.g., `"yoda"` matches `"Yoda"`).
- The agent MUST NOT reveal the secret question to the customer before identity verification passes.
- On the first turn, if the customer's message already contains identifying fields, the agent MUST extract and process them immediately rather than asking for them again.
- The maximum number of total attempts (verification + secret question failures combined) is 3. After 3 failures, the conversation ends.
