"""Integration tests for the API endpoint.

This module tests the FastAPI chat endpoint with mocked graph to verify:
- Request/response handling
- Session management
- Error handling
- Validation
- Performance requirements
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.api.v1.endpoints.chat import SESSION_STORE


@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app.
    
    Returns:
        TestClient: Test client for making HTTP requests
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_session_store():
    """Clear the SESSION_STORE before and after each test.
    
    This ensures test isolation by preventing state leakage between tests.
    """
    SESSION_STORE.clear()
    yield
    SESSION_STORE.clear()


def test_health_check(client):
    """Test the health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.v1.endpoints.chat.graph")
def test_new_session(mock_graph, client):
    """Test that POST /chat creates a new session with default state."""
    # Mock graph to return a state with an AI response
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi! How can I help you?"),
            ],
            "session_id": "test-session-001",
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-001", "message": "Hello"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-001"
    assert data["response"] == "Hi! How can I help you?"
    assert data["current_agent"] == "greeter"
    assert data["is_authenticated"] is False
    assert data["conversation_ended"] is False
    assert "test-session-001" in SESSION_STORE


@patch("app.api.v1.endpoints.chat.graph")
def test_existing_session(mock_graph, client):
    """Test that POST /chat reuses and updates an existing session."""
    # First request - create session
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi! How can I help you?"),
            ],
            "session_id": "test-session-002",
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": "test-session-002", "message": "Hello"},
    )
    
    # Second request - reuse session
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi! How can I help you?"),
                HumanMessage(content="I need help"),
                AIMessage(content="What do you need help with?"),
            ],
            "session_id": "test-session-002",
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-002", "message": "I need help"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "What do you need help with?"
    # Verify session was reused (messages accumulated)
    assert len(SESSION_STORE["test-session-002"]["messages"]) == 4


def test_ended_conversation(client):
    """Test that endpoint returns termination message without invoking graph."""
    # Pre-populate session with ended conversation
    SESSION_STORE["test-session-003"] = {
        "messages": [
            HumanMessage(content="Goodbye"),
            AIMessage(content="Thank you for contacting DEUS Bank!"),
        ],
        "session_id": "test-session-003",
        "verified_user": None,
        "is_authenticated": False,
        "customer_tier": None,
        "customer_intent": None,
        "current_agent": "greeter",
        "collected_fields": {},
        "verification_attempts": 0,
        "conversation_ended": True,
    }
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-003", "message": "Are you there?"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_ended"] is True
    assert "ended" in data["response"].lower()
    # Verify messages list was not modified (no new message appended)
    assert len(SESSION_STORE["test-session-003"]["messages"]) == 2


def test_validation_error_empty_message(client):
    """Test that empty message returns 422 validation error."""
    response = client.post(
        "/chat",
        json={"session_id": "test-session-004", "message": ""},
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_validation_error_missing_field(client):
    """Test that missing field returns 422 validation error."""
    response = client.post(
        "/chat",
        json={"session_id": "test-session-005"},
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@patch("app.api.v1.endpoints.chat.graph")
def test_graph_invocation_error(mock_graph, client):
    """Test that graph errors return 500 with generic message."""
    mock_graph.ainvoke = AsyncMock(side_effect=Exception("Graph failure"))
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-006", "message": "Hello"},
    )
    
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal error occurred."
    # Verify no internal details leaked
    assert "Graph failure" not in data["detail"]


@patch("app.api.v1.endpoints.chat.graph")
def test_invalid_message_type(mock_graph, client):
    """Test that non-AIMessage last message returns 500."""
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                HumanMessage(content="Another human message"),
            ],
            "session_id": "test-session-007",
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-007", "message": "Hello"},
    )
    
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal error occurred."


@patch("app.api.v1.endpoints.chat.graph")
def test_response_structure(mock_graph, client):
    """Test that ChatResponse contains all required fields."""
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there!"),
            ],
            "session_id": "test-session-008",
            "verified_user": None,
            "is_authenticated": True,
            "customer_tier": "premium",
            "customer_intent": "account_inquiry",
            "current_agent": "specialist_premium",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    response = client.post(
        "/chat",
        json={"session_id": "test-session-008", "message": "Hello"},
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify all required fields are present
    assert "session_id" in data
    assert "response" in data
    assert "current_agent" in data
    assert "is_authenticated" in data
    assert "conversation_ended" in data
    
    # Verify field values
    assert data["session_id"] == "test-session-008"
    assert data["response"] == "Hi there!"
    assert data["current_agent"] == "specialist_premium"
    assert data["is_authenticated"] is True
    assert data["conversation_ended"] is False


@patch("app.api.v1.endpoints.chat.graph")
def test_session_state_persistence(mock_graph, client):
    """Test that state persists across multiple requests."""
    session_id = "test-session-009"
    
    # First request
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
            ],
            "session_id": session_id,
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {"name": "John"},
            "verification_attempts": 1,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "Hello"},
    )
    
    # Verify state persisted
    assert session_id in SESSION_STORE
    state = SESSION_STORE[session_id]
    assert state["collected_fields"]["name"] == "John"
    assert state["verification_attempts"] == 1
    
    # Second request - state should be reused
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
                HumanMessage(content="My DOB is 1990-01-01"),
                AIMessage(content="Thank you!"),
            ],
            "session_id": session_id,
            "verified_user": "user-123",
            "is_authenticated": True,
            "customer_tier": "premium",
            "customer_intent": None,
            "current_agent": "bouncer",
            "collected_fields": {"name": "John", "dob": "1990-01-01"},
            "verification_attempts": 1,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "My DOB is 1990-01-01"},
    )
    
    # Verify state updated
    state = SESSION_STORE[session_id]
    assert state["is_authenticated"] is True
    assert state["verified_user"] == "user-123"
    assert state["customer_tier"] == "premium"
    assert state["collected_fields"]["dob"] == "1990-01-01"


@patch("app.api.v1.endpoints.chat.graph")
def test_message_history_accumulation(mock_graph, client):
    """Test that messages list grows with each turn."""
    session_id = "test-session-010"
    
    # First turn
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
            ],
            "session_id": session_id,
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "Hello"},
    )
    assert len(SESSION_STORE[session_id]["messages"]) == 2
    
    # Second turn
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
                HumanMessage(content="I need help"),
                AIMessage(content="Sure!"),
            ],
            "session_id": session_id,
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "I need help"},
    )
    assert len(SESSION_STORE[session_id]["messages"]) == 4
    
    # Third turn
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
                HumanMessage(content="I need help"),
                AIMessage(content="Sure!"),
                HumanMessage(content="Thanks"),
                AIMessage(content="You're welcome!"),
            ],
            "session_id": session_id,
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    client.post(
        "/chat",
        json={"session_id": session_id, "message": "Thanks"},
    )
    assert len(SESSION_STORE[session_id]["messages"]) == 6


@patch("app.api.v1.endpoints.chat.graph")
def test_response_performance(mock_graph, client):
    """Test that response time is under 5 seconds with mocked graph."""
    mock_graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi!"),
            ],
            "session_id": "test-session-011",
            "verified_user": None,
            "is_authenticated": False,
            "customer_tier": None,
            "customer_intent": None,
            "current_agent": "greeter",
            "collected_fields": {},
            "verification_attempts": 0,
            "conversation_ended": False,
        }
    )
    
    start_time = time.time()
    response = client.post(
        "/chat",
        json={"session_id": "test-session-011", "message": "Hello"},
    )
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed_time < 5.0, f"Response took {elapsed_time:.2f}s, expected < 5s"
