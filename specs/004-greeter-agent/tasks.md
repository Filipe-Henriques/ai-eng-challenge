# Tasks: Greeter Agent

**Feature**: 004-greeter-agent  
**Branch**: `004-greeter-agent`  
**Input**: Design documents from `/specs/004-greeter-agent/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/agent-interface.md](contracts/agent-interface.md)

**Context**: Implement the Greeter Agent, the first node in the DEUS Bank AI Support System LangGraph pipeline. The agent welcomes customers, collects identity information, verifies them using 2-out-of-3 matching, and authenticates via secret question.

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[INC#]**: Implementation increment number (INC1, INC2, etc.)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project structure and agent file scaffolding

- [X] T001 Create `app/agents/` directory if it doesn't exist
- [X] T002 Create `app/agents/__init__.py` with empty content
- [X] T003 Create `tests/test_greeter.py` with pytest imports and basic structure

---

## Phase 2: Foundational

**Purpose**: Core infrastructure and helper functions needed by all increments

**⚠️ CRITICAL**: These must be complete before agent implementation can begin

- [X] T004 Add `DatabaseUnavailableError` exception class to `app/models/database.py`
- [X] T005 Implement `find_user_with_retry()` helper function in `app/models/database.py` with single retry logic (NEW wrapper around existing `find_user_by_fields()`)
- [X] T006 Add docstrings and type hints to retry function following Google Style

**Checkpoint**: Foundation ready - agent implementation can now begin

---

## Phase 3: Increment 1 - Basic Agent Structure & Welcome (INC1) 🎯 MVP

**Goal**: Create basic agent node that accepts state, applies input guardrails, and returns welcome message on first turn

**Independent Test**: Agent responds with welcome message when given single-message state; guardrail rejection ends conversation

### Tests for Increment 1

> **Write tests FIRST, ensure they FAIL before implementation**

- [X] T007 [P] [INC1] Write test for welcome message on first turn in `tests/test_greeter.py`
- [X] T008 [P] [INC1] Write test for guardrail rejection (unsafe input) in `tests/test_greeter.py`

### Implementation for Increment 1

- [X] T009 [INC1] Create `app/agents/greeter.py` with module docstring
- [X] T010 [INC1] Define `ExtractedInfo` Pydantic model in `app/agents/greeter.py`
- [X] T011 [INC1] Implement `greeter_agent(state: State) -> dict` function skeleton in `app/agents/greeter.py`
- [X] T012 [INC1] Add input guardrail check logic in `greeter_agent()` using `run_guardrails()`
- [X] T013 [INC1] Add welcome message logic for first turn (when `len(state["messages"]) == 1`)
- [X] T014 [INC1] Add max attempts check (if `verification_attempts >= 3`, end conversation) in `greeter_agent()`

**Checkpoint**: Agent handles welcome and guardrail rejection. Tests pass.

---

## Phase 4: Increment 2 - Field Extraction (INC2)

**Goal**: Extract identity fields (name, phone, iban) from user messages using LLM structured output and merge into `collected_fields`

**Independent Test**: Agent extracts fields from user message and merges into state; incremental collection works across multiple turns

### Tests for Increment 2

- [X] T015 [P] [INC2] Write test for field extraction (single message with multiple fields) in `tests/test_greeter.py`
- [X] T016 [P] [INC2] Write test for incremental field collection (multiple turns) in `tests/test_greeter.py`
- [X] T017 [P] [INC2] Write test for field merge behavior (non-None values only) in `tests/test_greeter.py`

### Implementation for Increment 2

- [X] T018 [INC2] Add LLM initialization (`ChatOpenAI` with `gpt-4o-mini`, temperature=0) in `greeter_agent()`
- [X] T019 [INC2] Implement field extraction using `with_structured_output(ExtractedInfo)` in `greeter_agent()`
- [X] T020 [INC2] Add system prompt for field extraction with instructions in `greeter_agent()`
- [X] T021 [INC2] Implement field merge logic (update `collected_fields` with non-None extracted values) in `greeter_agent()`
- [X] T022 [INC2] Add response logic when insufficient fields (<2 non-None) collected in `greeter_agent()`

**Checkpoint**: Agent extracts and collects fields incrementally. Tests pass.

---

## Phase 5: Increment 3 - Identity Verification (INC3)

**Goal**: Verify customer identity using 2-out-of-3 rule with database lookup, handle verification failures and database errors

**Independent Test**: Agent verifies identity when 2+ fields collected; handles success, failure, and database errors correctly

### Tests for Increment 3

- [X] T023 [P] [INC3] Write test for successful 2/3 verification in `tests/test_greeter.py`
- [X] T024 [P] [INC3] Write test for failed verification (no user match) in `tests/test_greeter.py`
- [X] T025 [P] [INC3] Write test for database failure with retry in `tests/test_greeter.py`
- [X] T026 [P] [INC3] Write test for `verification_attempts` increment on failure in `tests/test_greeter.py`

### Implementation for Increment 3

- [X] T027 [INC3] Add logic to count non-None fields in `collected_fields` in `greeter_agent()`
- [X] T028 [INC3] Implement verification attempt when `non_none_count >= 2` using `find_user_with_retry()` in `greeter_agent()`
- [X] T029 [INC3] Add database error handling (catch `DatabaseUnavailableError`, set `conversation_ended=True`) in `greeter_agent()`
- [X] T030 [INC3] Implement verification failure logic (increment `verification_attempts`, return retry message) in `greeter_agent()`
- [X] T031 [INC3] Implement verification success logic (set `verified_user`, ask secret question) in `greeter_agent()`

**Checkpoint**: Agent verifies identity with 2/3 rule, handles all error cases. Tests pass.

---

## Phase 6: Increment 4 - Secret Question Authentication (INC4)

**Goal**: Present secret question after verification, validate customer's answer (case-insensitive), handle authentication success/failure

**Independent Test**: Agent asks secret question after verification; authenticates on correct answer; rejects wrong answers with retry

### Tests for Increment 4

- [X] T032 [P] [INC4] Write test for secret question asked after verification in `tests/test_greeter.py`
- [X] T033 [P] [INC4] Write test for correct secret answer (case-insensitive) in `tests/test_greeter.py`
- [X] T034 [P] [INC4] Write test for incorrect secret answer in `tests/test_greeter.py`
- [X] T035 [P] [INC4] Write test for authentication success state transition in `tests/test_greeter.py`

### Implementation for Increment 4

- [X] T036 [INC4] Add logic to check if `verified_user` is set and `is_authenticated` is False in `greeter_agent()`
- [X] T037 [INC4] Implement secret answer extraction and case-insensitive comparison in `greeter_agent()`
- [X] T038 [INC4] Implement authentication success logic (set `is_authenticated=True`, `current_agent="bouncer"`) in `greeter_agent()`
- [X] T039 [INC4] Implement authentication failure logic (increment `verification_attempts`, return retry message) in `greeter_agent()`

**Checkpoint**: Agent handles complete authentication flow. Tests pass.

---

## Phase 7: Increment 5 - Output Guardrails & Polish (INC5)

**Goal**: Apply output guardrails to all agent responses, add comprehensive Google-style docstrings, ensure all edge cases handled

**Independent Test**: Agent sanitizes all outputs through guardrails; all functions properly documented

### Tests for Increment 5

- [X] T040 [P] [INC5] Write test for output guardrail application in `tests/test_greeter.py`
- [X] T041 [P] [INC5] Write test for max attempts termination (3 failures) in `tests/test_greeter.py`
- [X] T042 [P] [INC5] Write test for conversation flow with all state transitions in `tests/test_greeter.py`

### Implementation for Increment 5

- [X] T043 [INC5] Add output guardrail check to all response paths in `greeter_agent()`
- [X] T044 [INC5] Add comprehensive Google-style docstring to `greeter_agent()` function
- [X] T045 [INC5] Add Google-style docstring to `ExtractedInfo` class
- [X] T046 [INC5] Review and refactor for code clarity and error handling completeness in `app/agents/greeter.py`
- [X] T047 [INC5] Add logging statements for key operations (verification attempts, database calls) in `greeter_agent()`

**Checkpoint**: Agent fully implements spec, all tests pass, code documented.

---

## Phase 8: LangGraph Integration

**Purpose**: Wire Greeter Agent into LangGraph pipeline

- [X] T048 Add greeter node to graph builder in `app/graph/pipeline.py`
- [X] T049 Set greeter as entry point in graph builder in `app/graph/pipeline.py`
- [X] T050 Implement `route_after_greeter()` conditional edge function in `app/graph/pipeline.py`
- [X] T051 Add conditional edges for greeter routing (bouncer/greeter/end) in `app/graph/pipeline.py`
- [X] T052 Write integration test for full greeter flow in graph in `tests/test_greeter.py`

**Checkpoint**: Greeter integrated into LangGraph pipeline, end-to-end flow works.

---

## Phase 9: Polish & Documentation

**Purpose**: Final validation and documentation

- [X] T053 [P] Run all greeter tests with coverage report (`pytest tests/test_greeter.py --cov`)
- [X] T054 [P] Validate implementation against spec.md checklist
- [X] T055 [P] Follow quickstart.md validation steps
- [ ] T056 Manual testing with real LLM (test conversation flows)
- [X] T057 Code review for constitution compliance (all 5 principles)
- [X] T058 Format code with Black (`black app/agents/greeter.py tests/test_greeter.py`)

**Note**: T056 (manual testing with real LLM) requires OPENAI_API_KEY to be set and can be done separately. All other tasks complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all increments
- **Increments 1-5 (Phases 3-7)**: Each depends on previous increment
  - INC1 (Basic + Welcome): Depends on Foundational
  - INC2 (Field Extraction): Depends on INC1
  - INC3 (Verification): Depends on INC2
  - INC4 (Authentication): Depends on INC3
  - INC5 (Guardrails + Polish): Depends on INC4
- **Integration (Phase 8)**: Depends on INC5 completion
- **Polish (Phase 9)**: Depends on Integration

### Within Each Increment

- Tests MUST be written and FAIL before implementation
- Implementation tasks must be completed in order (no [P] within increment implementation)
- Increment checkpoint validates before moving to next

### Parallel Opportunities

- Phase 1: All setup tasks can run in parallel
- Phase 2: T004, T005, T006 can run in parallel with different files
- Within each increment: All test tasks marked [P] can run together
- Phase 9: T053, T054, T055 can run in parallel

---

## Parallel Example: Increment 1 Tests

```bash
# Launch all tests for Increment 1 together:
pytest tests/test_greeter.py::test_welcome_message tests/test_greeter.py::test_guardrail_rejection -v
```

---

## Implementation Strategy

### MVP First (Increment 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: Increment 1 (Basic + Welcome)
4. **STOP and VALIDATE**: Test welcome message and guardrail rejection
5. Can demo basic agent interaction

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add INC1 (Welcome) → Test independently → Basic agent works
3. Add INC2 (Field Extraction) → Test independently → Can collect info
4. Add INC3 (Verification) → Test independently → Can verify identity
5. Add INC4 (Authentication) → Test independently → Full flow works
6. Add INC5 (Guardrails) → Test independently → Production-ready
7. Integration + Polish → Ready for deployment

Each increment adds capability without breaking previous functionality.

### Test-Driven Development

Follow TDD for each increment:
1. Write tests for increment (ensure they FAIL)
2. Implement increment functionality
3. Run tests (ensure they PASS)
4. Refactor if needed
5. Move to next increment

---

## Summary

**Total Tasks**: 58 tasks across 9 phases
**Task Breakdown**:
- Setup: 3 tasks
- Foundational: 3 tasks (BLOCKING)
- Increment 1 (Basic + Welcome): 8 tasks (2 tests + 6 impl)
- Increment 2 (Field Extraction): 8 tasks (3 tests + 5 impl)
- Increment 3 (Verification): 9 tasks (4 tests + 5 impl)
- Increment 4 (Authentication): 8 tasks (4 tests + 4 impl)
- Increment 5 (Guardrails + Polish): 7 tasks (3 tests + 4 impl)
- Integration: 5 tasks
- Polish: 6 tasks

**Parallel Opportunities**: ~15 tasks can run in parallel (all marked with [P])
**Test Tasks**: 18 tests covering all increments
**Estimated Completion**: 1-2 days for single developer following incremental approach

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (Increment 1) = Basic welcome and guardrail handling
**Full Feature**: All phases complete = Production-ready Greeter Agent integrated into LangGraph pipeline

**Independent Testing**: Each increment has clear checkpoint and can be validated independently before proceeding to next increment.
