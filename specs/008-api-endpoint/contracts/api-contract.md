# API Contract: DEUS Bank AI Support System

**Feature**: 008-api-endpoint  
**Date**: 2026-03-07  
**Version**: 1.0  
**Type**: REST HTTP API

## Overview

This document defines the external HTTP API contract for the DEUS Bank AI Support System. It specifies endpoints, request/response formats, status codes, error handling, and behavioral guarantees.

---

## Base URL

**Development**: `http://localhost:8000`  
**Production**: TBD (configured via environment variables)

---

## Endpoints

### 1. POST /chat

**Purpose**: Process a customer message and return the agent's response

**Authentication**: None required (intentional per spec)

**Rate Limiting**: None (intentional per spec)

**Content-Type**: `application/json`

#### Request

**Body** (JSON):
```json
{
  "session_id": "string",
  "message": "string"
}
```

**Parameters**:
| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `session_id` | string | Yes | min_length: 1 | Unique identifier for the conversation session |
| `message` | string | Yes | min_length: 1 | The customer's input message |

**Example**:
```json
{
  "session_id": "user-12345-session-001",
  "message": "I need help with my account"
}
```

#### Response (Success)

**Status Code**: `200 OK`

**Body** (JSON):
```json
{
  "session_id": "string",
  "response": "string",
  "current_agent": "string",
  "is_authenticated": boolean,
  "conversation_ended": boolean
}
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Echo of the request's session ID |
| `response` | string | The agent's response message |
| `current_agent` | string | Agent that handled this turn (`"greeter"`, `"bouncer"`, `"specialist_standard"`, `"specialist_premium"`, `"specialist_vip"`) |
| `is_authenticated` | boolean | Whether the customer has been authenticated |
| `conversation_ended` | boolean | Whether the conversation has ended |

**Example**:
```json
{
  "session_id": "user-12345-session-001",
  "response": "Hello! I'm here to help you today. Before we proceed, I need to verify your identity. May I have your date of birth?",
  "current_agent": "greeter",
  "is_authenticated": false,
  "conversation_ended": false
}
```

#### Response (Validation Error)

**Status Code**: `422 Unprocessable Entity`

**Body** (JSON):
```json
{
  "detail": [
    {
      "type": "string",
      "loc": ["body", "field_name"],
      "msg": "string",
      "input": "any"
    }
  ]
}
```

**When**: Request body fails Pydantic validation (empty fields, missing fields, wrong types)

**Example**:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "message"],
      "msg": "Field required",
      "input": {"session_id": "test-001"}
    }
  ]
}
```

#### Response (Internal Error)

**Status Code**: `500 Internal Server Error`

**Body** (JSON):
```json
{
  "detail": "An internal error occurred."
}
```

**When**: Graph invocation fails, unhandled exceptions, LLM errors

**Security Note**: Error details are intentionally generic. Full error information is logged server-side but never exposed to clients.

---

### 2. GET /health

**Purpose**: Health check endpoint for monitoring and load balancers

**Authentication**: None required

**Request**: No body or parameters

#### Response

**Status Code**: `200 OK`

**Body** (JSON):
```json
{
  "status": "ok"
}
```

**Example**:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## Behavioral Guarantees

### Session Lifecycle

1. **New Session**: First request with a new `session_id` creates a fresh session with default state
2. **Existing Session**: Subsequent requests with the same `session_id` continue the conversation with preserved history
3. **Ended Conversation**: If `conversation_ended` is `true`, subsequent messages return a termination message without invoking the graph
4. **Server Restart**: All sessions are lost (in-memory storage per spec)

### Conversation Flow

| Turn | Action | `current_agent` | `is_authenticated` | `conversation_ended` |
|------|--------|-----------------|--------------------|----------------------|
| 1 | User sends greeting | `"greeter"` | `false` | `false` |
| 2 | User provides DOB | `"greeter"` | `false` (verification in progress) | `false` |
| 3 | User provides name | `"greeter"` | `true` (verified) | `false` |
| 4 | User asks about balance | `"bouncer"` → `"specialist_vip"` | `true` | `false` |
| 5 | Specialist answers | `"specialist_vip"` | `true` | `false` |
| 6 | User says goodbye | `"specialist_vip"` | `true` | `true` |
| 7 | User tries to continue | N/A (graph not invoked) | N/A | N/A |

**Turn 7 Response**:
```json
{
  "session_id": "user-12345-session-001",
  "response": "This conversation has ended. Please start a new session.",
  "current_agent": "specialist_vip",
  "is_authenticated": true,
  "conversation_ended": true
}
```

### Error Handling

| Scenario | HTTP Status | Behavior |
|----------|-------------|----------|
| Empty `message` field | 422 | Pydantic validation error returned |
| Missing `session_id` | 422 | Pydantic validation error returned |
| Graph invocation fails | 500 | Generic error message, details logged server-side |
| LLM timeout/error | 500 | Generic error message, conversation state preserved |
| Ended conversation + new message | 200 | Returns termination message, graph NOT invoked |

### Performance Guarantees

- **Response Time**: <5 seconds under normal load (per spec success criteria)
- **Concurrency**: Supports multiple concurrent sessions
- **Session Isolation**: Sessions do not interfere with each other

---

## CORS Policy

**Status**: Not implemented (per spec clarifications)

**Implication**: API can only be called from same-origin or from clients that don't enforce CORS (e.g., server-to-server, CLI tools)

---

## Authentication & Authorization

**Status**: Not implemented (per spec clarifications)

**Implication**: All requests are accepted without authentication. Identity verification happens at the application level (via Greeter agent), not at the API level.

---

## Rate Limiting

**Status**: Not implemented (per spec clarifications)

**Implication**: No protection against abuse. Suitable for development/challenge context but not production-ready.

---

## OpenAPI Documentation

The API automatically generates OpenAPI 3.0 documentation via FastAPI.

**Access**:
- Interactive docs (Swagger UI): `http://localhost:8000/docs`
- Alternative docs (ReDoc): `http://localhost:8000/redoc`
- OpenAPI JSON schema: `http://localhost:8000/openapi.json`

---

## Client Integration Examples

### Python (requests)

```python
import requests

# Start conversation
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "session_id": "user-12345-session-001",
        "message": "Hello, I need help"
    }
)

data = response.json()
print(data["response"])
print(f"Authenticated: {data['is_authenticated']}")
```

### curl

```bash
# New session
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-001","message":"Hello"}'

# Continue session
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-001","message":"My name is John Doe"}'
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8000/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'user-12345-session-001',
    message: 'I need help with my account'
  })
});

const data = await response.json();
console.log(data.response);
console.log(`Agent: ${data.current_agent}`);
```

---

## Versioning

**Current Version**: 1.0  
**Versioning Strategy**: Not implemented (single version for challenge)  
**Future**: API versioning via URL prefix (`/v1/chat`, `/v2/chat`) or Accept headers

---

## Summary

- **Endpoint**: `POST /chat` for message processing, `GET /health` for monitoring
- **Request**: JSON with `session_id` and `message`
- **Response**: JSON with `response`, `current_agent`, `is_authenticated`, `conversation_ended`
- **Status Codes**: 200 (success), 422 (validation), 500 (internal error)
- **Session Management**: In-memory, persisted across requests within server lifetime
- **Error Handling**: Generic client messages, detailed server logs
- **Documentation**: Automatic OpenAPI generation via FastAPI
