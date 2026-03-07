# Tasks: LangGraph State

**Branch**: `002-graph-state`  
**Feature**: Implement LangGraph State object for DEUS Bank AI Support System  
**Input**: [spec.md](spec.md), [plan.md](plan.md)  

**Organization**: This is a foundational infrastructure feature. All tasks are essential blocking prerequisites for agent implementation.

## Format: `- [ ] [ID] [P?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create directory structure for graph module

- [X] T001 Create app/graph/ directory for LangGraph components
- [X] T002 Create app/graph/__init__.py to expose State and factory function

---

## Phase 2: Foundational (Core State Implementation)

**Purpose**: Implement the State TypedDict and initialization logic

**⚠️ CRITICAL**: This is the backbone of the entire agent pipeline - all agents depend on this

- [X] T003 Define State TypedDict with all 10 fields in app/graph/state.py
- [X] T004 Implement create_initial_state factory function in app/graph/state.py
- [X] T005 Add comprehensive docstrings explaining State fields and usage in app/graph/state.py

**Checkpoint**: State is defined and can be instantiated with defaults

---

## Phase 3: Validation

**Purpose**: Verify State definition and initialization logic

- [X] T006 [P] Test create_initial_state returns correct defaults in tests/test_graph_state.py
- [X] T007 [P] Test messages field uses add_messages reducer correctly in tests/test_graph_state.py
- [X] T008 [P] Test verified_user accepts None and User objects in tests/test_graph_state.py
- [X] T009 Run all tests to validate State implementation

**Checkpoint**: All tests pass - State is production-ready

---

## Phase 4: Documentation & Polish

**Purpose**: Ensure State module is well-documented and ready for agent development

- [X] T010 [P] Add module-level docstring to app/graph/state.py explaining State architecture
- [X] T011 [P] Update app/graph/__init__.py with proper exports and type hints
- [X] T012 Verify State can be imported from app.graph.state in Python REPL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) - directory must exist
- **Validation (Phase 3)**: Depends on Foundational (Phase 2) - State must be implemented
- **Documentation (Phase 4)**: Depends on all previous phases - polish after validation

### Task Dependencies Within Phases

**Phase 1 (Setup)**:
- T001 → T002 (directory before __init__.py)

**Phase 2 (Foundational)**:
- T003 → T004 (State definition before factory)
- T003, T004 → T005 (implementation before documentation)

**Phase 3 (Validation)**:
- T006, T007, T008 can run in parallel [P]
- All tests → T009 (individual tests before final validation)

**Phase 4 (Documentation)**:
- T010, T011 can run in parallel [P]
- T010, T011 → T012 (documentation before final verification)

### Parallel Opportunities

- **Phase 3**: Tasks T006, T007, T008 can be written in parallel (different test functions)
- **Phase 4**: Tasks T010, T011 can be completed in parallel (different files)

---

## Implementation Strategy

### Linear Execution (Recommended for Solo Developer)

1. Complete Phase 1 (2 tasks) - ~5 minutes
2. Complete Phase 2 (3 tasks) - ~30 minutes
3. Complete Phase 3 (4 tasks) - ~30 minutes
4. Complete Phase 4 (3 tasks) - ~15 minutes

**Total Estimated Time**: ~80 minutes

### Validation Checkpoints

- After Phase 1: `ls app/graph/` should show __init__.py
- After Phase 2: `python -c "from app.graph.state import State, create_initial_state"` should succeed
- After Phase 3: `pytest tests/test_graph_state.py -v` should show all tests passing
- After Phase 4: State module is ready for agent development

---

## Task Details

### Phase 1 Details

**T001**: Create app/graph/ directory
- Action: `mkdir app/graph` (or use IDE)
- Result: Directory exists at correct path

**T002**: Create app/graph/__init__.py
- Action: Create empty __init__.py file
- Result: Makes graph/ a Python package

### Phase 2 Details

**T003**: Define State TypedDict in app/graph/state.py
- Import: `TypedDict` from `typing_extensions`, `Annotated` from `typing`
- Import: `add_messages` from `langgraph.graph.message`
- Import: `BaseMessage` from `langchain_core.messages`
- Import: `User` from `app.models.schemas`
- Define: State class with 10 fields as per spec.md
- Fields:
  - `messages: Annotated[list[BaseMessage], add_messages]`
  - `session_id: str`
  - `current_agent: str`
  - `verified_user: User | None`
  - `is_authenticated: bool`
  - `customer_tier: str | None`
  - `verification_attempts: int`
  - `collected_fields: dict[str, str]`
  - `specialist_needed: bool`
  - `conversation_ended: bool`

**T004**: Implement create_initial_state factory function
- Signature: `def create_initial_state(session_id: str) -> State:`
- Returns: State dict with all default values from spec.md
- Defaults:
  - messages: []
  - session_id: provided parameter
  - current_agent: "greeter"
  - verified_user: None
  - is_authenticated: False
  - customer_tier: None
  - verification_attempts: 0
  - collected_fields: {}
  - specialist_needed: False
  - conversation_ended: False

**T005**: Add docstrings
- State class: Explain it's the shared data structure
- create_initial_state: Explain initialization purpose
- Each field: Brief comment on purpose (optional but helpful)

### Phase 3 Details

**T006**: Test create_initial_state defaults
- Import: `create_initial_state` from `app.graph.state`
- Test: Call with session ID, verify all fields match defaults
- Assert: session_id is set correctly, all other defaults are correct

**T007**: Test add_messages reducer
- Import: State types and test utilities
- Test: Simulate adding messages twice, verify they append
- Assert: Message list grows, doesn't overwrite

**T008**: Test verified_user field
- Import: `User` from `app.models.schemas`
- Test: State with verified_user=None
- Test: State with verified_user=User(...) instance
- Assert: Both work without type errors

**T009**: Run all tests
- Command: `pytest tests/test_graph_state.py -v`
- Verify: All tests pass with no errors

### Phase 4 Details

**T010**: Add module docstring
- Location: Top of app/graph/state.py
- Content: Explain State architecture, its role in pipeline
- Reference: spec.md sections 1-4

**T011**: Update __init__.py
- Export: `State`, `create_initial_state`
- Type stubs: Add `__all__` list

**T012**: Verify imports work
- Command: `python -c "from app.graph.state import State, create_initial_state; print('OK')"`
- Expected: "OK" printed without errors

---

## Notes

- State is shared across all agents - changes here affect entire pipeline
- Never expose `verified_user.answer` in responses (security requirement)
- The `add_messages` reducer is critical for conversation history
- All agents will import State from `app.graph.state`
- Tests are essential - State bugs will cascade to all agents

---

## Next Steps After Completion

Once all tasks are complete and tests pass:

1. **Commit changes**: `git add . && git commit -m "feat: implement LangGraph State"`
2. **Next feature**: Begin work on Guardrails agent (spec-guardrails.md)
3. **Agent development**: State is now available for all agent implementations
