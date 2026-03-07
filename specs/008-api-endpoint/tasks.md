# Tasks: API Endpoint

**Feature Branch**: `008-api-endpoint`  
**Input**: Design documents from `specs/008-api-endpoint/`  
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/api-contract.md](contracts/api-contract.md), [quickstart.md](quickstart.md)

**Note**: This feature is infrastructure (HTTP API layer), not user-story based. Tasks are organized by implementation phases.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

This project uses single project structure with `app/` for source and `tests/` for tests.

---

## Phase 1: Data Models

**Purpose**: Update existing Pydantic models to match API contract

- [X] T001 Update ChatResponse model in app/models/schemas.py to rename field `agent` to `current_agent`
- [X] T002 Add `is_authenticated: bool` field to ChatResponse model in app/models/schemas.py
- [X] T003 Add `conversation_ended: bool` field to ChatResponse model in app/models/schemas.py
- [X] T004 Update ChatResponse docstring and field descriptions in app/models/schemas.py

**Checkpoint**: ChatResponse model has all 5 required fields (session_id, response, current_agent, is_authenticated, conversation_ended) and imports without errors

---

## Phase 2: API Module Structure

**Purpose**: Create the API module directory structure per constitution

- [X] T005 Create app/api/ directory with app/api/__init__.py
- [X] T006 Create app/api/v1/ directory with app/api/v1/__init__.py
- [X] T007 Create app/api/v1/endpoints/ directory with app/api/v1/endpoints/__init__.py

**Checkpoint**: API module structure exists and can be imported, follows constitution Section 4

---

## Phase 3: Chat Router Implementation

**Purpose**: Implement the POST /chat endpoint with session management

- [X] T008 Create app/api/v1/endpoints/chat.py with module imports (APIRouter, HTTPException, HumanMessage, AIMessage, logging)
- [X] T009 Add imports for ChatRequest, ChatResponse from app.models.schemas in app/api/v1/endpoints/chat.py
- [X] T010 Add imports for State from app.graph.state and graph from app.graph.pipeline in app/api/v1/endpoints/chat.py
- [X] T011 Define module-level SESSION_STORE: dict[str, State] = {} in app/api/v1/endpoints/chat.py
- [X] T012 Instantiate router = APIRouter() in app/api/v1/endpoints/chat.py
- [X] T013 Implement create_initial_state(session_id: str) -> State function in app/api/v1/endpoints/chat.py
- [X] T014 Implement async chat_endpoint(request: ChatRequest) -> ChatResponse function with @router.post("/chat") decorator in app/api/v1/endpoints/chat.py
- [X] T015 Add session loading/creation logic (check SESSION_STORE, create if missing) in chat_endpoint
- [X] T016 Add conversation_ended guard (return termination message without invoking graph) in chat_endpoint
- [X] T017 Add message appending logic (append HumanMessage to state["messages"]) in chat_endpoint
- [X] T018 Add graph invocation with try-except (await graph.ainvoke(state), raise HTTPException on error) in chat_endpoint
- [X] T019 Add state saving logic (store updated state in SESSION_STORE) in chat_endpoint
- [X] T020 Add response extraction logic (get last AIMessage with validation, build ChatResponse, raise HTTPException if not AIMessage) in chat_endpoint
- [X] T021 Add error logging for graph failures and invalid message types in chat_endpoint
- [X] T022 Add Google Style docstrings to all functions in app/api/v1/endpoints/chat.py

**Checkpoint**: Chat router exports router with POST /chat endpoint, session management works, graph invocation wrapped in error handling

---

## Phase 4: Application Entry Point

**Purpose**: Create the FastAPI app and wire up routers

- [X] T023 Create app/main.py with FastAPI import
- [X] T024 Import chat router from app.api.v1.endpoints.chat in app/main.py
- [X] T025 Create FastAPI app instance with title="DEUS Bank AI Support" and version="1.0.0" in app/main.py
- [X] T026 Include chat router with app.include_router(router, prefix="", tags=["chat"]) in app/main.py
- [X] T027 [P] Implement GET /health endpoint that returns {"status": "ok"} in app/main.py
- [X] T028 [P] Add if __name__ == "__main__": block with uvicorn.run() for local development in app/main.py
- [X] T029 [P] Add module docstring and Google Style docstrings to app/main.py

**Checkpoint**: Running `uvicorn app.main:app` starts the server, GET /health returns 200, POST /chat is accessible

---

## Phase 5: Integration Tests

**Purpose**: Verify endpoint behavior with mocked graph

- [X] T030 Create tests/test_api.py with imports (TestClient, AsyncMock, pytest, time)
- [X] T031 Add fixture for TestClient(app) in tests/test_api.py
- [X] T032 Add autouse fixture to clear SESSION_STORE before/after each test in tests/test_api.py
- [X] T033 [P] Write test_health_check() to verify GET /health returns 200 and {"status": "ok"} in tests/test_api.py
- [X] T034 [P] Write test_new_session() to verify POST /chat creates new session with default state in tests/test_api.py
- [X] T035 [P] Write test_existing_session() to verify POST /chat reuses and updates existing session in tests/test_api.py
- [X] T036 [P] Write test_ended_conversation() to verify endpoint returns termination message without invoking graph in tests/test_api.py
- [X] T037 [P] Write test_validation_error_empty_message() to verify empty message returns 422 in tests/test_api.py
- [X] T038 [P] Write test_validation_error_missing_field() to verify missing field returns 422 in tests/test_api.py
- [X] T039 [P] Write test_graph_invocation_error() to verify graph errors return 500 with generic message in tests/test_api.py
- [X] T040 [P] Write test_invalid_message_type() to verify non-AIMessage last message returns 500 in tests/test_api.py
- [X] T041 [P] Write test_response_structure() to verify ChatResponse contains all required fields in tests/test_api.py
- [X] T042 [P] Write test_session_state_persistence() to verify state persists across multiple requests in tests/test_api.py
- [X] T043 [P] Write test_message_history_accumulation() to verify messages list grows with each turn in tests/test_api.py
- [X] T044 [P] Write test_response_performance() to verify response time <5 seconds with mocked graph in tests/test_api.py

**Checkpoint**: All API tests pass (pytest tests/test_api.py -v), endpoint behavior verified with mocked graph, performance requirement validated

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Data Models (Phase 1)**: No dependencies - start here
2. **API Module Structure (Phase 2)**: Can run in parallel with Phase 1
3. **Chat Router Implementation (Phase 3)**: Depends on Phase 1 and Phase 2 completion
4. **Application Entry Point (Phase 4)**: Depends on Phase 3 completion
5. **Integration Tests (Phase 5)**: Can start after Phase 4 completion

### Within Each Phase

**Phase 1**: Sequential order:
- T001 (rename field) → T002 (add field) → T003 (add field) → T004 (update docs)

**Phase 2**: Sequential order:
- T005 (create app/api/) → T006 (create app/api/v1/) → T007 (create app/api/v1/endpoints/)

**Phase 3**: Sequential order:
- T008-T012 (imports and setup) → T013 (create_initial_state) → T014 (endpoint signature) → T015-T020 (endpoint implementation) → T021-T022 (logging and docs)

**Phase 4**: Mostly sequential:
- T023-T026 (app setup and router) → T027-T029 can be done in parallel

**Phase 5**: After setup, tests can be written in parallel:
- T030-T032 (test setup) → T033-T044 (all tests in parallel)

### Parallel Opportunities

**Between Phase 1 and Phase 2**:
```bash
Developer A: Phase 1 (T001-T004) - Update ChatResponse model
Developer B: Phase 2 (T005-T007) - Create API module structure
```

**Within Phase 4 - Final tasks**:
```bash
Task T027: Health endpoint
Task T028: Local dev runner
Task T029: Documentation
```

**Phase 5 - All tests after setup**:
```bash
Task T033: test_health_check
Task T034: test_new_session
Task T035: test_existing_session
Task T036: test_ended_conversation
Task T037: test_validation_error_empty_message
Task T038: test_validation_error_missing_field
Task T039: test_graph_invocation_error
Task T040: test_invalid_message_type
Task T041: test_response_structure
Task T042: test_session_state_persistence
Task T043: test_message_history_accumulation
Task T044: test_response_performance
```

---

## Implementation Strategy

### Sequential Approach (Recommended for Single Developer)

1. **Phase 1**: Data Models → ChatResponse updated
2. **Phase 2**: API Module Structure → app/api/v1/endpoints/ created per constitution
3. **Phase 3**: Chat Router Implementation → POST /chat working
4. **Phase 4**: Application Entry Point → Server runnable
5. **Phase 5**: Integration Tests → All tests pass

**Total**: 44 tasks (4 model updates + 3 structure + 15 router + 7 app + 15 tests)

**Estimated Time**: 
- Phase 1: 30 minutes
- Phase 2: 10 minutes
- Phase 3: 2-3 hours (core endpoint logic)
- Phase 4: 30 minutes
- Phase 5: 2-3 hours (comprehensive tests)

**MVP Definition**: Phases 1-4 complete = functional API endpoint. Phase 5 = validation.

### Parallel Approach (If Multiple Developers Available)

1. **Developer A**: Phase 1 → Phase 3 → Phase 4 (API implementation)
2. **Developer B**: Wait for Phase 3 → Phase 5 (comprehensive tests)

**Timeline**: ~4-5 hours with parallel execution vs 6-7 hours sequential

---

## Testing Verification

After completing all tasks, verify the implementation:

```bash
# 1. Run the server
uvicorn app.main:app --reload

# 2. Test health check
curl http://localhost:8000/health

# 3. Test new conversation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-001","message":"Hello"}'

# 4. Run all tests
pytest tests/test_api.py -v

# 5. Check coverage
pytest tests/test_api.py --cov=app.api --cov-report=term-missing
```

**Success Criteria**:
- ✅ Server starts without errors
- ✅ Health check returns 200
- ✅ Chat endpoint accepts requests and returns valid responses
- ✅ All 15 tests pass
- ✅ Performance test validates <5 second response time
- ✅ Coverage >90% for app/api/v1/endpoints/chat.py

---

## Next Steps After Implementation

1. **Manual Testing**: Use the interactive docs at `http://localhost:8000/docs` to test the endpoint
2. **Integration Testing**: Test with actual LangGraph pipeline (not mocked)
3. **Performance Testing**: Verify <5 second response time requirement
4. **Documentation**: Update README with API usage examples
5. **Deployment**: Prepare Docker configuration for production deployment
