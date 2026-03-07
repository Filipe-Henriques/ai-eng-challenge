# Tasks: Data Models & Mock Database

**Feature**: Data Models & Mock Database  
**Branch**: `001-data-models`  
**Input**: Design documents from `/specs/001-data-models/`  
**Prerequisites**: plan.md, spec.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

---

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Feature Context

**Tech Stack**: Python 3.11+, Pydantic v2, pytest  
**Structure**: Single project (`app/models/`, `tests/`)  
**Files**: schemas.py (models), database.py (mock data + lookups), test_data_models.py

---

## Phase 1: Setup

**Goal**: Initialize project structure for data models

### Tasks

- [X] T001 Create app/ directory in project root
- [X] T002 Create app/models/ directory
- [X] T003 Create tests/ directory in project root
- [X] T004 Create app/models/__init__.py (empty file for Python package)

---

## Phase 2: Foundational

**Goal**: Create base schemas file that all user stories depend on

**Independent Test**: Schemas file can be imported without errors

### Tasks

- [X] T005 Create app/models/schemas.py with Pydantic BaseModel import

---

## Phase 3: User Story 1 - API Data Exchange

**Goal**: Implement ChatRequest and ChatResponse models for API communication

**Priority**: P1  
**Story**: As a developer integrating with the chat API, I need standardized request/response models

**Independent Test**: Can instantiate ChatRequest with session_id and message; ChatResponse with session_id, response, and agent; Pydantic validates required fields

### Implementation Tasks

- [X] T006 [P] [US1] Implement ChatRequest model in app/models/schemas.py (fields: session_id, message)
- [X] T007 [P] [US1] Implement ChatResponse model in app/models/schemas.py (fields: session_id, response, agent)

### Testing Tasks

- [X] T008 [US1] Create tests/test_data_models.py with test_chat_request_valid()
- [X] T009 [US1] Add test_chat_request_missing_field() to tests/test_data_models.py
- [X] T010 [US1] Add test_chat_response_valid() to tests/test_data_models.py
- [X] T011 [US1] Add test_chat_response_missing_field() to tests/test_data_models.py

---

## Phase 4: User Story 2 - Customer Identity Verification

**Goal**: Implement User model and 2-out-of-3 identity verification logic

**Priority**: P1  
**Story**: As a bouncer agent, I need to verify customer identity before granting access

**Independent Test**: Can query User data store with 2 out of 3 fields (name/phone/IBAN) and retrieve matching user; verify secret question and answer

### Implementation Tasks

- [X] T012 [US2] Implement User model in app/models/schemas.py (fields: name, phone, iban, secret, answer)
- [X] T013 [US2] Create app/models/database.py with MOCK_USERS list (Lisa, John, Maria)
- [X] T014 [US2] Implement find_user_by_fields(fields: dict) in app/models/database.py with 2-out-of-3 matching logic

### Testing Tasks

- [X] T015 [US2] Add test_find_user_by_fields_two_matches() to tests/test_data_models.py (name + phone)
- [X] T016 [US2] Add test_find_user_by_fields_three_matches() to tests/test_data_models.py (all fields)
- [X] T017 [US2] Add test_find_user_by_fields_one_match() to tests/test_data_models.py (returns None)
- [X] T018 [US2] Add test_find_user_by_fields_no_match() to tests/test_data_models.py (returns None)
- [X] T019 [US2] Add test_find_user_by_fields_case_insensitive() to tests/test_data_models.py (name: "lisa" matches "Lisa")
- [X] T020 [US2] Add test_user_model_missing_field() to tests/test_data_models.py (Pydantic ValidationError)

---

## Phase 5: User Story 3 - Account Tier Determination

**Goal**: Implement Account model and IBAN-based account lookup

**Priority**: P1  
**Story**: As a specialist agent, I need to check premium status to route customers correctly

**Independent Test**: Can lookup Account by IBAN and retrieve premium status; returns None for users without accounts

### Implementation Tasks

- [X] T021 [US3] Implement Account model in app/models/schemas.py (fields: iban, premium)
- [X] T022 [US3] Add MOCK_ACCOUNTS list to app/models/database.py (Lisa premium=True, John premium=False)
- [X] T023 [US3] Implement find_account_by_iban(iban: str) in app/models/database.py

### Testing Tasks

- [X] T024 [US3] Add test_find_account_by_iban_premium() to tests/test_data_models.py (Lisa's IBAN → premium=True)
- [X] T025 [US3] Add test_find_account_by_iban_regular() to tests/test_data_models.py (John's IBAN → premium=False)
- [X] T026 [US3] Add test_find_account_by_iban_not_found() to tests/test_data_models.py (Maria's IBAN → None)
- [X] T027 [US3] Add test_find_account_by_iban_unknown() to tests/test_data_models.py (invalid IBAN → None)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Ensure code quality, documentation, and comprehensive coverage

### Tasks

- [X] T028 Add Google-style docstrings to all models in app/models/schemas.py
- [X] T029 Add Google-style docstrings to all functions in app/models/database.py
- [X] T030 Add module-level docstrings to schemas.py and database.py
- [X] T031 Run pytest with coverage report (target: 100% of database.py)
- [X] T032 Verify all models can be imported: `from app.models.schemas import User, Account, ChatRequest, ChatResponse`
- [X] T033 Verify all database functions can be imported: `from app.models.database import MOCK_USERS, MOCK_ACCOUNTS, find_user_by_fields, find_account_by_iban`

---

## Dependencies

### Story Completion Order

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational - schemas.py base)
    ↓
Phase 3 (US1), Phase 4 (US2), Phase 5 (US3) ← Can be done independently
    ↓
Phase 6 (Polish)
```

**Critical Path**: Setup → Foundational → US2 (contains security-critical 2-out-of-3 logic)

**Blocking Dependencies**:
- Phase 2 blocks all user story phases (schemas.py must exist)
- T013 (create database.py) must complete before T014 (add find_user_by_fields)
- T022 (add MOCK_ACCOUNTS) depends on T013 (database.py exists)

**Parallel Opportunities**:
- T006 and T007 can run in parallel (different models in same file - use multi-edit)
- T012 can be done in parallel with or after T006/T007
- T021 can be done in parallel with or after T006/T007/T012
- All test tasks within a phase can be written in parallel once implementation is complete

---

## Parallel Execution Examples

### After Phase 2 Completion

**Parallel Group 1 - Model Definitions** (different sections of schemas.py):
- T006 [US1] - ChatRequest model
- T007 [US1] - ChatResponse model  
- T012 [US2] - User model
- T021 [US3] - Account model

**Note**: Use multi-edit or multi_replace_string_in_file for efficiency

### US1 Testing (after T006, T007 complete)

**Parallel Group 2 - US1 Tests**:
- T008 - test_chat_request_valid()
- T009 - test_chat_request_missing_field()
- T010 - test_chat_response_valid()
- T011 - test_chat_response_missing_field()

### US2 Testing (after T012, T013, T014 complete)

**Parallel Group 3 - US2 Tests**:
- T015 - test_find_user_by_fields_two_matches()
- T016 - test_find_user_by_fields_three_matches()
- T017 - test_find_user_by_fields_one_match()
- T018 - test_find_user_by_fields_no_match()
- T019 - test_find_user_by_fields_case_insensitive()
- T020 - test_user_model_missing_field()

### US3 Testing (after T021, T022, T023 complete)

**Parallel Group 4 - US3 Tests**:
- T024 - test_find_account_by_iban_premium()
- T025 - test_find_account_by_iban_regular()
- T026 - test_find_account_by_iban_not_found()
- T027 - test_find_account_by_iban_unknown()

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**MVP = User Story 2 ONLY** (Customer Identity Verification)

**Rationale**: US2 contains the security-critical 2-out-of-3 verification logic mandated by the constitution. This is the core requirement.

**MVP Tasks**: T001-T005 (Setup/Foundation) + T012-T020 (US2 complete)

**MVP Deliverables**:
- User model with all required fields
- MOCK_USERS with 3 test users
- find_user_by_fields with 2-out-of-3 logic
- 6 comprehensive tests proving security requirement works

### Incremental Delivery Plan

1. **Iteration 1 (MVP)**: US2 - Identity Verification
   - Delivers core security functionality
   - Independently testable and demonstrable
   - Blocks: No agents can verify users yet

2. **Iteration 2**: US1 - API Data Exchange
   - Adds ChatRequest/ChatResponse for API layer
   - Independently testable
   - Enables API endpoint development

3. **Iteration 3**: US3 - Account Tier Determination
   - Adds Account model and lookup
   - Enables premium/regular routing
   - Independently testable

4. **Iteration 4**: Polish & Integration
   - Documentation, coverage, final validation

### Recommended Development Order

**For full feature implementation**:

1. **Setup (Phase 1-2)**: T001-T005 - Create structure
2. **All Models (Parallel)**: T006, T007, T012, T021 - Implement all 4 models in schemas.py
3. **Database Foundation**: T013 - Create database.py with MOCK_USERS
4. **US2 Implementation**: T014 - Add find_user_by_fields (security-critical)
5. **US2 Testing**: T015-T020 - Validate 2-out-of-3 logic thoroughly
6. **US3 Implementation**: T022-T023 - Add accounts and lookup
7. **US3 Testing**: T024-T027 - Validate account lookup
8. **US1 Testing**: T008-T011 - Validate API models
9. **Polish**: T028-T033 - Documentation and final checks

**Estimated Time**: 4-6 hours total
- Setup: 15 min
- Models: 1 hour
- Database + lookups: 1.5 hours
- Tests: 2 hours
- Polish: 30-45 min

---

## Task Summary

**Total Tasks**: 33  
**By Phase**:
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 1 task
- Phase 3 (US1 - API Data Exchange): 6 tasks (2 implementation + 4 tests)
- Phase 4 (US2 - Identity Verification): 9 tasks (3 implementation + 6 tests)
- Phase 5 (US3 - Account Tier): 7 tasks (3 implementation + 4 tests)
- Phase 6 (Polish): 6 tasks

**By Type**:
- Setup/Infrastructure: 5 tasks (T001-T005)
- Model Implementation: 4 tasks (T006, T007, T012, T021)
- Database Implementation: 4 tasks (T013, T014, T022, T023)
- Tests: 17 tasks (T008-T011, T015-T020, T024-T027)
- Documentation/Polish: 6 tasks (T028-T033)

**Parallelization Potential**: 20 tasks can run in parallel groups (60% of tasks)

**Independent Test Criteria Met**:
- ✅ US1: ChatRequest/ChatResponse validate correctly
- ✅ US2: 2-out-of-3 verification returns correct user, rejects insufficient matches
- ✅ US3: Account lookup by IBAN returns correct premium status, None for non-accounts

---

## Format Validation

✅ **All tasks follow checklist format**: `- [ ] [TaskID] [P?] [Story?] Description with file path`  
✅ **Task IDs**: Sequential T001-T033  
✅ **Story labels**: [US1], [US2], [US3] applied correctly to user story phases  
✅ **Parallel markers**: [P] applied to T006, T007 (can edit same file independently)  
✅ **File paths**: All tasks include specific file paths  
✅ **Setup/Foundational**: No story labels (correct)  
✅ **Polish phase**: No story labels (correct)

---

**End of Tasks Document**