# Quickstart: API Endpoint

**Feature**: 008-api-endpoint  
**Date**: 2026-03-07  
**Audience**: Developers implementing or integrating with the API

## Overview

This guide shows how to implement, run, and test the FastAPI endpoint for the DEUS Bank AI Support System. It covers the core implementation patterns, server startup, and common integration scenarios.

---

## Prerequisites

- Python 3.11+
- All dependencies installed: `pip install -r requirements.txt`
- LangGraph pipeline implemented (spec 007)
- Data models defined (spec 001)
- All agents implemented (specs 004, 005, 006)

---

## Implementation

### Step 1: Create the Chat Router (`app/api/v1/endpoints/chat.py`)

```python
"""
Chat API endpoint for the DEUS Bank AI Support System.

This module defines the POST /chat endpoint that manages session state,
invokes the LangGraph pipeline, and returns structured responses.
"""

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
import logging

from app.models.schemas import ChatRequest, ChatResponse
from app.graph.state import GraphState
from app.graph.pipeline import graph

logger = logging.getLogger(__name__)

# Module-level session store
SESSION_STORE: dict[str, GraphState] = {}

router = APIRouter()


def create_initial_state(session_id: str) -> GraphState:
    """Create a new GraphState with default values for a new session.
    
    Args:
        session_id: Unique identifier for the session
        
    Returns:
        GraphState: Initialized state with all default fields
    """
    return {
        "messages": [],
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


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Handle chat requests and return agent responses.
    
    Args:
        request: ChatRequest with session_id and message
        
    Returns:
        ChatResponse: Agent's response with session metadata
        
    Raises:
        HTTPException: 500 if graph invocation fails
    """
    # Load or create session
    if request.session_id not in SESSION_STORE:
        SESSION_STORE[request.session_id] = create_initial_state(request.session_id)
    
    state = SESSION_STORE[request.session_id]
    
    # Guard: Check if conversation has ended
    if state["conversation_ended"]:
        return ChatResponse(
            session_id=request.session_id,
            response="This conversation has ended. Please start a new session.",
            current_agent=state["current_agent"],
            is_authenticated=state["is_authenticated"],
            conversation_ended=True
        )
    
    # Append user message to state
    state["messages"].append(HumanMessage(content=request.message))
    
    # Invoke graph
    try:
        updated_state = await graph.ainvoke(state)
    except Exception as e:
        logger.error(f"Graph invocation failed for session {request.session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred."
        )
    
    # Save updated state
    SESSION_STORE[request.session_id] = updated_state
    
    # Extract response from last AI message
    last_message = updated_state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        logger.error(f"Last message is not AIMessage: {type(last_message)}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred."
        )
    
    # Build and return response
    return ChatResponse(
        session_id=request.session_id,
        response=last_message.content,
        current_agent=updated_state["current_agent"],
        is_authenticated=updated_state["is_authenticated"],
        conversation_ended=updated_state["conversation_ended"]
    )
```

### Step 2: Create the Application Entry Point (`app/main.py`)

```python
"""
FastAPI application entry point for the DEUS Bank AI Support System.

This module creates the FastAPI app, includes routers, and defines
utility endpoints like health checks.
"""

from fastapi import FastAPI
from app.api.v1.endpoints.chat import router as chat_router

app = FastAPI(
    title="DEUS Bank AI Support",
    version="1.0.0",
    description="AI-powered customer support system with multi-agent pipeline"
)

# Include chat router
app.include_router(chat_router, prefix="", tags=["chat"])


@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Status indicator
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

### Step 3: Update Data Models (`app/models/schemas.py`)

**Required Modification**: Update `ChatResponse` to include all required fields:

```python
class ChatResponse(BaseModel):
    """Response body for the chat API endpoint.
    
    Attributes:
        session_id: The conversation session identifier (matches request)
        response: The agent's response message
        current_agent: Name of the agent that handled this turn
        is_authenticated: Whether the customer is authenticated
        conversation_ended: Whether the conversation has ended
    """
    session_id: str
    response: str
    current_agent: str  # Changed from 'agent'
    is_authenticated: bool  # NEW
    conversation_ended: bool  # NEW
```

---

## Running the Server

### Development Mode (with auto-reload)

```bash
# From repository root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using watchdog
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Using the built-in runner

```bash
# From repository root
python -m app.main
```

### Production Mode (no auto-reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Testing

### Manual Testing with curl

#### 1. Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

#### 2. Start a New Conversation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "Hello, I need help"
  }'
```

**Response**:
```json
{
  "session_id": "test-001",
  "response": "Hello! I'm here to help you today. Before we proceed, I need to verify your identity. May I have your date of birth?",
  "current_agent": "greeter",
  "is_authenticated": false,
  "conversation_ended": false
}
```

#### 3. Continue the Conversation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "1990-05-15"
  }'
```

### Automated Testing with pytest

Create `tests/test_api.py`:

```python
"""Integration tests for the chat API endpoint."""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import pytest

from app.main import app
from app.api.v1.endpoints.chat import SESSION_STORE
from app.graph.state import GraphState
from langchain_core.messages import HumanMessage, AIMessage


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear session store before each test."""
    SESSION_STORE.clear()
    yield
    SESSION_STORE.clear()


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_new_session(client, monkeypatch):
    """Test creating a new session."""
    # Mock graph.ainvoke
    mock_state = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Welcome! May I have your DOB?")
        ],
        "session_id": "test-001",
        "verified_user": None,
        "is_authenticated": False,
        "customer_tier": None,
        "customer_intent": None,
        "current_agent": "greeter",
        "collected_fields": {},
        "verification_attempts": 0,
        "conversation_ended": False
    }
    mock_invoke = AsyncMock(return_value=mock_state)
    monkeypatch.setattr("app.api.v1.endpoints.chat.graph.ainvoke", mock_invoke)
    
    # Make request
    response = client.post("/chat", json={
        "session_id": "test-001",
        "message": "Hello"
    })
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-001"
    assert data["current_agent"] == "greeter"
    assert data["is_authenticated"] is False
    assert data["conversation_ended"] is False
    assert "test-001" in SESSION_STORE


def test_existing_session(client, monkeypatch):
    """Test continuing an existing session."""
    # Pre-populate session
    SESSION_STORE["test-002"] = {
        "messages": [HumanMessage(content="Hello")],
        "session_id": "test-002",
        "verified_user": None,
        "is_authenticated": False,
        "customer_tier": None,
        "customer_intent": None,
        "current_agent": "greeter",
        "collected_fields": {},
        "verification_attempts": 0,
        "conversation_ended": False
    }
    
    # Mock graph.ainvoke
    mock_state = SESSION_STORE["test-002"].copy()
    mock_state["messages"].append(HumanMessage(content="1990-05-15"))
    mock_state["messages"].append(AIMessage(content="Thank you. What is your name?"))
    mock_invoke = AsyncMock(return_value=mock_state)
    monkeypatch.setattr("app.api.v1.endpoints.chat.graph.ainvoke", mock_invoke)
    
    # Make request
    response = client.post("/chat", json={
        "session_id": "test-002",
        "message": "1990-05-15"
    })
    
    # Assertions
    assert response.status_code == 200
    assert len(SESSION_STORE["test-002"]["messages"]) > 1


def test_ended_conversation(client):
    """Test that ended conversations return termination message."""
    # Pre-populate session with ended conversation
    SESSION_STORE["test-003"] = {
        "messages": [HumanMessage(content="Goodbye")],
        "session_id": "test-003",
        "verified_user": None,
        "is_authenticated": True,
        "customer_tier": "standard",
        "customer_intent": None,
        "current_agent": "specialist_standard",
        "collected_fields": {},
        "verification_attempts": 0,
        "conversation_ended": True
    }
    
    # Make request (should NOT invoke graph)
    response = client.post("/chat", json={
        "session_id": "test-003",
        "message": "Wait, one more thing"
    })
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "has ended" in data["response"]
    assert data["conversation_ended"] is True


def test_validation_error_empty_message(client):
    """Test that empty message returns 422."""
    response = client.post("/chat", json={
        "session_id": "test-004",
        "message": ""
    })
    
    assert response.status_code == 422


def test_graph_invocation_error(client, monkeypatch):
    """Test that graph errors return 500."""
    # Mock graph.ainvoke to raise exception
    mock_invoke = AsyncMock(side_effect=Exception("LLM timeout"))
    monkeypatch.setattr("app.api.v1.endpoints.chat.graph.ainvoke", mock_invoke)
    
    # Make request
    response = client.post("/chat", json={
        "session_id": "test-005",
        "message": "Hello"
    })
    
    # Assertions
    assert response.status_code == 500
    assert "internal error" in response.json()["detail"].lower()
```

**Run tests**:
```bash
pytest tests/test_api.py -v
```

---

## Interactive Documentation

FastAPI automatically generates interactive API documentation.

### Swagger UI

1. Start the server: `uvicorn app.main:app --reload`
2. Open browser: `http://localhost:8000/docs`
3. Try the endpoints directly in the browser

### ReDoc

Alternative documentation UI: `http://localhost:8000/redoc`

---

## Common Patterns

### Pattern 1: Multi-Turn Conversation Client

```python
import requests
from uuid import uuid4

class ChatClient:
    """Simple client for testing multi-turn conversations."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"client-{uuid4()}"
    
    def send(self, message: str) -> dict:
        """Send a message and return the response."""
        response = requests.post(
            f"{self.base_url}/chat",
            json={"session_id": self.session_id, "message": message}
        )
        response.raise_for_status()
        return response.json()
    
    def chat(self):
        """Interactive chat loop."""
        print(f"Session: {self.session_id}")
        print("Type 'exit' to quit\n")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break
            
            result = self.send(user_input)
            print(f"Agent ({result['current_agent']}): {result['response']}")
            print(f"Authenticated: {result['is_authenticated']}")
            
            if result["conversation_ended"]:
                print("\nConversation ended.")
                break


# Usage
if __name__ == "__main__":
    client = ChatClient()
    client.chat()
```

### Pattern 2: Programmatic Verification Flow

```python
def complete_verification(client: ChatClient, user_data: dict):
    """Complete the verification flow programmatically."""
    
    # Greeting
    response = client.send("Hello")
    print(response["response"])
    
    # Provide DOB
    response = client.send(user_data["dob"])
    print(response["response"])
    
    # Provide name
    response = client.send(user_data["name"])
    print(response["response"])
    
    # Provide phone or IBAN if needed
    if not response["is_authenticated"]:
        response = client.send(user_data["phone"])
        print(response["response"])
    
    # Answer secret question
    response = client.send(user_data["secret_answer"])
    print(response["response"])
    
    return response["is_authenticated"]


# Usage
user = {
    "dob": "1990-05-15",
    "name": "Alice Johnson",
    "phone": "+1234567890",
    "secret_answer": "Fluffy"
}

client = ChatClient()
authenticated = complete_verification(client, user)
print(f"Authenticated: {authenticated}")
```

---

## Troubleshooting

### Issue: Module not found errors

**Solution**: Ensure you're running from the repository root and the `app` package is in your Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn app.main:app --reload
```

### Issue: Session state not persisting

**Symptom**: Each request sees a fresh session

**Cause**: Server is restarting or `SESSION_STORE` is being cleared

**Solution**: Check that auto-reload is not reloading unnecessarily. Use `--reload-exclude` for data files.

### Issue: 500 errors on graph invocation

**Symptom**: All chat requests return 500

**Cause**: Graph import fails or agents have errors

**Solution**: Check server logs for detailed stack traces. Test graph independently:
```python
from app.graph.pipeline import graph
from app.graph.state import GraphState

state: GraphState = {...}  # Initial state
result = await graph.ainvoke(state)
```

---

## Next Steps

1. **Run the server**: `uvicorn app.main:app --reload`
2. **Test health check**: `curl http://localhost:8000/health`
3. **Test chat endpoint**: Use curl or the interactive docs
4. **Run automated tests**: `pytest tests/test_api.py -v`
5. **Build a client**: Use the patterns above to create a CLI or GUI client

For production deployment, see the Docker configuration and deployment guides (separate documentation).
