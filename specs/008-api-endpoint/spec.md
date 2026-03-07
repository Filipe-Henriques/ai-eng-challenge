# Spec: API Endpoint — DEUS Bank AI Support System

## 1. Description

This spec defines the **FastAPI Endpoint**, the external interface of the system. It exposes a single HTTP endpoint that receives a customer's message, manages the session state, invokes the LangGraph pipeline, and returns the agent's response. It lives in `app/api/v1/endpoints/chat.py` and is mounted in `app/main.py`.

## 2. Endpoint Definition

### `POST /chat`

| Property | Value |
| :--- | :--- |
| Method | `POST` |
| Path | `/chat` |
| Request Body | `ChatRequest` (Pydantic model from `app/models`) |
| Response Body | `ChatResponse` (Pydantic model from `app/models`) |
| Status Codes | `200 OK`, `422 Unprocessable Entity` (validation error) |

### Request Model (`ChatRequest`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `session_id` | `str` | Unique identifier for the conversation session |
| `message` | `str` | The customer's message text |

### Response Model (`ChatResponse`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `session_id` | `str` | Echo of the request's session ID |
| `response` | `str` | The agent's response message |
| `current_agent` | `str` | The agent that produced the response |
| `is_authenticated` | `bool` | Whether the customer is authenticated |
| `conversation_ended` | `bool` | Whether the conversation has ended |

## 3. Session Management

The API layer is responsible for managing session state between turns. It uses a **module-level in-memory dictionary** to store the full `GraphState` for each active session.

```python
# app/api/v1/endpoints/chat.py
SESSION_STORE: dict[str, GraphState] = {}
```

### Session Lifecycle

1. **New session**: If `session_id` is not in `SESSION_STORE`, initialise a new `GraphState` with default values and an empty `messages` list.
2. **Existing session**: Load the existing `GraphState` from `SESSION_STORE`.
3. **Append message**: Add the customer's new message to `state["messages"]` as a `HumanMessage`.
4. **Invoke graph**: Call `await graph.ainvoke(state)` with the updated state.
5. **Save state**: Store the returned state back in `SESSION_STORE` under the `session_id`.
6. **Extract response**: Get the last `AIMessage` from the returned state's `messages` list.
7. **Return response**: Build and return the `ChatResponse` object.

## 4. Initial State

When a new session is created, the `GraphState` MUST be initialised with the following default values:

| Field | Default Value |
| :--- | :--- |
| `messages` | `[]` |
| `session_id` | value from `ChatRequest.session_id` |
| `verified_user` | `None` |
| `is_authenticated` | `False` |
| `customer_tier` | `None` |
| `customer_intent` | `None` |
| `current_agent` | `"greeter"` |
| `collected_fields` | `{}` |
| `verification_attempts` | `0` |
| `conversation_ended` | `False` |

## 5. Application Entry Point

The FastAPI application is defined in `app/main.py`. It:
1. Creates the `FastAPI` app instance with a title and version.
2. Includes the chat router from `app/api/v1/endpoints/chat.py`.
3. Adds a `GET /health` endpoint that returns `{"status": "ok"}`.

## 6. Error Handling

| Scenario | Behaviour |
| :--- | :--- |
| `conversation_ended = True` on a new message | Return a `ChatResponse` with `response = "This conversation has ended. Please start a new session."` without invoking the graph. |
| Graph invocation raises an exception | Return HTTP `500` with a generic error message. Do not expose internal error details. |
| Last message is not AIMessage | Return HTTP `500` with a generic error message. Log detailed error server-side. |
| Empty `message` field | Pydantic validation will return HTTP `422` automatically. |

## 7. Example Payloads

### Example Request

```json
{
  "session_id": "user-12345-session-001",
  "message": "I need help with my account"
}
```

### Example Response

```json
{
  "session_id": "user-12345-session-001",
  "response": "Hello! I'm here to help you today. Before we proceed, I need to verify your identity. May I have your date of birth?",
  "current_agent": "greeter",
  "is_authenticated": false,
  "conversation_ended": false
}
```

## 8. Success Criteria

- **Functional**: Endpoint successfully processes new and existing sessions with correct state persistence
- **Functional**: Conversation state (messages, authentication, agent) correctly carries over across multiple turns
- **Functional**: Error scenarios return appropriate HTTP status codes and messages
- **Performance**: Endpoint responds within 5 seconds under normal load (defined as: single request with mocked graph invocation, typical message length <500 chars)
- **Reliability**: Session state persists correctly for duration of server uptime

## 9. Test Scenarios

### Scenario 1: New Session Initialization

**Given**: No existing session with ID "test-001"  
**When**: POST /chat with `{"session_id": "test-001", "message": "Hello"}`  
**Then**: 
- Response returns 200 OK
- New GraphState created with default values
- `current_agent` is "greeter"
- `is_authenticated` is false

### Scenario 2: Existing Session Continuation

**Given**: Active session "test-001" with 2 prior messages  
**When**: POST /chat with `{"session_id": "test-001", "message": "My DOB is 1990-05-15"}`  
**Then**:
- Existing state loaded from SESSION_STORE
- New message appended to existing messages list
- Graph invoked with full conversation history
- Updated state saved back to SESSION_STORE

### Scenario 3: Ended Conversation

**Given**: Session "test-001" with `conversation_ended = True`  
**When**: POST /chat with new message  
**Then**:
- Returns 200 OK with message "This conversation has ended. Please start a new session."
- Graph is NOT invoked
- Session state remains unchanged

### Scenario 4: Validation Error

**Given**: Any state  
**When**: POST /chat with empty `message` field  
**Then**: Returns 422 Unprocessable Entity with validation error details

## 10. Clarifications

- The `SESSION_STORE` is in-memory and will be reset on server restart. This is intentional for this challenge.
- The API does NOT implement authentication or rate limiting. This is out of scope.
- The `current_agent` field in `ChatResponse` reflects the agent that handled the current turn, read from `state["current_agent"]`.
- The endpoint MUST be fully async (`async def`) to support the async graph invocation.
- CORS is not required for this challenge.
