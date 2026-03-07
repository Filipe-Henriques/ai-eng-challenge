# Research: API Endpoint

**Feature**: 008-api-endpoint  
**Date**: 2026-03-07  
**Phase**: 0 (Research & Discovery)

## Research Questions

1. What are best practices for FastAPI async endpoint design?
2. How should session state be managed in-memory for a FastAPI application?
3. What error handling patterns are recommended for FastAPI endpoints?
4. How to integrate FastAPI with async LangGraph pipeline invocation?
5. What testing approaches are effective for FastAPI endpoints with external dependencies?

---

## 1. FastAPI Async Endpoint Design

### Decision: Use Fully Async Endpoint Handlers

**Rationale**: The LangGraph pipeline uses `async def` functions and provides `.ainvoke()` for async execution. FastAPI natively supports async handlers with `async def`, allowing the endpoint to await the graph invocation without blocking the event loop.

**Best Practices**:
- Define endpoint handlers with `async def` when performing I/O operations (LLM calls, database, external APIs)
- Use `await` for all async operations (graph invocation, async database calls)
- FastAPI automatically runs async handlers in the event loop without thread pool overhead
- Return Pydantic models directly from async handlers for automatic serialization

**Implementation Pattern**:
```python
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    # Load/create session state
    state = get_or_create_session(request.session_id)
    
    # Await async graph invocation
    updated_state = await graph.ainvoke(state)
    
    # Return Pydantic model
    return build_response(updated_state)
```

**Alternatives Considered**:
- **Synchronous handler with thread pool**: Rejected because it adds unnecessary overhead and complexity. FastAPI's async support is more efficient for I/O-bound operations like LLM calls.
- **Background tasks**: Rejected because the API must return the response synchronously per spec requirements.

---

## 2. In-Memory Session Management

### Decision: Module-Level Dictionary with GraphState Values

**Rationale**: The spec explicitly requires in-memory session storage that resets on restart. A module-level `dict[str, GraphState]` is the simplest implementation that meets requirements without introducing external dependencies.

**Best Practices**:
- Declare dictionary at module level: `SESSION_STORE: dict[str, GraphState] = {}`
- Use `session_id` as the key for O(1) lookups
- Initialize new sessions with a factory function to ensure consistent default values
- Store the complete `GraphState` dict (not just messages) to preserve all stateful fields

**Implementation Pattern**:
```python
# Module level
SESSION_STORE: dict[str, GraphState] = {}

def get_or_create_session(session_id: str) -> GraphState:
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = create_initial_state(session_id)
    return SESSION_STORE[session_id]

def create_initial_state(session_id: str) -> GraphState:
    return {
        "messages": [],
        "session_id": session_id,
        "verified_user": None,
        # ... all other default fields per spec
    }
```

**Alternatives Considered**:
- **Redis or external cache**: Rejected because spec explicitly states in-memory storage with restart reset is intentional. No persistence required.
- **Class-based state manager**: Rejected for simplicity. A module-level dict is sufficient and follows the principle of using the simplest solution that meets requirements.
- **Thread-safe locks**: Not required because Python's GIL ensures dict operations are atomic for single-key access. FastAPI's async model uses a single-threaded event loop by default.

---

## 3. Error Handling Patterns

### Decision: Try-Except with HTTPException for Graph Errors

**Rationale**: FastAPI provides `HTTPException` for returning HTTP error responses. Graph invocation failures (LLM errors, validation errors) should be caught and returned as HTTP 500 with a generic message to avoid exposing internal details.

**Best Practices**:
- Wrap `graph.ainvoke()` in try-except to catch all exceptions
- Raise `HTTPException(status_code=500, detail="...")` for internal errors
- Return generic error messages to clients (no stack traces or internal details)
- Pydantic validation errors are automatically handled by FastAPI (returns 422)
- Log detailed errors server-side for debugging while returning safe messages to clients

**Implementation Pattern**:
```python
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

try:
    updated_state = await graph.ainvoke(state)
except Exception as e:
    logger.error(f"Graph invocation failed: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="An internal error occurred."
    )
```

**Alternatives Considered**:
- **Return error in response body with 200 OK**: Rejected because HTTP status codes should reflect actual failure (5xx for server errors).
- **Custom exception handler**: Not needed for this simple case. Inline try-except is clearer and sufficient.

---

## 4. FastAPI + LangGraph Integration

### Decision: Import Compiled Graph and Invoke Async

**Rationale**: The LangGraph pipeline (spec 007) exports a compiled `graph` object from `app.graph.pipeline`. The API layer imports this object and calls `.ainvoke(state)` with the session state.

**Best Practices**:
- Import the compiled graph at module level: `from app.graph.pipeline import graph`
- Pass the complete `GraphState` dict to `graph.ainvoke(state)`
- The graph returns an updated `GraphState` dict with new messages and modified fields
- Extract the response from the last `AIMessage` in the returned `state["messages"]` list
- Save the returned state back to `SESSION_STORE` to persist changes across turns

**Implementation Pattern**:
```python
from app.graph.pipeline import graph
from langchain_core.messages import HumanMessage, AIMessage

# Append user message to state
state["messages"].append(HumanMessage(content=request.message))

# Invoke graph (async)
updated_state = await graph.ainvoke(state)

# Save updated state
SESSION_STORE[request.session_id] = updated_state

# Extract response from last AIMessage
last_message = updated_state["messages"][-1]
assert isinstance(last_message, AIMessage)
response_text = last_message.content
```

**Alternatives Considered**:
- **Streaming with `.astream()`**: Deferred to future work. Spec requires synchronous response return, not streaming.
- **Graph invocation in background task**: Rejected because the endpoint must return the response, not acknowledge receipt.

---

## 5. Testing FastAPI Endpoints

### Decision: Use FastAPI TestClient with Mocked Graph

**Rationale**: FastAPI provides `TestClient` for synchronous testing of async endpoints. Tests should mock `graph.ainvoke` to return controlled state without making real LLM calls, enabling fast, deterministic tests.

**Best Practices**:
- Use `from fastapi.testclient import TestClient`
- Mock `graph.ainvoke` with `unittest.mock.AsyncMock` to control return values
- Test key scenarios: new session, existing session, ended conversation, validation errors, exceptions
- Verify session state changes in `SESSION_STORE` after requests
- Clear `SESSION_STORE` in teardown to ensure test isolation

**Implementation Pattern**:
```python
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.api.chat import SESSION_STORE

client = TestClient(app)

def test_new_session(monkeypatch):
    # Mock graph.ainvoke to return controlled state
    mock_invoke = AsyncMock(return_value={
        "messages": [...],
        "session_id": "test-001",
        "current_agent": "greeter",
        # ... full state
    })
    monkeypatch.setattr("app.api.chat.graph.ainvoke", mock_invoke)
    
    # Make request
    response = client.post("/chat", json={
        "session_id": "test-001",
        "message": "Hello"
    })
    
    # Assertions
    assert response.status_code == 200
    assert "test-001" in SESSION_STORE
    mock_invoke.assert_called_once()
```

**Alternatives Considered**:
- **End-to-end tests with real LLM**: Deferred to integration test suite. Unit tests should be fast and deterministic.
- **Direct function testing without HTTP layer**: Missed coverage of request parsing, validation, and HTTP error codes. TestClient provides full stack testing.

---

## Summary

All research questions have been resolved with clear decisions and implementation patterns:

1. **Async Endpoints**: Use `async def` handlers with `await` for graph invocation
2. **Session Management**: Module-level `dict[str, GraphState]` with factory function for initialization
3. **Error Handling**: Try-except around graph calls with `HTTPException(500)` for failures
4. **LangGraph Integration**: Import compiled graph, invoke with `.ainvoke()`, extract response from messages list
5. **Testing**: FastAPI TestClient with mocked `graph.ainvoke` for fast, deterministic tests

No unknowns remain. Ready for Phase 1 (Design Artifacts).
