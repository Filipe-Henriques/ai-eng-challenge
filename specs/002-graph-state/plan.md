# Implementation Plan: LangGraph State

## 1. Goal

Implement the LangGraph `State` object as defined in [spec.md](spec.md). The result will be a single, well-typed shared data structure that all agents and routing functions can read from and write to, forming the backbone of the entire pipeline.

**Note**: See [tasks.md](tasks.md) for the detailed 12-task breakdown of the 3 high-level tasks described below.

## 2. Technical Context

- **Library**: LangGraph (`langgraph.graph.message.add_messages`, `typing_extensions.TypedDict`, `typing.Annotated`).
- **Message Types**: LangGraph's `BaseMessage` from `langchain_core.messages`.
- **Pattern**: A `TypedDict` with typed fields and a single `Annotated` field for the message list, using LangGraph's `add_messages` reducer.

## 3. Task Breakdown

### Task 1: Implement the State TypedDict (`app/graph/state.py`)

- **Description**: Create the `State` class with all fields as defined in the spec.
- **Action**:
  1. Create `app/graph/state.py`.
  2. Import `TypedDict` from `typing_extensions`, `Annotated` from `typing`, `add_messages` from `langgraph.graph.message`, and `BaseMessage` from `langchain_core.messages`.
  3. Import the `User` model from `app/models/schemas.py`.
  4. Define the `State` class as a `TypedDict` with the following fields:
     - `messages: Annotated[list[BaseMessage], add_messages]`
     - `session_id: str`
     - `current_agent: str`
     - `verified_user: User | None`
     - `is_authenticated: bool`
     - `customer_tier: str | None`
     - `verification_attempts: int`
     - `collected_fields: dict`
     - `specialist_needed: bool`
     - `conversation_ended: bool`
- **Acceptance**: The `State` class is importable and can be instantiated with default values.

### Task 2: Define the Initial State Factory

- **Description**: Create a helper function that returns a fresh, fully initialised `State` dictionary for a new conversation session.
- **Action**:
  1. In `app/graph/state.py`, implement `create_initial_state(session_id: str) -> State`.
  2. The function returns a `State` dict with all default values as specified:
     - `messages`: `[]`
     - `session_id`: the provided `session_id`
     - `current_agent`: `"greeter"`
     - `verified_user`: `None`
     - `is_authenticated`: `False`
     - `customer_tier`: `None`
     - `verification_attempts`: `0`
     - `collected_fields`: `{}`
     - `specialist_needed`: `False`
     - `conversation_ended`: `False`
- **Acceptance**: `create_initial_state("session-123")` returns a valid `State` dict with `session_id == "session-123"` and all other fields at their defaults.

### Task 3: Write Unit Tests (`tests/test_graph_state.py`)

- **Description**: Verify the State definition and the initial state factory.
- **Action**:
  1. Create `tests/test_graph_state.py`.
  2. Test that `create_initial_state` returns a dict with all expected keys and correct default values.
  3. Test that the `messages` field correctly uses the `add_messages` reducer by simulating two state updates and verifying messages are appended, not overwritten.
  4. Test that `verified_user` accepts both `None` and a valid `User` object.
- **Acceptance**: All tests pass, confirming the state is correctly defined and initialised.

## 4. Next Steps

Once the State is implemented and tested, we will proceed to **spec-guardrails.md** to define the safety layer that all agents will depend on.
