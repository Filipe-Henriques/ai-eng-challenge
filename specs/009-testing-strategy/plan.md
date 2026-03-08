# Implementation Plan: Testing Strategy

**Branch**: `009-testing-strategy` | **Date**: March 7, 2026 | **Spec**: [spec.md](spec.md)

## 1. Goal

Implement the full test suite as defined in `spec.md`. The result will be a comprehensive, three-layer test suite covering unit tests, integration tests, and end-to-end tests, all runnable via `pytest`.

## 2. Technical Context

- **Framework**: `pytest` + `pytest-asyncio` with `asyncio_mode = "auto"`.
- **Mocking**: `unittest.mock.patch` and `unittest.mock.MagicMock` for LLM calls and external dependencies.
- **API Testing**: FastAPI `TestClient` for synchronous endpoint tests.
- **E2E Tests**: Real `gpt-4o-mini` calls, marked `@pytest.mark.e2e`, skipped if `OPENAI_API_KEY` is not set.
- **Configuration**: `pyproject.toml` for pytest settings and custom markers.

## 3. Constitution Check

*GATE: Must pass before implementation.*

✓ **Multi-Agent Architecture with LangGraph**: Tests validate the multi-agent pipeline behavior without modifying the architecture.

✓ **Safety First — Guardrails as a Cross-Cutting Concern**: Comprehensive guardrails test coverage ensures safety mechanisms are thoroughly validated.

✓ **Security by Design — Strict Verification**: Tests validate the 2-of-3 verification logic and authentication flow.

✓ **Stateful Conversation History**: Tests validate state management across conversation turns.

✓ **Clean Architecture — Separation of Concerns**: Test structure mirrors the source code organization (`tests/` directory with separate files per component).

**Result**: All principles respected. No violations.

## 4. Task Breakdown

### Task 1: Configure `pyproject.toml`

- **Description**: Add pytest configuration and the `e2e` custom marker.
- **Action**:
  1. Add or update `pyproject.toml` with the following section:
     ```toml
     [tool.pytest.ini_options]
     asyncio_mode = "auto"
     markers = [
         "e2e: marks tests as end-to-end (deselect with '-m not e2e')",
     ]
     testpaths = ["tests"]
     ```
- **Acceptance**: Running `pytest --co` (collect only) lists all tests without warnings about unknown markers.

### Task 2: Implement `tests/conftest.py`

- **Description**: Create all shared fixtures used across the test suite.
- **Action**:
  1. Create `tests/conftest.py`.
  2. Define `mock_user` fixture (`scope="session"`): returns a `User` object for Alice Martin (`user_001`, standard tier) with a known secret question and answer.
  3. Define `mock_vip_user` fixture (`scope="session"`): returns a `User` object for Charlie Brown (`user_003`, VIP tier).
  4. Define `mock_account` fixture (`scope="session"`): returns an `Account` object for `user_001` with a known balance (e.g., `5000.00 EUR`) and 3 pre-defined transactions.
  5. Define `base_state` fixture (`scope="function"`): returns a minimal `GraphState` with all default values and a single `HumanMessage("Hello")`.
  6. Define `authenticated_state` fixture (`scope="function"`): returns a `GraphState` with `is_authenticated=True`, `verified_user=mock_user`, and `current_agent="bouncer"`.
  7. Define `mock_llm_response` fixture: returns a factory function `make_response(content: str)` that creates a mock LLM response object with the given content.
- **Acceptance**: All fixtures are importable and usable in test files without errors.

### Task 3: Implement `tests/test_models.py`

- **Description**: Write all unit tests for data models and the mock database lookup function.
- **Action**:
  1. Create `tests/test_models.py`.
  2. Implement all 7 tests specified in Section 5.1 of the spec.
  3. For `find_user_by_details` tests, use the actual `USERS_DB` from `app.models.database` — no mocking needed as it is in-memory.
- **Acceptance**: All 7 model tests pass.

### Task 4: Implement `tests/test_guardrails.py`

- **Description**: Write all unit tests for the guardrails layer.
- **Action**:
  1. Create `tests/test_guardrails.py`.
  2. For `check_toxicity` and `check_topic` tests, use `unittest.mock.patch` to mock the OpenAI client and return controlled string responses.
  3. For `check_pii` tests, call the function directly — no mocking needed as it is pure regex.
  4. For `run_guardrails` orchestrator tests, mock the individual check functions to verify short-circuit behaviour.
  5. Implement all 10 tests specified in Section 5.2 of the spec.
- **Acceptance**: All 10 guardrail tests pass with mocked LLM calls.

### Task 5: Implement `tests/test_agents.py`

- **Description**: Write all unit tests for the three agents.
- **Action**:
  1. Create `tests/test_agents.py`.
  2. For all agent tests, mock both the LLM calls and `run_guardrails` to return safe, controlled responses.
  3. For Greeter Agent tests, also mock `find_user_by_details`.
  4. For Specialist Agent tool tests (`test_specialist_get_balance`, `test_specialist_transfer_*`, `test_specialist_report_lost_card`), call the tool functions **directly** without mocking — they operate on the in-memory mock DB.
  5. Reset the mock DB state between tool tests using a fixture or setup/teardown to prevent test pollution.
  6. Implement all 17 tests specified in Section 5.3 of the spec.
- **Acceptance**: All 17 agent tests pass.

### Task 6: Implement `tests/test_pipeline.py`

- **Description**: Write all unit tests for the LangGraph routing logic.
- **Action**:
  1. Create `tests/test_pipeline.py`.
  2. Import and test the three routing functions (`route_after_greeter`, `route_after_bouncer`, `route_after_specialist`) directly — they are pure functions with no LLM calls.
  3. For `test_build_graph`, simply assert that `build_graph()` does not raise an exception and returns a non-None object.
  4. Implement all 7 tests specified in Section 5.4 of the spec.
- **Acceptance**: All 7 pipeline tests pass without any mocking.

### Task 7: Implement `tests/test_api.py`

- **Description**: Write integration tests for the FastAPI endpoint.
- **Action**:
  1. Create `tests/test_api.py`.
  2. Use `from fastapi.testclient import TestClient` and `from app.main import app`.
  3. In each test, patch `graph.ainvoke` to return a controlled `GraphState` to avoid real LLM calls.
  4. Use a `setup_function` or fixture to clear `SESSION_STORE` between tests to prevent state leakage.
  5. Implement all 6 integration tests for the API endpoint (health check, new session, existing session, ended conversation, response structure, error handling).
- **Acceptance**: All 6 API integration tests pass with mocked graph invocation.

### Task 8: Implement `tests/test_e2e.py`

- **Description**: Write end-to-end tests that exercise the full pipeline with real LLM calls.
- **Action**:
  1. Create `tests/test_e2e.py`.
  2. Add a session-scoped fixture that skips all E2E tests if `OPENAI_API_KEY` is not set:
     ```python
     import os, pytest
     if not os.getenv("OPENAI_API_KEY"):
         pytest.skip("OPENAI_API_KEY not set", allow_module_level=True)
     ```
  3. Mark all tests in this file with `@pytest.mark.e2e`.
  4. Use the FastAPI `TestClient` (without mocking) to send real HTTP requests through the full pipeline.
  5. Implement all 5 E2E tests specified in Section 6 of the spec.
  6. For `test_e2e_full_verification_flow`, simulate a multi-turn conversation across multiple `POST /chat` calls using the same `session_id`.
- **Acceptance**: All 5 E2E tests pass when run with `pytest -m e2e` and a valid `OPENAI_API_KEY`.

## 5. Next Steps

With the full test suite implemented, the system will have comprehensive test coverage across all layers. The test suite enables:
- **Fast feedback** during development (unit + integration tests < 60 seconds)
- **Confidence in changes** with automated regression detection
- **Production readiness** validation through E2E tests
- **Documentation** of expected behavior through test specifications
