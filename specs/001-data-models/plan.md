# Implementation Plan: Data Models & Mock Database

**Branch**: `001-data-models` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-data-models/spec.md`

## Summary

Implement all Pydantic data models and the mock in-memory database as the foundation for the DEUS Bank AI Support System. This includes four core models (User, Account, ChatRequest, ChatResponse) and two helper functions for identity verification and account lookup. These models serve as the single source of truth for data structures across all agents, guardrails, and the API layer.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic v2, FastAPI (for data models), pytest + pytest-asyncio (testing)  
**Storage**: In-memory (mock data, no persistence)  
**Testing**: pytest with 100% coverage target for database.py module  
**Target Platform**: Linux server / containerized environment  
**Project Type**: Web service (AI-powered customer support system)  
**Performance Goals**: Model instantiation <1ms per instance, O(n) lookup acceptable for mock data  
**Constraints**: Clean architecture - no business logic in models, pure data definitions only  
**Scale/Scope**: 3 mock users, 2 mock accounts (development/testing scope)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle V: Clean Architecture — Separation of Concerns

**Requirement**: Models in `app/models/`, no business logic

**Compliance**: 
- ✅ Models will be placed in `app/models/schemas.py` (Pydantic definitions only)
- ✅ Database in `app/models/database.py` (mock data + lookup helpers)
- ✅ No agent logic, no business rules, no computation in models
- ✅ Lookup functions (`find_user_by_fields`, `find_account_by_iban`) are data access only

**Verdict**: PASS - Clean separation maintained

### ✅ Principle III: Security by Design — Strict Verification

**Requirement**: 2-out-of-3 field matching for identity verification

**Compliance**: 
- ✅ `find_user_by_fields` implements exactly the 2-out-of-3 logic mandated by constitution
- ✅ Function is critical and will be thoroughly tested (5+ test cases)

**Verdict**: PASS - Core security requirement properly implemented in data layer

### ✅ Technology Stack: Pydantic v2

**Requirement**: Use Pydantic v2 for data validation

**Compliance**: 
- ✅ All models use Pydantic v2 BaseModel
- ✅ Native validation for required fields

**Verdict**: PASS - Full alignment with technology stack

**GATE STATUS: ✅ ALL CHECKS PASSED - Proceed to Phase 0**

## Project Structure

### Documentation (this feature)

```text
specs/001-data-models/
├── plan.md              # This file
├── data-model.md        # Phase 1 output (detailed model documentation)
└── tasks.md             # Phase 2 output (via /speckit.tasks command)
```

Note: research.md not needed - all requirements clear from spec
Note: contracts/ not applicable - internal data models, not external API contracts
Note: quickstart.md not needed - this is foundational data layer, no standalone usage

### Source Code (this feature)

```text
app/
├── models/
│   ├── __init__.py          # (create if needed)
│   ├── schemas.py           # Task 1: Pydantic models (User, Account, ChatRequest, ChatResponse)
│   └── database.py          # Task 2-4: Mock data + lookup functions

tests/
└── test_data_models.py      # Task 5: Unit tests for models and database
```

**Structure Decision**: Single-project structure following constitution Principle V. The `app/models/` directory contains pure data definitions with no business logic. Tests follow pytest conventions in the `tests/` directory root.

## Phase 0: Research

**Status**: ⏭️ SKIPPED - No NEEDS CLARIFICATION items

All technical decisions are clear:
- Pydantic v2 usage is mandated by constitution
- Mock in-memory database is specified in requirements
- 2-out-of-3 verification logic is defined in constitution
- Project structure follows constitution Section 4

## Phase 1: Design & Implementation Details

### Data Model Definitions

See [data-model.md](data-model.md) for complete model schemas and field specifications.

**Summary**:
- **User**: 5 fields (name, phone, iban, secret, answer) - represents registered customers
- **Account**: 2 fields (iban, premium) - represents bank accounts
- **ChatRequest**: 2 fields (session_id, message) - API input
- **ChatResponse**: 3 fields (session_id, response, agent) - API output

### Implementation Task Breakdown

#### Task 1: Implement Pydantic Models (`app/models/schemas.py`)

**File**: `app/models/schemas.py`

**Action**:
1. Create `app/models/schemas.py`
2. Import `BaseModel` from `pydantic`
3. Define `User` model with fields: `name: str`, `phone: str`, `iban: str`, `secret: str`, `answer: str`
4. Define `Account` model with fields: `iban: str`, `premium: bool`
5. Define `ChatRequest` model with fields: `session_id: str`, `message: str`
6. Define `ChatResponse` model with fields: `session_id: str`, `response: str`, `agent: str`

**Acceptance**: 
- All models importable: `from app.models.schemas import User, Account, ChatRequest, ChatResponse`
- Models instantiate correctly with all required fields
- Pydantic raises `ValidationError` for missing fields

#### Task 2: Implement Mock Database (`app/models/database.py`)

**File**: `app/models/database.py`

**Action**:
1. Create `app/models/database.py`
2. Import `User` and `Account` from `schemas.py`
3. Define `MOCK_USERS` list with 3 User objects:
   - Lisa: phone `+1122334455`, iban `DE89370400440532013000`, secret "Which is the name of my dog?", answer "Yoda"
   - John: phone `+1987654321`, iban `GB29NWBK60161331926819`, secret "What is your mother's maiden name?", answer "Smith"
   - Maria: phone `+1555000111`, iban `FR7630006000011234567890189`, secret "What was the name of your first pet?", answer "Fluffy"
4. Define `MOCK_ACCOUNTS` list with 2 Account objects:
   - Lisa's IBAN → premium=True
   - John's IBAN → premium=False
   - (Maria intentionally has no account for testing)

**Acceptance**: 
- Module importable: `from app.models.database import MOCK_USERS, MOCK_ACCOUNTS`
- `len(MOCK_USERS) == 3`
- `len(MOCK_ACCOUNTS) == 2`
- One account has `premium=True`, one has `premium=False`

#### Task 3: Implement `find_user_by_fields`

**File**: `app/models/database.py`

**Function Signature**: `find_user_by_fields(fields: dict) -> User | None`

**Action**:
1>. Add function to `database.py`
2. Accept a dict with optional keys: `name`, `phone`, `iban`
3. Iterate over `MOCK_USERS`
4. For each user, count matches:
   - If `name` in fields: compare case-insensitive (`fields['name'].lower() == user.name.lower()`)
   - If `phone` in fields: compare exact (`fields['phone'] == user.phone`)
   - If `iban` in fields: compare exact (`fields['iban'] == user.iban`)
5. If match count >= 2, return that user immediately
6. If no user matches, return None

**Acceptance**:
- ✅ `find_user_by_fields({"name": "Lisa", "phone": "+1122334455"})` → returns Lisa's User object
- ✅ `find_user_by_fields({"name": "lisa", "phone": "+1122334455"})` → returns Lisa (case-insensitive name)
- ✅ `find_user_by_fields({"phone": "+1122334455", "iban": "DE89370400440532013000"})` → returns Lisa
- ✅ `find_user_by_fields({"name": "Lisa", "phone": "WRONG"})` → returns None (only 1 match)
- ✅ `find_user_by_fields({"name": "Unknown", "phone": "000", "iban": "000"})` → returns None
- ✅ `find_user_by_fields({"name": "John", "phone": "+1987654321", "iban": "GB29NWBK60161331926819"})` → returns John (3/3 match)

**Critical**: This function implements Constitution Principle III (2-out-of-3 verification)

#### Task 4: Implement `find_account_by_iban`

**File**: `app/models/database.py`

**Function Signature**: `find_account_by_iban(iban: str) -> Account | None`

**Action**:
1. Add function to `database.py`
2. Iterate over `MOCK_ACCOUNTS`
3. Return first account where `account.iban == iban`
4. Return None if no match found

**Acceptance**:
- ✅ `find_account_by_iban("DE89370400440532013000")` → returns Account with `premium=True` (Lisa)
- ✅ `find_account_by_iban("GB29NWBK60161331926819")` → returns Account with `premium=False` (John)
- ✅ `find_account_by_iban("FR7630006000011234567890189")` → returns None (Maria has no account)
- ✅ `find_account_by_iban("UNKNOWN")` → returns None

#### Task 5: Write Unit Tests (`tests/test_data_models.py`)

**File**: `tests/test_data_models.py`

**Action**:
1. Create `tests/test_data_models.py`
2. Test `find_user_by_fields`:
   - Test 2-field match returns correct user
   - Test 3-field match returns correct user
   - Test 1-field match returns None
   - Test 0-field match returns None
   - Test case-insensitive name matching
   - Test all 3 users can be found with correct combinations
3. Test `find_account_by_iban`:
   - Test Lisa's IBAN returns premium account
   - Test John's IBAN returns non-premium account
   - Test Maria's IBAN returns None
   - Test invalid IBAN returns None
4. Test Pydantic validation:
   - Test ChatRequest with missing `message` raises ValidationError
   - Test User with missing field raises ValidationError

**Acceptance**: 
- All tests pass
- 100% code coverage of `database.py` module
- Minimum 10 test cases covering all acceptance criteria

## Post-Phase 1 Constitution Check

*Re-evaluate after design phase*

### ✅ Clean Architecture - Verified

**Review**: 
- Models in `app/models/schemas.py` contain only Pydantic field definitions
- Database module contains only data and simple lookup functions
- No agent logic, no business rules, no LLM calls
- Lookup functions are pure data access (no side effects)

**Verdict**: ✅ PASS - Clean architecture maintained

### ✅ Security Implementation - Verified

**Review**:
- `find_user_by_fields` correctly implements 2-of-3 matching
- Name comparison is case-insensitive (security consideration)
- Function will be tested with 6+ scenarios (comprehensive coverage)

**Verdict**: ✅ PASS - Security requirement properly implemented

**FINAL GATE STATUS: ✅ ALL CHECKS PASSED - Ready for implementation**

## Next Steps

1. **Implementation**: Run `/speckit.tasks` to generate tasks.md with actionable task list
2. **After Implementation**: Proceed to `spec-graph-state.md` to define LangGraph State object
3. **Integration**: These models will be imported by agents, guardrails, and API endpoints

## Notes

- This is a foundational feature - all other features depend on these models
- The 2-out-of-3 verification logic in Task 3 is security-critical
- Mock data includes deliberate test scenarios: premium (Lisa), regular (John), no-account (Maria)
- No external API contracts needed - these are internal data models
