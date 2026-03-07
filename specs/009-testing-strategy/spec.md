# Spec: Testing Strategy — DEUS Bank AI Support System

## 1. Description

This spec defines the **comprehensive testing strategy** for the DEUS Bank AI Support System. It covers three layers of testing: unit tests (isolated, mocked), integration tests (component interaction), and end-to-end tests (full pipeline with real LLM calls). All tests live in the `tests/` directory and are run with `pytest`.

## 2. Testing Principles

- **Isolation by default**: Unit tests MUST mock all LLM calls and external dependencies. No real API calls in unit tests.
- **Real LLM for E2E only**: End-to-end tests use real `gpt-4o-mini` calls and are marked with `@pytest.mark.e2e` to allow selective execution.
- **Deterministic assertions**: Tests MUST assert on state fields and response structure, not on the exact wording of LLM-generated text.
- **Fast feedback**: The full unit + integration test suite MUST complete in under 60 seconds.
- **Coverage target**: Aim for >80% code coverage across `app/`.

## 3. Test Structure

```
tests/
├── conftest.py               # Shared fixtures (mock users, mock state, mock LLM)
├── test_models.py            # Unit tests for data models and mock DB
├── test_guardrails.py        # Unit tests for all guardrail checks
├── test_agents.py            # Unit tests for Greeter, Bouncer, Specialist agents
├── test_pipeline.py          # Unit tests for graph routing logic
├── test_api.py               # Integration tests for the FastAPI endpoint
└── test_e2e.py               # End-to-end tests (marked @pytest.mark.e2e)
```

## 4. Shared Fixtures (`conftest.py`)

The following fixtures MUST be defined in `tests/conftest.py` and shared across all test files:

| Fixture | Type | Description |
| :--- | :--- | :--- |
| `mock_user` | `User` | A pre-built `User` object for `user_001` (Alice Martin, standard tier) |
| `mock_vip_user` | `User` | A pre-built `User` object for `user_003` (Charlie Brown, VIP tier) |
| `mock_account` | `Account` | A pre-built `Account` object for `user_001` with a known balance and transactions |
| `base_state` | `GraphState` | A minimal `GraphState` with default values and a single `HumanMessage` |
| `authenticated_state` | `GraphState` | A `GraphState` with `is_authenticated=True`, `verified_user=mock_user`, and `current_agent="bouncer"` |
| `mock_llm_response` | `callable` | A factory that returns a mock LLM response with a given string content |

## 5. Unit Test Specifications

### 5.1 `test_models.py`

| Test | Description | Assertion |
| :--- | :--- | :--- |
| `test_user_creation` | Create a `User` object with valid fields | All fields are set correctly |
| `test_account_creation` | Create an `Account` object with valid fields | All fields are set correctly |
| `test_find_user_2_of_3_name_phone` | Call `find_user_by_details` with correct name and phone | Returns the correct `User` |
| `test_find_user_2_of_3_name_iban` | Call `find_user_by_details` with correct name and IBAN | Returns the correct `User` |
| `test_find_user_2_of_3_phone_iban` | Call `find_user_by_details` with correct phone and IBAN | Returns the correct `User` |
| `test_find_user_1_of_3_fails` | Call `find_user_by_details` with only one correct field | Returns `None` |
| `test_find_user_wrong_fields_fails` | Call `find_user_by_details` with all wrong fields | Returns `None` |

### 5.2 `test_guardrails.py`

| Test | Description | Assertion |
| :--- | :--- | :--- |
| `test_toxicity_detected` | Mock LLM returns `"toxic"` | `check_toxicity` returns the warning message |
| `test_toxicity_safe` | Mock LLM returns `"safe"` | `check_toxicity` returns `None` |
| `test_topic_off_topic` | Mock LLM returns `"off_topic"` | `check_topic` returns the refusal message |
| `test_topic_on_topic` | Mock LLM returns `"on_topic"` | `check_topic` returns `None` |
| `test_pii_phone_redacted` | Pass a response with a phone number, `is_authenticated=False` | Phone is replaced with `[REDACTED]` |
| `test_pii_iban_redacted` | Pass a response with an IBAN, `is_authenticated=False` | IBAN is replaced with `[REDACTED]` |
| `test_pii_authenticated_unchanged` | Pass a response with a phone number, `is_authenticated=True` | Response is returned unchanged |
| `test_guardrails_short_circuit_toxicity` | Mock toxicity check to trigger | `run_guardrails` returns `is_safe=False` without calling topic check |
| `test_guardrails_short_circuit_topic` | Mock topic check to trigger | `run_guardrails` returns `is_safe=False` without calling PII check |
| `test_guardrails_safe_applies_pii` | Both checks pass | `run_guardrails` returns `is_safe=True` with `sanitised_response` |

### 5.3 `test_agents.py`

| Test | Description | Assertion |
| :--- | :--- | :--- |
| `test_greeter_welcome` | First turn with empty state | Response is generated, no fields extracted |
| `test_greeter_extracts_fields` | Mock LLM extracts name and phone | `collected_fields` is updated correctly |
| `test_greeter_verification_success` | 2+ fields provided, mock DB returns user | `verified_user` is set, secret question is asked |
| `test_greeter_verification_failure` | 2+ fields provided, mock DB returns `None` | `verification_attempts` is incremented |
| `test_greeter_secret_answer_correct` | `verified_user` set, correct answer provided | `is_authenticated=True`, `current_agent="bouncer"` |
| `test_greeter_secret_answer_wrong` | `verified_user` set, wrong answer provided | `verification_attempts` incremented |
| `test_greeter_max_attempts` | `verification_attempts=3` | `conversation_ended=True` |
| `test_bouncer_routes_standard` | `verified_user.tier="standard"` | `current_agent="specialist_standard"` |
| `test_bouncer_routes_premium` | `verified_user.tier="premium"` | `current_agent="specialist_premium"` |
| `test_bouncer_routes_vip` | `verified_user.tier="vip"` | `current_agent="specialist_vip"` |
| `test_bouncer_classifies_intent` | Mock LLM returns `account_balance` intent | `customer_intent="account_balance"` |
| `test_bouncer_low_confidence_fallback` | Mock LLM returns confidence `0.3` | `customer_intent="general_inquiry"` |
| `test_specialist_get_balance` | Call `get_account_balance` tool directly | Returns correct balance from mock DB |
| `test_specialist_transfer_success` | Call `transfer_funds` with sufficient balance | Balance deducted, `success=True` |
| `test_specialist_transfer_insufficient` | Call `transfer_funds` with insufficient balance | Balance unchanged, `success=False` |
| `test_specialist_report_lost_card` | Call `report_lost_card` tool directly | `card_blocked=True` in mock DB |

### 5.4 `test_pipeline.py`

| Test | Description | Assertion |
| :--- | :--- | :--- |
| `test_build_graph` | Call `build_graph()` | Returns a compiled graph without error |
| `test_route_greeter_to_bouncer` | `is_authenticated=True` | Returns `"bouncer"` |
| `test_route_greeter_to_end_not_auth` | `is_authenticated=False` | Returns `END` |
| `test_route_greeter_to_end_ended` | `conversation_ended=True` | Returns `END` |
| `test_route_bouncer_standard` | `current_agent="specialist_standard"` | Returns `"specialist_standard"` |
| `test_route_specialist_loop` | `conversation_ended=False` | Returns `current_agent` |
| `test_route_specialist_end` | `conversation_ended=True` | Returns `END` |

### 5.5 `test_api.py`

| Test | Description | Assertion |
| :--- | :--- | :--- |
| `test_health_check` | Call `GET /health` endpoint | Returns 200 status with health status |
| `test_new_session` | Post message without `session_id` | Creates new session, returns valid response |
| `test_existing_session` | Post message with existing `session_id` | Continues conversation, maintains state |
| `test_ended_conversation` | Post to session with `conversation_ended=True` | Returns appropriate end message |
| `test_response_structure` | Validate API response JSON schema | Contains required fields: `response`, `session_id`, `conversation_ended` |
| `test_error_handling` | Trigger internal error in graph invocation | Returns 500 status with error message |

## 6. End-to-End Test Specifications (`test_e2e.py`)

These tests use real LLM calls and are marked `@pytest.mark.e2e`. They MUST be excluded from the default `pytest` run and only executed explicitly with `pytest -m e2e`.

| Test | Scenario | Assertion |
| :--- | :--- | :--- |
| `test_e2e_full_verification_flow` | Simulate a full conversation: provide name + phone → answer secret question → check balance | `is_authenticated=True`, `conversation_ended=True`, final response contains balance info |
| `test_e2e_max_attempts_flow` | Provide wrong details 3 times | `conversation_ended=True` after 3 failures |
| `test_e2e_guardrail_toxicity` | Send a toxic message | Response contains the safety warning, state is unchanged |
| `test_e2e_guardrail_off_topic` | Send an off-topic message | Response contains the refusal message |
| `test_e2e_vip_routing` | Authenticate as VIP user, send a message | `current_agent="specialist_vip"` |

## 7. Test Configuration (`pytest.ini` / `pyproject.toml`)

The following configuration MUST be added to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m not e2e')",
]
testpaths = ["tests"]
```

## 8. Clarifications

- All async tests MUST use `pytest-asyncio` with `asyncio_mode = "auto"` to avoid boilerplate `@pytest.mark.asyncio` decorators.
- The `conftest.py` fixtures MUST use `pytest.fixture` scope appropriately: `mock_user` and `mock_account` can be `scope="session"`, while `base_state` and `authenticated_state` MUST be `scope="function"` to prevent state mutation between tests.
- E2E tests require the `OPENAI_API_KEY` environment variable to be set. They MUST be skipped gracefully if the key is not present.
