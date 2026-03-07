# Data Model: API Endpoint

**Feature**: 008-api-endpoint  
**Date**: 2026-03-07  
**Phase**: 1 (Design Artifacts)

## Overview

This document defines the Pydantic models for the API endpoint's request and response bodies. These models provide automatic validation, serialization, and OpenAPI documentation for the `/chat` endpoint.

---

## ChatRequest

**Location**: `app/models/schemas.py`  
**Purpose**: Validates incoming POST requests to `/chat`

### Fields

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `session_id` | `str` | Yes | Non-empty string | Unique identifier for the conversation session |
| `message` | `str` | Yes | Non-empty string | The customer's input message |

### Pydantic Model Definition

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request body for the chat API endpoint.
    
    Attributes:
        session_id: Unique identifier for the conversation session
        message: The customer's input message
    """
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    message: str = Field(..., min_length=1, description="Customer's message text")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "user-12345-session-001",
                    "message": "I need help with my account"
                }
            ]
        }
    }
```

### Validation Behavior

- **Empty `session_id`**: Returns HTTP 422 with validation error
- **Empty `message`**: Returns HTTP 422 with validation error
- **Missing fields**: Returns HTTP 422 with validation error
- **Extra fields**: Ignored by default (Pydantic's default behavior)

---

## ChatResponse

**Location**: `app/models/schemas.py`  
**Purpose**: Structures the response returned from `/chat`

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | `str` | Yes | Echo of the request's session ID |
| `response` | `str` | Yes | The agent's response message text |
| `current_agent` | `str` | Yes | Name of the agent that produced the response (e.g., "greeter", "specialist_vip") |
| `is_authenticated` | `bool` | Yes | Whether the customer has been successfully authenticated |
| `conversation_ended` | `bool` | Yes | Whether the conversation has ended (triggers end of session) |

### Pydantic Model Definition

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
    current_agent: str
    is_authenticated: bool
    conversation_ended: bool
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "user-12345-session-001",
                    "response": "Hello! I'm here to help you today. Before we proceed, I need to verify your identity. May I have your date of birth?",
                    "current_agent": "greeter",
                    "is_authenticated": False,
                    "conversation_ended": False
                }
            ]
        }
    }
```

### Field Mapping from GraphState

The `ChatResponse` is built from the `GraphState` returned by the graph:

| ChatResponse Field | Source from GraphState | Notes |
|--------------------|------------------------|-------|
| `session_id` | `state["session_id"]` | Direct copy |
| `response` | `state["messages"][-1].content` | Extract content from last AIMessage |
| `current_agent` | `state["current_agent"]` | Direct copy |
| `is_authenticated` | `state["is_authenticated"]` | Direct copy |
| `conversation_ended` | `state["conversation_ended"]` | Direct copy |

---

## Implementation Notes

### Existing Model Status

**Current State**: The `ChatRequest` and `ChatResponse` models **already exist** in `app/models/schemas.py` (from spec 001).

**Required Modifications**:
- `ChatRequest`: ✅ **No changes needed** - already matches spec
- `ChatResponse`: ⚠️ **Needs update** - currently has only 3 fields (`session_id`, `response`, `agent`), must add:
  - Rename `agent` → `current_agent`
  - Add `is_authenticated: bool`
  - Add `conversation_ended: bool`

### Response Building Pattern

```python
from langchain_core.messages import AIMessage

def build_chat_response(session_id: str, state: GraphState) -> ChatResponse:
    """Build ChatResponse from GraphState after graph invocation.
    
    Args:
        session_id: Session identifier from request
        state: Updated GraphState from graph.ainvoke()
        
    Returns:
        ChatResponse with all required fields
    """
    # Extract last AI message
    last_message = state["messages"][-1]
    assert isinstance(last_message, AIMessage), "Last message must be AIMessage"
    
    return ChatResponse(
        session_id=session_id,
        response=last_message.content,
        current_agent=state["current_agent"],
        is_authenticated=state["is_authenticated"],
        conversation_ended=state["conversation_ended"]
    )
```

---

## Validation Examples

### Valid Request

```json
{
  "session_id": "user-12345-session-001",
  "message": "I need help with my account"
}
```

✅ **Result**: HTTP 200 with ChatResponse

### Invalid Request: Empty Message

```json
{
  "session_id": "user-12345-session-001",
  "message": ""
}
```

❌ **Result**: HTTP 422 with validation error:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
    }
  ]
}
```

### Invalid Request: Missing Field

```json
{
  "session_id": "user-12345-session-001"
}
```

❌ **Result**: HTTP 422 with validation error:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "message"],
      "msg": "Field required",
      "input": {"session_id": "user-12345-session-001"}
    }
  ]
}
```

---

## Summary

- **ChatRequest**: Defines required inputs for `/chat` endpoint (session_id, message)
- **ChatResponse**: Defines structured output with session state metadata
- **Validation**: Pydantic automatically validates requests and returns HTTP 422 for invalid input
- **Serialization**: Pydantic automatically serializes response to JSON
- **Documentation**: Models generate OpenAPI schema for automatic API documentation
- **Modification Required**: Update existing `ChatResponse` to include `is_authenticated` and `conversation_ended` fields
