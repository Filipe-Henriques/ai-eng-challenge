# Tasks: Bouncer Agent

**Input**: Design documents from `/specs/005-bouncer-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/agent-interface.md, quickstart.md

**Feature**: Single-turn tier classification and routing agent in LangGraph pipeline

**Tests**: Included - spec requires comprehensive testing per agent interface contract

**Organization**: Tasks are grouped by capability to enable incremental delivery (basic routing → intent classification → enhanced handoff)

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which capability this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Project uses single-project structure:
- `app/` - Application code
- `tests/` - Test files

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend GraphState and prepare for Bouncer Agent integration

- [ ] T001 Extend GraphState with three new fields in app/graph/state.py: customer_tier (Optional[str] = None), customer_intent (Optional[str] = None), current_agent (str, default "greeter")
- [ ] T002 [P] Create ClassifiedIntent Pydantic model in app/agents/bouncer.py with intent (Literal type) and confidence (float) fields
- [ ] T003 [P] Define TIER_ROUTING constant dictionary in app/agents/bouncer.py mapping tiers to specialist agent names

**Checkpoint**: State model ready for Bouncer Agent implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Verify Greeter Agent sets is_authenticated and verified_user in state (prerequisite validation)
- [ ] T005 Verify guardrails module exists and run_guardrails function is available in app/guardrails/guardrails.py
- [ ] T006 Create test fixtures for mock authenticated state in tests/test_bouncer.py

**Checkpoint**: Foundation ready - Bouncer Agent implementation can now begin

---

## Phase 3: User Story 1 - Basic Tier Routing (Priority: P1) 🎯 MVP

**Goal**: Authenticated customers are routed to the correct specialist based on their account tier

**Independent Test**: Mock user with each tier (standard/premium/vip) → verify current_agent is set correctly

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T007 [P] [US1] Unit test for standard tier routing in tests/test_bouncer.py: test_bouncer_routes_standard_customer
- [ ] T008 [P] [US1] Unit test for premium tier routing in tests/test_bouncer.py: test_bouncer_routes_premium_customer
- [ ] T009 [P] [US1] Unit test for vip tier routing in tests/test_bouncer.py: test_bouncer_routes_vip_customer
- [ ] T010 [P] [US1] Unit test for unknown tier fallback in tests/test_bouncer.py: test_bouncer_fallback_unknown_tier

### Implementation for User Story 1

- [ ] T011 [US1] Create bouncer_agent function skeleton in app/agents/bouncer.py with GraphState input and dict output
- [ ] T012 [US1] Implement tier reading logic: extract tier from state['verified_user'].tier in app/agents/bouncer.py
- [ ] T013 [US1] Implement routing logic: use TIER_ROUTING dict with defensive default to specialist_standard in app/agents/bouncer.py
- [ ] T014 [US1] Implement state updates: set customer_tier and current_agent fields in bouncer_agent return dict
- [ ] T015 [US1] Add hardcoded handoff message "Connecting you to a specialist..." (temporary, replaced in US3)
- [ ] T016 [US1] Add input guardrail check at function start with early return if unsafe in app/agents/bouncer.py

**Checkpoint**: At this point, basic tier routing should work - authenticated users route to correct specialist

---

## Phase 4: User Story 2 - Intent Classification (Priority: P2)

**Goal**: Customer intent is automatically classified from conversation history to provide context to specialists

**Independent Test**: Provide conversation with clear intent → verify customer_intent is set correctly and confidence threshold works

### Tests for User Story 2

- [ ] T017 [P] [US2] Unit test for account_balance intent classification in tests/test_bouncer.py: test_bouncer_classifies_account_balance
- [ ] T018 [P] [US2] Unit test for transaction_history intent classification in tests/test_bouncer.py: test_bouncer_classifies_transaction_history
- [ ] T019 [P] [US2] Unit test for fund_transfer intent classification in tests/test_bouncer.py: test_bouncer_classifies_fund_transfer
- [ ] T020 [P] [US2] Unit test for lost_card intent classification in tests/test_bouncer.py: test_bouncer_classifies_lost_card
- [ ] T021 [P] [US2] Unit test for general_inquiry intent classification in tests/test_bouncer.py: test_bouncer_classifies_general_inquiry
- [ ] T022 [P] [US2] Unit test for low confidence fallback in tests/test_bouncer.py: test_bouncer_fallback_low_confidence

### Implementation for User Story 2

- [ ] T023 [US2] Build conversation history string from state['messages'] in bouncer_agent function
- [ ] T024 [US2] Create system prompt for intent classification in app/agents/bouncer.py (instructs LLM on 5 supported intents)
- [ ] T025 [US2] Initialize ChatOpenAI with model gpt-4o-mini, temperature 0.3, and timeout 10s in bouncer_agent function
- [ ] T026 [US2] Create LLM chain with structured output using ClassifiedIntent model in bouncer_agent function
- [ ] T027 [US2] Invoke LLM with conversation history and extract ClassifiedIntent result
- [ ] T028 [US2] Implement confidence threshold check: if confidence < 0.5, override intent to general_inquiry
- [ ] T029 [US2] Add try-except error handling: single retry on timeout, fallback to general_inquiry on LLM failure after retry
- [ ] T030 [US2] Update state return dict to include customer_intent field

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - routing works AND intent is classified

---

## Phase 5: User Story 3 - Enhanced Handoff Messages (Priority: P3)

**Goal**: Customers receive warm, professional, LLM-generated handoff messages that pass safety guardrails

**Independent Test**: Verify handoff message is generated by LLM, passes guardrails, and is appended to conversation history

### Tests for User Story 3

- [ ] T031 [P] [US3] Unit test for handoff message generation in tests/test_bouncer.py: test_bouncer_generates_handoff_message
- [ ] T032 [P] [US3] Unit test for output guardrail sanitization in tests/test_bouncer.py: test_bouncer_sanitizes_output
- [ ] T033 [P] [US3] Unit test for message appending to history in tests/test_bouncer.py: test_bouncer_appends_to_messages

### Implementation for User Story 3

- [ ] T034 [US3] Remove hardcoded handoff message from US1 implementation
- [ ] T035 [US3] Create handoff prompt template in bouncer_agent: instructs LLM to generate one-sentence professional handoff
- [ ] T036 [US3] Invoke LLM for free-form handoff message generation (not structured output)
- [ ] T037 [US3] Add try-except for handoff generation: fallback to default message on failure
- [ ] T038 [US3] Apply output guardrails: call run_guardrails on generated handoff message
- [ ] T039 [US3] Use sanitised_response from guardrails output check
- [ ] T040 [US3] Append AIMessage with final handoff to state['messages'] in return dict

**Checkpoint**: All user stories complete - full Bouncer Agent functionality working end-to-end

---

## Phase 6: LangGraph Integration

**Purpose**: Integrate Bouncer Agent as a node in the LangGraph pipeline

- [ ] T041 Import bouncer_agent in app/graph/pipeline.py
- [ ] T042 Add bouncer node to StateGraph: graph.add_node("bouncer", bouncer_agent)
- [ ] T043 Create route_from_greeter conditional edge function: returns "bouncer" if is_authenticated else loops greeter
- [ ] T044 Create route_from_bouncer conditional edge function: returns state["current_agent"] (specialist name)
- [ ] T045 Add conditional edge from greeter node: graph.add_conditional_edges("greeter", route_from_greeter)
- [ ] T046 Add conditional edge from bouncer node: graph.add_conditional_edges("bouncer", route_from_bouncer)
- [ ] T047 Verify entry point is set to "greeter": graph.set_entry_point("greeter")

**Checkpoint**: Bouncer Agent is fully integrated into LangGraph pipeline

---

## Phase 7: Integration Testing

**Purpose**: Verify end-to-end flow from Greeter to Bouncer to (mock) Specialist

**Note**: These tests assume Specialist Agent nodes (specialist_standard, specialist_premium, specialist_vip) will be implemented in future features. Tests use mocks or stubs for specialists.

- [ ] T048 [P] Integration test for full authentication to routing flow in tests/test_bouncer.py: test_integration_greeter_to_bouncer
- [ ] T049 [P] Integration test for unsafe input blocking in tests/test_bouncer.py: test_bouncer_blocks_unsafe_input
- [ ] T050 [P] Integration test for single-turn execution (no loops) in tests/test_bouncer.py: test_bouncer_single_turn_execution

**Checkpoint**: All integration tests pass - Bouncer Agent works with upstream (Greeter) and downstream (Specialist) agents

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final touches

- [ ] T051 [P] Add Google Style docstrings to bouncer_agent function in app/agents/bouncer.py
- [ ] T052 [P] Add Google Style docstrings to ClassifiedIntent model in app/agents/bouncer.py
- [ ] T053 [P] Add inline comments for confidence threshold logic in app/agents/bouncer.py
- [ ] T054 Run full test suite: pytest tests/test_bouncer.py -v
- [ ] T055 Verify quickstart.md steps against implementation
- [ ] T056 Run Black formatter on app/agents/bouncer.py
- [ ] T057 Quick validation: Verify all constitution principles are satisfied (should all pass per plan.md Constitution Check)
- [ ] T058 Manual test: Run full conversation from greeting to routing with sample user

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (Basic Routing): Can start after Foundational - No LLM requirements
  - US2 (Intent Classification): Depends on US1 (extends bouncer_agent function)
  - US3 (Enhanced Handoff): Depends on US2 (replaces placeholder message)
- **LangGraph Integration (Phase 6)**: Depends on US1 minimum (US2+US3 optional for MVP)
- **Integration Testing (Phase 7)**: Depends on Phase 6 (LangGraph integration complete)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - MVP)**: Can start after Foundational (Phase 2) - No dependencies on other stories
  - Delivers: Basic tier-based routing with placeholder handoff message
  - MVP sufficient for testing end-to-end pipeline
  
- **User Story 2 (P2)**: Depends on US1 completion (extends same function)
  - Delivers: Intent classification for specialist context
  - Can proceed without US3 (uses US1's placeholder message)
  
- **User Story 3 (P3)**: Depends on US2 completion (uses intent for handoff prompt)
  - Delivers: Professional LLM-generated handoff messages
  - Final polish - not required for basic functionality

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Write all tests for a story first (marked [P] tasks can run in parallel)
- Implementation tasks in sequence (each builds on previous)
- Story complete and passing tests before moving to next priority

### Parallel Opportunities

#### Phase 1 (Setup)
- T002 (ClassifiedIntent model) and T003 (TIER_ROUTING) can run in parallel with T001 (GraphState)

#### Phase 2 (Foundational)
- T004 (verify Greeter) and T005 (verify guardrails) can run in parallel

#### Within User Stories
- All test tasks marked [P] within a story can run in parallel
- Tests MUST run (and fail) before implementation tasks

#### Across User Stories (if team capacity allows)
- After Foundational completes, could theoretically work on US1 and US2 in parallel
- However, US2 extends US1's function, so sequential is safer
- US3 could be started in parallel with US2 if using feature branches

---

## Parallel Example: User Story 2 Implementation

```bash
# After US1 is complete and US2 tests are written, these can run in parallel:
# (Though in practice, they modify the same function, so coordinate carefully)

# Write tests first (all in parallel):
Task: T017 - test_bouncer_classifies_account_balance
Task: T018 - test_bouncer_classifies_transaction_history  
Task: T019 - test_bouncer_classifies_fund_transfer
Task: T020 - test_bouncer_classifies_lost_card
Task: T021 - test_bouncer_classifies_general_inquiry
Task: T022 - test_bouncer_fallback_low_confidence

# Then implement sequentially (same function):
Task: T023 → T024 → T025 → T026 → T027 → T028 → T029 → T030
```

---

## Implementation Strategy

### MVP First (Just User Story 1)

1. Complete Phase 1: Setup (state + models) - ~5 min
2. Complete Phase 2: Foundational (verify prereqs) - ~5 min
3. Complete Phase 3: User Story 1 (basic routing) - ~10 min
4. Complete Phase 6: LangGraph Integration - ~5 min
5. **STOP and VALIDATE**: Test basic routing independently
6. Deploy/demo if ready

**MVP Delivers**: Authenticated users are routed to correct specialist based on tier
**What's Missing**: Intent classification (defaults to general_inquiry), LLM-generated handoffs

### Recommended Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (~10 min)
2. Add User Story 1 + Integration → Test independently → MVP ready! (~15 min)
3. Add User Story 2 → Test independently → Intent classification working (~15 min)
4. Add User Story 3 → Test independently → Full feature complete (~10 min)
5. Integration Testing + Polish → Production ready (~10 min)

**Total time**: ~60 minutes (vs 30 min in quickstart, which skips TDD and some tests)

### Parallel Team Strategy

With multiple developers (advanced):

1. Team completes Setup + Foundational together
2. Developer A: User Story 1 (core routing)
3. Once US1 done:
   - Developer A: User Story 2 (intent classification)
   - Developer B: Pre-write tests for User Story 3
4. Once US2 done:
   - Developer A: User Story 3 (enhanced handoff)
   - Developer B: LangGraph Integration (Phase 6)
5. Together: Integration Testing + Polish

---

## Notes

- [P] tasks = different files or independent test cases, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story delivers incremental value and is independently testable
- US1 is MVP - system works end-to-end with basic routing
- US2 adds intelligence - better context for specialists
- US3 adds polish - better customer experience
- Tests use mocked ChatOpenAI and run_guardrails for fast, deterministic execution
- Commit after each task or logical group
- Follow TDD: Write tests first, watch them fail, make them pass
- See quickstart.md for code examples and implementation details
- See contracts/agent-interface.md for interface requirements