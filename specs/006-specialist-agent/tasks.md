# Implementation Tasks: Specialist Agent

**Feature**: Specialist Agent — Banking Operations Fulfillment  
**Status**: Ready for Implementation  
**Generated**: 2026-03-07

## Overview

This document provides an actionable task breakdown for implementing the Specialist Agent feature, organized by user story priority to enable incremental delivery and independent testing.

**MVP Scope**: User Story 1 (Balance Inquiry) + User Story 5/6 (Agent Infrastructure)

**Total Estimated Time**: 8-10 hours

---

## Phase 1: Setup & Project Initialization

**Goal**: Prepare development environment and verify prerequisites

**Tasks**:
- [ ] T001 Verify Greeter Agent is implemented and tested in app/agents/greeter.py
- [ ] T002 Verify Bouncer Agent is implemented and tested in app/agents/bouncer.py
- [ ] T003 Verify GraphState has customer_tier and customer_intent fields in app/graph/state.py
- [ ] T004 Verify guardrails system exists in app/guardrails/guardrails.py
- [ ] T005 Install langchain and langchain-openai dependencies via pip
- [ ] T006 Create app/agents/specialist.py file structure with imports

**Completion Criteria**: All dependencies verified, specialist.py file created

---

## Phase 2: Foundational Infrastructure (BLOCKING)

**Goal**: Extend data models to support banking operations

**⚠️ CRITICAL**: This phase BLOCKS all user stories—must complete before tool implementation

**Tasks**:
- [ ] T007 Add Transaction model to app/models/schemas.py with date, description, amount fields
- [ ] T008 Extend Account model in app/models/schemas.py with balance, currency, transactions list, card_blocked fields
- [ ] T009 Add ACCOUNTS_DB dictionary to app/models/database.py with 3 mock accounts (user_001/Lisa/VIP/5420.50 EUR, user_002/John/Standard/1247.80 GBP, user_003/Maria/Standard/325.10 EUR)
- [ ] T010 Add 5 sample transactions to each mock account in ACCOUNTS_DB

**Completion Criteria**: 
- Transaction model validates date/description/amount
- Account model includes all banking fields
- ACCOUNTS_DB contains 3 complete mock accounts with transaction history
- All tests in tests/test_data_models.py pass

**Independent Testing**:
```python
# Verify Transaction model
t = Transaction(date="2026-03-01", description="Test", amount=100.0)
assert t.date == "2026-03-01"

# Verify extended Account model
from app.models.database import ACCOUNTS_DB
account = ACCOUNTS_DB["user_001"]
assert account.balance == 5420.50
assert len(account.transactions) == 5
assert account.card_blocked == False
```

---

## Phase 3: User Story 1 — Account Balance Inquiry (P1) 🎯 MVP

**Story Goal**: As a customer, I want to check my account balance so I can see how much money I have

**Priority**: P1 (Must Have)

**Tasks**:
- [ ] T011 [P] [US1] Implement get_account_balance tool in app/agents/specialist.py with @tool decorator
- [ ] T012 [P] [US1] Add docstring to get_account_balance describing purpose and parameters for LLM
- [ ] T013 [US1] Implement account lookup by user_id in ACCOUNTS_DB within get_account_balance
- [ ] T014 [US1] Return dict with balance and currency keys from get_account_balance
- [ ] T015 [US1] Handle account not found error in get_account_balance by returning error dict
- [ ] T016 [US1] Add logging for get_account_balance invocations and results
- [ ] T016a [US1] Implement retry logic (retry once on failure per FR-019) in get_account_balance

**Completion Criteria**:
- get_account_balance returns {"balance": float, "currency": str} for valid user_id
- Returns {"error": "Account not found"} for invalid user_id
- Executes in <500ms (in-memory lookup)
- Read-only operation (no side effects)

**Independent Testing**:
```python
# Direct tool invocation test
result = get_account_balance("user_001")
assert result == {"balance": 5420.50, "currency": "EUR"}

result = get_account_balance("invalid_user")
assert "error" in result
```

**Acceptance Criteria** (from spec.md):
- ✅ Agent retrieves balance using user_id from state
- ✅ Response includes both balance amount and currency
- ✅ Response is conversational (not raw JSON)
- ✅ Handles missing accounts gracefully

---

## Phase 4: User Story 2 — Transaction History Review (P2)

**Story Goal**: As a customer, I want to view my recent transactions so I can track my spending

**Priority**: P2 (Should Have)

**Tasks**:
- [ ] T017 [P] [US2] Implement get_transaction_history tool in app/agents/specialist.py with @tool decorator
- [ ] T018 [P] [US2] Add docstring to get_transaction_history describing purpose and parameters for LLM
- [ ] T019 [US2] Add limit parameter with default value 5 to get_transaction_history
- [ ] T020 [US2] Implement limit clamping logic (min 1, max 20) in get_transaction_history
- [ ] T021 [US2] Implement account lookup and transaction slicing ([-limit:]) in get_transaction_history
- [ ] T022 [US2] Return list of transaction dicts (date, description, amount) from get_transaction_history
- [ ] T023 [US2] Handle account not found by returning empty list from get_transaction_history
- [ ] T024 [US2] Add logging for get_transaction_history invocations with limit parameter
- [ ] T024a [US2] Implement retry logic (retry once on failure per FR-019) in get_transaction_history

**Completion Criteria**:
- get_transaction_history returns list of recent transactions (up to 20)
- Default limit is 5 transactions
- Limit is clamped to [1, 20] range
- Returns empty list for invalid user_id
- Executes in <500ms
- Read-only operation

**Independent Testing**:
```python
# Default limit (5 transactions)
result = get_transaction_history("user_001")
assert len(result) == 5

# Custom limit (clamped to 20)
result = get_transaction_history("user_001", limit=50)
assert len(result) <= 20

# Invalid user
result = get_transaction_history("invalid_user")
assert result == []
```

**Acceptance Criteria** (from spec.md):
- ✅ Agent presents transactions in readable format (date, description, amount)
- ✅ Default shows 5 transactions
- ✅ Customer can request different count (1-20)
- ✅ Handles accounts with no transactions gracefully

---

## Phase 5: User Story 5 — Multi-Turn Conversation Resolution (P2)

**Story Goal**: As a customer, I want to have a natural conversation with follow-up questions so I don't have to repeat myself

**Priority**: P2 (Should Have)

**Dependencies**: Requires at least one tool (US1 or US2) to be implemented

**Tasks**:
- [ ] T025 [US5] Import create_tool_calling_agent and AgentExecutor from langchain.agents in app/agents/specialist.py
- [ ] T026 [US5] Import ChatOpenAI from langchain_openai in app/agents/specialist.py
- [ ] T027 [US5] Create specialist_agent function with State parameter in app/agents/specialist.py
- [ ] T028 [US5] Initialize ChatOpenAI with model="gpt-4o-mini" and temperature=0 in specialist_agent
- [ ] T029 [US5] Create tools list containing all implemented tool functions in specialist_agent
- [ ] T030 [US5] Build system prompt using placeholder (to be replaced in Phase 6) in specialist_agent
- [ ] T031 [US5] Create tool-calling agent using create_tool_calling_agent with llm, tools, and prompt
- [ ] T032 [US5] Create AgentExecutor with agent and tools in specialist_agent
- [ ] T033 [US5] Invoke agent_executor with conversation history from state["messages"]
- [ ] T034 [US5] Extract agent response and append to state["messages"] in specialist_agent
- [ ] T035 [US5] Implement conversation turn counting logic where 1 turn = 1 customer message + 1 agent response (track turn_count in state)
- [ ] T036 [US5] Implement conversation ending at turn 10 per FR-018 (set conversation_ended=True, add boundary message with callback offer)
- [ ] T037 [US5] Return updated state from specialist_agent function
- [ ] T037a [US5] Implement out-of-scope service detection in specialist_agent (mortgage, investment advice, new accounts, loans, credit cards, account closure, disputes, financial planning)
- [ ] T037b [US5] Add handoff message for out-of-scope requests per FR-017 with polite explanation and conversation ending

**Completion Criteria**:
- AgentExecutor successfully invokes tools based on user requests
- Conversation history is maintained across turns
- Agent can handle follow-up questions without re-authentication
- Conversation automatically ends at turn 10 with polite boundary message
- state["conversation_ended"] is set to True when ending conversation

**Independent Testing**:
```python
# Multi-turn conversation test
state = {
    "messages": [{"role": "user", "content": "What's my balance?"}],
    "verified_user": User(user_id="user_001", name="Lisa"),
    "customer_tier": "vip",
    "customer_intent": "account_inquiry",
    "turn_count": 1,
}

result = specialist_agent(state)
assert "balance" in result["messages"][-1]["content"].lower()

# Follow-up without re-auth
result["messages"].append({"role": "user", "content": "And my transactions?"})
result["turn_count"] = 2
result = specialist_agent(result)
assert "transaction" in result["messages"][-1]["content"].lower()

# Turn 10 boundary
state["turn_count"] = 10
result = specialist_agent(state)
assert result["conversation_ended"] == True
```

**Acceptance Criteria** (from spec.md):
- ✅ Agent maintains context across multiple turns
- ✅ Customer can ask follow-ups without repeating information
- ✅ Conversation ends gracefully at turn 10 with callback offer
- ✅ state["conversation_ended"] is set when conversation concludes

---

## Phase 6: User Story 6 — Tier-Specific Persona Adaptation (P2)

**Story Goal**: As a premium customer, I want personalized service so I feel valued

**Priority**: P2 (Should Have)

**Dependencies**: Requires US5 (specialist_agent function) to be implemented

**Tasks**:
- [ ] T038 [P] [US6] Define PERSONA_STANDARD constant in app/agents/specialist.py (concise, efficient tone)
- [ ] T039 [P] [US6] Define PERSONA_PREMIUM constant in app/agents/specialist.py (warm, personalized tone)
- [ ] T040 [P] [US6] Define PERSONA_VIP constant in app/agents/specialist.py (white-glove service, proactive suggestions)
- [ ] T041 [US6] Implement build_system_prompt function in app/agents/specialist.py
- [ ] T042 [US6] Extract customer_tier from state with default fallback to "standard" in build_system_prompt
- [ ] T043 [US6] Map tier to persona constant using dict lookup in build_system_prompt
- [ ] T044 [US6] Extract customer_name from state["verified_user"].name in build_system_prompt
- [ ] T045 [US6] Extract customer_intent from state in build_system_prompt
- [ ] T046 [US6] Build formatted system prompt with persona, customer name, and intent using f-string
- [ ] T047 [US6] Add instructions to never expose raw tool output or user IDs in system prompt
- [ ] T048 [US6] Replace placeholder system prompt in specialist_agent with call to build_system_prompt(state)

**Completion Criteria**:
- Three distinct persona constants defined (Standard, Premium, VIP)
- build_system_prompt generates tier-appropriate prompts
- Falls back to Standard persona if tier is missing or unrecognized
- System prompt includes customer name and intent for personalization
- Agent responses match expected tone for each tier

**Independent Testing**:
```python
# Standard tier test
state = {"customer_tier": "standard", "verified_user": User(name="John"), "customer_intent": "balance_inquiry"}
prompt = build_system_prompt(state)
assert "helpful" in prompt.lower() or "concise" in prompt.lower()

# VIP tier test
state["customer_tier"] = "vip"
state["verified_user"].name = "Lisa"
prompt = build_system_prompt(state)
assert "vip" in prompt.lower() or "private banking" in prompt.lower()

# Missing tier (fallback)
state_no_tier = {"verified_user": User(name="Test"), "customer_intent": "inquiry"}
prompt = build_system_prompt(state_no_tier)
assert prompt  # Should not crash, should use Standard fallback
```

**Acceptance Criteria** (from spec.md):
- ✅ Standard tier receives helpful, efficient responses
- ✅ Premium tier receives warm, personalized responses
- ✅ VIP tier receives white-glove service with proactive suggestions
- ✅ Tier defaults to Standard if not found in state

---

## Phase 7: User Story 3 — Fund Transfer Execution (P3)

**Story Goal**: As a customer, I want to transfer money to another account so I can pay friends or bills

**Priority**: P3 (Could Have)

**Dependencies**: Requires Phase 2 (extended Account model with balance field)

**Tasks**:
- [ ] T049 [P] [US3] Implement transfer_funds tool in app/agents/specialist.py with @tool decorator
- [ ] T050 [P] [US3] Add docstring to transfer_funds describing purpose and parameters for LLM
- [ ] T051 [US3] Add parameters: user_id, recipient_iban, amount, description to transfer_funds
- [ ] T052 [US3] Implement account lookup by user_id in transfer_funds
- [ ] T053 [US3] Implement basic IBAN validation (regex pattern ^[A-Z]{2}[A-Z0-9]{13,32}$) in transfer_funds
- [ ] T054 [US3] Implement balance check (account.balance >= amount) in transfer_funds
- [ ] T055 [US3] Deduct amount from account.balance if validation passes in transfer_funds
- [ ] T056 [US3] Append Transaction record with negative amount to account.transactions in transfer_funds
- [ ] T057 [US3] Generate mock transaction_id using uuid4 in transfer_funds
- [ ] T058 [US3] Return success dict with transaction_id from transfer_funds
- [ ] T059 [US3] Handle validation failures (invalid IBAN, insufficient funds, account not found) by returning error dict with reason
- [ ] T060 [US3] Add logging for transfer attempts, successes, and failures
- [ ] T061 [US3] Implement retry logic (retry once on failure per FR-019) in transfer_funds

**Completion Criteria**:
- transfer_funds validates IBAN format (15-34 chars, starts with 2 letters)
- Checks sufficient balance before transfer
- Deducts amount and records transaction on success
- Returns {"success": true, "transaction_id": "TXN-..."} on success
- Returns {"success": false, "reason": "..."} on failure
- Executes in <3s
- Properly handles edge cases (invalid IBAN, insufficient funds)

**Independent Testing**:
```python
# Successful transfer
result = transfer_funds("user_001", "GB29NWBK60161331926819", 100.0, "Test payment")
assert result["success"] == True
assert "transaction_id" in result
assert ACCOUNTS_DB["user_001"].balance == 5320.50  # 5420.50 - 100.0

# Insufficient funds
result = transfer_funds("user_001", "GB29NWBK60161331926819", 10000.0, "Large payment")
assert result["success"] == False
assert result["reason"] == "Insufficient funds"

# Invalid IBAN
result = transfer_funds("user_001", "INVALID", 50.0, "Bad IBAN")
assert result["success"] == False
assert result["reason"] == "Invalid IBAN format"
```

**Acceptance Criteria** (from spec.md):
- ✅ Agent validates IBAN format before transfer
- ✅ Checks sufficient balance
- ✅ Confirms transfer success with transaction ID
- ✅ Handles validation errors gracefully (insufficient funds, invalid IBAN)
- ✅ Transfer completes in <3s

---

## Phase 8: User Story 4 — Lost Card Reporting (P3)

**Story Goal**: As a customer, I want to report my card as lost so it gets blocked immediately

**Priority**: P3 (Could Have)

**Dependencies**: Requires Phase 2 (extended Account model with card_blocked field)

**Tasks**:
- [ ] T062 [P] [US4] Implement report_lost_card tool in app/agents/specialist.py with @tool decorator
- [ ] T063 [P] [US4] Add docstring to report_lost_card describing purpose and parameters for LLM
- [ ] T064 [US4] Add user_id parameter to report_lost_card
- [ ] T065 [US4] Implement account lookup by user_id in report_lost_card
- [ ] T066 [US4] Set account.card_blocked to True in report_lost_card
- [ ] T067 [US4] Generate mock case_id using uuid4 in report_lost_card
- [ ] T068 [US4] Return success dict with case_id from report_lost_card
- [ ] T069 [US4] Handle account not found error by returning error dict with reason
- [ ] T070 [US4] Add logging for card blocking requests and outcomes
- [ ] T071 [US4] Implement retry logic (retry once on failure per FR-019) in report_lost_card

**Completion Criteria**:
- report_lost_card sets card_blocked flag to True
- Generates unique case ID for tracking
- Returns {"success": true, "case_id": "CASE-..."} on success
- Returns {"success": false, "reason": "Account not found"} on failure
- Executes in <2s
- Idempotent (safe to call multiple times)

**Independent Testing**:
```python
# Successful card blocking
result = report_lost_card("user_001")
assert result["success"] == True
assert "case_id" in result
assert ACCOUNTS_DB["user_001"].card_blocked == True

# Idempotency test (call again)
result2 = report_lost_card("user_001")
assert result2["success"] == True
assert result2["case_id"] != result["case_id"]  # New case ID each time

# Account not found
result = report_lost_card("invalid_user")
assert result["success"] == False
assert result["reason"] == "Account not found"
```

**Acceptance Criteria** (from spec.md):
- ✅ Agent blocks card immediately
- ✅ Provides case reference number for tracking
- ✅ Confirms blocking with customer
- ✅ Handles missing accounts gracefully
- ✅ Completes in <2s

---

## Phase 9: Polish & Cross-Cutting Concerns

**Goal**: Integrate specialist agent into LangGraph pipeline and ensure production readiness

**Tasks**:
- [ ] T072 [P] Wire specialist_agent into LangGraph pipeline in app/graph/pipeline.py
- [ ] T073 [P] Add conditional edge from bouncer to specialist in app/graph/pipeline.py
- [ ] T074 [P] Update routing logic in bouncer_agent to direct banking intents to specialist
- [ ] T075 Add guardrails integration to specialist_agent (run_guardrails on input and output)
- [ ] T076 Add comprehensive error handling with try-except blocks to specialist_agent
- [ ] T077 Add guardrails to all tool functions (validate inputs prevent prompt injection)
- [ ] T078 Write integration test for balance inquiry end-to-end flow in tests/test_specialist.py
- [ ] T079 Write integration test for transaction history end-to-end flow in tests/test_specialist.py
- [ ] T080 Write integration test for fund transfer end-to-end flow in tests/test_specialist.py
- [ ] T081 Write integration test for card blocking end-to-end flow in tests/test_specialist.py
- [ ] T082 Write integration test for multi-turn conversation in tests/test_specialist.py
- [ ] T083 Write integration test for tier persona adaptation in tests/test_specialist.py
- [ ] T084 Test conversation ending at turn 10 boundary in tests/test_specialist.py
- [ ] T085 Test retry logic for tool failures in tests/test_specialist.py
- [ ] T086 Add logging throughout specialist agent and tools
- [ ] T087 Update README.md with specialist agent documentation
- [ ] T088 Run full test suite and verify all tests pass
- [ ] T089 Write test to validate FR-012/SC-006: scan agent responses for prohibited patterns (user_id=, raw JSON braces, database references) and verify zero exposure
- [ ] T090 Write test to validate FR-017/SC-008: verify out-of-scope requests (mortgage, investment, new account, loan) trigger appropriate handoff message
- [ ] T091 Write test to validate SC-004: typical requests (balance, transactions, transfer, card) resolve within 5 turns
- [ ] T092 Write test to validate SC-009: transaction history limit is correctly clamped to [1, 20] range for edge values (0, 50, 100)

**Completion Criteria**:
- Specialist agent is fully integrated into LangGraph pipeline
- All 4 tools are accessible and functional
- Guardrails protect against prompt injection and data exposure
- All integration tests pass
- Documentation is complete

---

## Implementation Dependencies

### Story Completion Order

```
Phase 1 (Setup) 
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
    ├─→ Phase 3 (US1) ─┐
    ├─→ Phase 4 (US2) ─┤
    └─→ Phase 5 (US5) ←┴─ (needs at least one tool)
            ↓
        Phase 6 (US6)
            ↓
    ├─→ Phase 7 (US3)
    └─→ Phase 8 (US4)
            ↓
        Phase 9 (Polish & Integration)
```

### Parallel Execution Opportunities

**After Phase 2 completes**, these can be worked on in parallel:
- Phase 3 (US1: get_account_balance tool) 
- Phase 4 (US2: get_transaction_history tool)

**After Phase 6 completes**, these can be worked on in parallel:
- Phase 7 (US3: transfer_funds tool)
- Phase 8 (US4: report_lost_card tool)

**During Phase 9**, these can be worked on in parallel:
- Integration tests (T078-T085)
- Documentation (T087)
- Guardrails integration (T075-T077)

### Critical Path

Setup → Foundational → US1 → US5 → US6 → Integration (MVP)

**MVP Delivery**: Phase 1 + 2 + 3 + 5 + 6 provides a working agent with balance inquiry capability, conversation management, and tier-based personas. This is the minimum viable product for stakeholder demo.

---

## Implementation Strategy

### Recommended Approach

1. **MVP First** (Phases 1-3, 5-6): 
   - Complete foundational infrastructure
   - Implement single tool (balance inquiry)
   - Build agent framework with conversation management
   - Add tier-based personas
   - Result: Demonstrable agent that can check balances with appropriate tone

2. **Incremental Tool Addition** (Phases 4, 7-8):
   - Add transaction history (low risk, read-only)
   - Add fund transfers (medium risk, write operation)
   - Add card blocking (low risk, simple write)
   - Result: Full-featured banking agent

3. **Polish & Production** (Phase 9):
   - Integration testing
   - Guardrails hardening
   - Documentation
   - Result: Production-ready agent

### Testing Strategy

Each user story has independent test criteria that can be verified in isolation:

- **US1**: Direct tool invocation returns balance
- **US2**: Direct tool invocation returns transaction list
- **US3**: Direct tool invocation executes transfer and updates balance
- **US4**: Direct tool invocation sets card_blocked flag
- **US5**: Agent maintains conversation state across turns and ends at turn 10
- **US6**: System prompt includes tier-appropriate persona

### Validation Checklist

Before marking each phase complete:
- [ ] All tasks have checkboxes and IDs
- [ ] File paths are specified for implementation tasks
- [ ] Independent test criteria are clearly defined
- [ ] Acceptance criteria from spec.md are mapped to tasks
- [ ] Dependencies are clearly marked
- [ ] Parallel opportunities are identified with [P] markers

---

## Success Metrics

Upon completion, the following success criteria from spec.md should be met:

- **SC-001**: Specialist agent successfully invokes all 4 banking tools ✅
- **SC-002**: Tool call failures trigger retry logic with graceful degradation ✅
- **SC-003**: Balance inquiries complete in <2s, transfers in <3s ✅
- **SC-004**: VIP customers receive white-glove tone, Standard customers receive efficient tone ✅
- **SC-005**: Conversations can extend 5+ turns without losing context ✅
- **SC-006**: Conversations end politely at turn 10 with callback offer ✅
- **SC-007**: Transfer tool validates IBAN format before execution ✅
- **SC-008**: Transfer tool checks balance before execution ✅
- **SC-009**: Transaction history tool clamps limit to [1, 20] range ✅
- **SC-010**: Card blocking tool returns case ID for customer tracking ✅

**Task Count by Phase**:
- Phase 1 (Setup): 6 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (US1): 7 tasks (added retry logic)
- Phase 4 (US2): 9 tasks (added retry logic)
- Phase 5 (US5): 15 tasks (added out-of-scope detection)
- Phase 6 (US6): 11 tasks
- Phase 7 (US3): 13 tasks
- Phase 8 (US4): 10 tasks
- Phase 9 (Polish): 21 tasks (added validation tests)

**Total**: 95 tasks

**MVP Scope**: 42 tasks (Phases 1-3, 5-6 including new out-of-scope and retry tasks)
**Full Feature**: 95 tasks (all phases)

---

**Ready to implement!** Start with Phase 1 to verify prerequisites, then proceed to Phase 2 (foundational models). The MVP can be delivered after Phase 6.
