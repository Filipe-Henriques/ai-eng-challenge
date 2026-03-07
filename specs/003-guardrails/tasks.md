# Tasks: Guardrails System

**Feature**: Guardrails System  
**Branch**: `003-guardrails`  
**Input**: Design documents from `/specs/003-guardrails/` (plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. All three user stories are P1 priority as they represent core safety checks required for system operation.

**Tests**: Included - guardrails are safety-critical and require comprehensive test coverage with mocked LLM calls.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Initialize guardrails module structure per constitution Section 4

- [ ] T001 Create directory structure: `app/guardrails/` with `__init__.py`
- [ ] T002 Create test file: `tests/test_guardrails.py`
- [ ] T003 Add OpenAI SDK dependency to `requirements.txt` (openai>=1.0.0)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model and constants that ALL user stories depend on

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete

- [ ] T004 Define `GuardrailResult` Pydantic model in `app/guardrails/guardrails.py` with fields: `is_safe: bool`, `blocked_reason: str | None`, `safe_response: str | None`, `sanitised_response: str`
- [ ] T005 Add Pydantic field validators to `GuardrailResult` ensuring consistency between `is_safe` flag and blocking fields
- [ ] T006 [P] Define pre-defined message constants in `app/guardrails/guardrails.py`: `OFF_TOPIC_REFUSAL`, `TOXICITY_WARNING`, `ERROR_MESSAGE`
- [ ] T007 [P] Add Google Style docstring to `GuardrailResult` model explaining purpose and usage
- [ ] T008 [P] Unit test for `GuardrailResult` model validation in `tests/test_guardrails.py` (test field consistency)

**Checkpoint**: Foundation ready - GuardrailResult model is defined and validated. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Toxic Language Protection (Priority: P1) 🎯

**Goal**: Detect and block toxic, abusive, or threatening language to protect employees and maintain professional standards

**Independent Test**: Submit messages with profanity/threats and verify they are blocked with warning message; submit normal banking queries and verify they proceed

### Implementation for User Story 1

- [ ] T009 [P] [US1] Implement `check_toxicity(message: str) -> str | None` function in `app/guardrails/guardrails.py`
- [ ] T010 [US1] Create system prompt for toxicity classification (strict binary "safe"/"toxic" output) in `check_toxicity()`
- [ ] T011 [US1] Implement OpenAI `gpt-4o-mini` API call in `check_toxicity()` with temperature=0, max_tokens=10
- [ ] T012 [US1] Add 5-second timeout to OpenAI call in `check_toxicity()`
- [ ] T013 [US1] Implement response parsing: return `TOXICITY_WARNING` if "toxic", `None` if "safe"
- [ ] T014 [US1] Add try-except block to catch OpenAI errors and timeouts (fail-closed behavior)
- [ ] T015 [US1] Add Google Style docstring to `check_toxicity()` with examples

### Tests for User Story 1

- [ ] T016 [P] [US1] Unit test: Mock LLM to return "toxic" and verify `check_toxicity()` returns warning message in `tests/test_guardrails.py`
- [ ] T017 [P] [US1] Unit test: Mock LLM to return "safe" and verify `check_toxicity()` returns `None` in `tests/test_guardrails.py`
- [ ] T018 [P] [US1] Unit test: Mock LLM to raise timeout exception and verify `check_toxicity()` returns error message (fail-closed) in `tests/test_guardrails.py`
- [ ] T019 [P] [US1] Integration test: Test `check_toxicity()` with real API call using sample toxic messages in `tests/test_guardrails.py`

**Checkpoint**: Toxic language detection is fully functional. Messages with profanity/threats are blocked, normal messages proceed.

---

## Phase 4: User Story 2 - Topic Boundary Enforcement (Priority: P1)

**Goal**: Recognize and politely decline off-topic requests to ensure support resources focus on banking services

**Independent Test**: Submit off-topic requests (coding help, politics, unrelated services) and verify polite refusal; submit banking queries and verify recognition as on-topic

### Implementation for User Story 2

- [ ] T020 [P] [US2] Implement `check_topic(message: str) -> str | None` function in `app/guardrails/guardrails.py`
- [ ] T021 [US2] Create system prompt for topic classification defining banking scope (accounts, loans, cards, transfers, balance, IBAN, transactions, fraud) in `check_topic()`
- [ ] T022 [US2] Implement OpenAI `gpt-4o-mini` API call in `check_topic()` with temperature=0, max_tokens=10
- [ ] T023 [US2] Add 5-second timeout to OpenAI call in `check_topic()`
- [ ] T024 [US2] Implement response parsing: return `OFF_TOPIC_REFUSAL` if "off_topic", `None` if "on_topic"
- [ ] T025 [US2] Add try-except block to catch OpenAI errors and timeouts (fail-closed behavior)
- [ ] T026 [US2] Add Google Style docstring to `check_topic()` with examples

### Tests for User Story 2

- [ ] T027 [P] [US2] Unit test: Mock LLM to return "off_topic" and verify `check_topic()` returns refusal message in `tests/test_guardrails.py`
- [ ] T028 [P] [US2] Unit test: Mock LLM to return "on_topic" and verify `check_topic()` returns `None` in `tests/test_guardrails.py`
- [ ] T029 [P] [US2] Unit test: Mock LLM to raise timeout exception and verify `check_topic()` returns error message (fail-closed) in `tests/test_guardrails.py`
- [ ] T030 [P] [US2] Integration test: Test `check_topic()` with real API call using sample off-topic and banking messages in `tests/test_guardrails.py`

**Checkpoint**: Topic filtering is fully functional. Off-topic requests are politely declined, banking queries proceed normally.

---

## Phase 5: User Story 3 - PII Leakage Prevention (Priority: P1)

**Goal**: Prevent sensitive customer information (phone numbers, IBANs) from being exposed to unverified users

**Independent Test**: Simulate responses containing phone/IBAN to unauthenticated users and verify redaction with `[REDACTED]`; verify authenticated users receive complete information

### Implementation for User Story 3

- [ ] T031 [P] [US3] Implement `check_pii(response: str, is_authenticated: bool) -> str` function in `app/guardrails/guardrails.py`
- [ ] T032 [US3] Compile regex pattern for phone numbers: `r'\+?[0-9\s\-\(\)]{7,15}'` at module level
- [ ] T033 [US3] Compile regex pattern for IBANs: `r'[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}'` at module level
- [ ] T034 [US3] Implement early return: if `is_authenticated=True`, return `response` unchanged
- [ ] T035 [US3] Apply `re.sub()` to replace all phone number matches with `[REDACTED]`
- [ ] T036 [US3] Apply `re.sub()` to replace all IBAN matches with `[REDACTED]`
- [ ] T037 [US3] Return sanitized response string
- [ ] T038 [US3] Add Google Style docstring to `check_pii()` with examples

### Tests for User Story 3

- [ ] T039 [P] [US3] Unit test: Verify `check_pii()` with phone number and `is_authenticated=False` returns `[REDACTED]` in `tests/test_guardrails.py`
- [ ] T040 [P] [US3] Unit test: Verify `check_pii()` with IBAN and `is_authenticated=False` returns `[REDACTED]` in `tests/test_guardrails.py`
- [ ] T041 [P] [US3] Unit test: Verify `check_pii()` with phone number and `is_authenticated=True` returns original in `tests/test_guardrails.py`
- [ ] T042 [P] [US3] Unit test: Verify `check_pii()` with IBAN and `is_authenticated=True` returns original in `tests/test_guardrails.py`
- [ ] T043 [P] [US3] Unit test: Verify `check_pii()` with multiple PII instances all get redacted in `tests/test_guardrails.py`
- [ ] T044 [P] [US3] Unit test: Verify `check_pii()` with no PII returns response unchanged in `tests/test_guardrails.py`
- [ ] T045 [P] [US3] Integration test: Test `check_pii()` with various international phone formats (E.164) in `tests/test_guardrails.py`
- [ ] T046 [P] [US3] Integration test: Test `check_pii()` with various IBAN formats from different European countries in `tests/test_guardrails.py`

**Checkpoint**: PII protection is fully functional. Sensitive data is redacted for unauthenticated users, visible for authenticated users.

---

## Phase 6: Integration (Orchestration)

**Purpose**: Compose all three checks into single orchestrator function with short-circuit evaluation

**⚠️ CRITICAL**: This phase integrates all three user stories into the public API that agents will call

- [ ] T047 Implement `run_guardrails(message: str, proposed_response: str, is_authenticated: bool) -> GuardrailResult` function in `app/guardrails/guardrails.py`
- [ ] T048 Call `check_toxicity(message)` first in `run_guardrails()`; if returns message, return `GuardrailResult(is_safe=False, blocked_reason="toxic", safe_response=<msg>, sanitised_response="")`
- [ ] T049 Call `check_topic(message)` second in `run_guardrails()`; if returns message, return `GuardrailResult(is_safe=False, blocked_reason="off_topic", safe_response=<msg>, sanitised_response="")`
- [ ] T050 Call `check_pii(proposed_response, is_authenticated)` last in `run_guardrails()`
- [ ] T051 Return `GuardrailResult(is_safe=True, blocked_reason=None, safe_response=None, sanitised_response=<sanitized>)` from `run_guardrails()`
- [ ] T052 Wrap entire `run_guardrails()` in try-except to catch unexpected exceptions and return error `GuardrailResult`
- [ ] T053 Add Google Style docstring to `run_guardrails()` with comprehensive examples per contract specification
- [ ] T054 Export `run_guardrails` and `GuardrailResult` from `app/guardrails/__init__.py`

### Integration Tests

- [ ] T055 [P] Integration test: Verify `run_guardrails()` with toxic message short-circuits before topic check in `tests/test_guardrails.py`
- [ ] T056 [P] Integration test: Verify `run_guardrails()` with off-topic message short-circuits before PII check in `tests/test_guardrails.py`
- [ ] T057 [P] Integration test: Verify `run_guardrails()` with safe message runs all checks and returns sanitized response in `tests/test_guardrails.py`
- [ ] T058 [P] Integration test: Verify `run_guardrails()` handles concurrent calls correctly in `tests/test_guardrails.py`
- [ ] T059 [P] Integration test: End-to-end test with real LLM calls for all three scenarios (toxic, off-topic, PII) in `tests/test_guardrails.py`

**Checkpoint**: All user stories are integrated. Orchestrator handles priority ordering and returns unified results.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Non-functional requirements, documentation, and production readiness

- [ ] T060 [P] Add basic metrics logging to `run_guardrails()`: emit block count by type (toxic, off_topic), PII redaction count, latency
- [ ] T061 [P] Add error rate metric to `run_guardrails()` for monitoring guardrail failures
- [ ] T062 [P] Verify no message content is logged in any function (privacy requirement)
- [ ] T063 [P] Performance test: Verify p95 latency <500ms for `run_guardrails()` with mocked LLM in `tests/test_guardrails.py`
- [ ] T064 [P] Performance test: Verify average latency <200ms for `run_guardrails()` with mocked LLM in `tests/test_guardrails.py`
- [ ] T065 [P] Add module-level docstring to `app/guardrails/guardrails.py` explaining purpose and architecture
- [ ] T066 [P] Verify all functions follow Google Style docstring format per constitution
- [ ] T067 [P] Format code with Black per constitution Section 5
- [ ] T068 [P] Update README.md with guardrails integration instructions (link to quickstart.md)

---

## Dependencies Between Phases

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundational) ← MUST complete before user stories
  ↓
Phase 3 (US1: Toxicity) ↘
Phase 4 (US2: Topic)    → Phase 6 (Integration) → Phase 7 (Polish)
Phase 5 (US3: PII)     ↗
```

**Parallel Execution Opportunities**:
- Phase 3, 4, 5 can run in parallel after Phase 2 is complete
- Within each phase, tasks marked [P] can run in parallel
- All test tasks within a phase can run in parallel

---

## Execution Strategy

**MVP Scope** (Minimum Viable Product):
- Phase 1 + Phase 2 + Phase 3 + Phase 6 (minimal orchestrator)
- Delivers: Basic toxic language blocking with orchestrator API

**Recommended Incremental Delivery**:
1. **Iteration 1**: Phase 1 → Phase 2 → Phase 3 (Toxic blocking works)
2. **Iteration 2**: Phase 4 (Topic filtering works independently)
3. **Iteration 3**: Phase 5 (PII protection works independently)
4. **Iteration 4**: Phase 6 (All checks integrated in orchestrator)
5. **Iteration 5**: Phase 7 (Production-ready with metrics and docs)

Each iteration delivers independently testable value and can be demonstrated to stakeholders.

---

## Summary

- **Total Tasks**: 68
- **Parallelizable Tasks**: 45 (marked with [P])
- **User Story Distribution**:
  - Setup: 3 tasks
  - Foundational: 5 tasks (blocking)
  - US1 (Toxic): 11 tasks (7 implementation + 4 tests)
  - US2 (Topic): 11 tasks (7 implementation + 4 tests)
  - US3 (PII): 16 tasks (8 implementation + 8 tests)
  - Integration: 13 tasks (8 implementation + 5 tests)
  - Polish: 9 tasks
- **Independent Test Criteria**:
  - US1: After T019, toxic language blocking is fully testable
  - US2: After T030, topic filtering is fully testable
  - US3: After T046, PII protection is fully testable
  - Integration: After T059, all checks work together

**Estimated Effort**: 3-5 days for experienced Python developer with LLM integration experience

**Ready for Implementation**: All design artifacts complete, tasks are actionable and ordered by dependencies.
