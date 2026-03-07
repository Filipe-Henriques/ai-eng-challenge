# Tasks: LangGraph Pipeline

**Feature Branch**: `007-langgraph-pipeline`  
**Input**: Design documents from `specs/007-langgraph-pipeline/`  
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md)

**Note**: This feature is infrastructure (graph orchestration), not user-story based. Tasks are organized by implementation phases.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

This project uses single project structure with `app/` for source and `tests/` for tests.

---

## Phase 1: Module Setup

**Purpose**: Create the pipeline module structure and imports

- [ ] T001 Create app/graph/pipeline.py with module docstring and imports (StateGraph, START, END from langgraph.graph)
- [ ] T002 Add imports for GraphState from app.graph.state and agent functions (greeter_agent, bouncer_agent, specialist_agent)

**Checkpoint**: Module imports without errors

---

## Phase 2: Routing Functions

**Purpose**: Implement the three pure routing functions that control graph flow

**⚠️ Note**: These functions are pure (no side effects) and can be implemented in parallel

- [ ] T003 [P] Implement route_after_greeter(state: GraphState) -> str in app/graph/pipeline.py
- [ ] T004 [P] Implement route_after_bouncer(state: GraphState) -> str in app/graph/pipeline.py
- [ ] T005 [P] Implement route_after_specialist(state: GraphState) -> str in app/graph/pipeline.py

**Checkpoint**: All routing functions defined and return correct node names based on state

---

## Phase 3: Graph Assembly

**Purpose**: Build and compile the StateGraph with all nodes and edges

- [ ] T006 Implement build_graph() factory function in app/graph/pipeline.py
- [ ] T007 Add 5 nodes to workflow (greeter, bouncer, specialist_standard, specialist_premium, specialist_vip)
- [ ] T008 Set entry point to greeter node
- [ ] T009 Add conditional edge from greeter using route_after_greeter
- [ ] T010 Add conditional edge from bouncer using route_after_bouncer
- [ ] T011 Add conditional edges from all three specialist nodes using route_after_specialist
- [ ] T012 Compile graph with interrupt_after for all 5 nodes

**Checkpoint**: build_graph() returns compiled StateGraph without errors

---

## Phase 4: Module Export

**Purpose**: Export the compiled graph as module-level constant

- [ ] T013 Create module-level graph constant by calling build_graph() in app/graph/pipeline.py

**Checkpoint**: `from app.graph.pipeline import graph` works without errors, graph is ready for FastAPI layer

---

## Phase 5: Testing

**Purpose**: Verify routing logic and graph structure

- [ ] T014 Create tests/test_pipeline.py with test setup
- [ ] T015 [P] Write test_build_graph() to verify compilation succeeds
- [ ] T016 [P] Write test_route_after_greeter() for all three scenarios (ended, authenticated, waiting)
- [ ] T017 [P] Write test_route_after_bouncer() for all three tiers plus fallback
- [ ] T018 [P] Write test_route_after_specialist() for loop and termination
- [ ] T019 [P] Write test_graph_nodes() to verify all 5 nodes exist in compiled graph
- [ ] T020 [P] Write test_async_invocation() to verify graph.ainvoke() works with async execution
- [ ] T021 [P] Write test_interrupt_behavior() to verify interrupt_after pauses execution after each agent turn

**Checkpoint**: All pipeline tests pass (pytest tests/test_pipeline.py), routing functions are pure (no LLM calls needed), async and interrupt behavior validated

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Module Setup (Phase 1)**: No dependencies - start here
2. **Routing Functions (Phase 2)**: Depends on Phase 1 completion
3. **Graph Assembly (Phase 3)**: Depends on Phase 2 completion
4. **Module Export (Phase 4)**: Depends on Phase 3 completion
5. **Testing (Phase 5)**: Can start after Phase 2 (test routing functions) and Phase 4 (test graph)

### Within Each Phase

**Phase 1**: T001 → T002 (sequential)

**Phase 2**: All three routing functions [P] can be implemented in parallel:
- T003, T004, T005 (parallel)

**Phase 3**: Sequential order:
- T006 (create function) → T007 (add nodes) → T008 (entry point) → T009-T011 (edges) → T012 (compile)

**Phase 4**: Single task (T013)

**Phase 5**: Most tests [P] can run in parallel once routing functions exist:
- T014 (setup) → T015-T021 (all parallel)

### Parallel Opportunities

**Phase 2 - All routing functions can be implemented simultaneously**:
```bash
Task T003: route_after_greeter
Task T004: route_after_bouncer  
Task T005: route_after_specialist
```

**Phase 5 - All tests can be written in parallel after setup**:
```bash
Task T015: test_build_graph
Task T016: test_route_after_greeter
Task T017: test_route_after_bouncer
Task T018: test_route_after_specialist
Task T019: test_graph_nodes
Task T020: test_async_invocation
Task T021: test_interrupt_behavior
```

---

## Implementation Strategy

### Sequential Approach (Recommended for Single Developer)

1. **Phase 1**: Module Setup → imports work
2. **Phase 2**: Routing Functions → all routers correct
3. **Phase 3**: Graph Assembly → compiled graph ready
4. **Phase 4**: Module Export → graph importable
5. **Phase 5**: Testing → all tests pass

**Total**: ~7 core implementation tasks + 8 test tasks = **15 tasks** (was 13, added 2 for async/interrupt validation)

### Parallel Approach (If Multiple Developers Available)

1. Developer A: Phase 1 → Phase 3 → Phase 4 (graph implementation)
2. Developer B: Phase 2 → Phase 5 (routing functions + tests)
3. Once Phase 4 completes, Developer B can test full graph integration

---

## Next Steps

After completing this feature, the LangGraph Pipeline will be ready for integration with:
- **Feature 008**: FastAPI Endpoint (session management, graph invocation, streaming responses)
- The pipeline exposes `graph` which the API layer will call via `graph.ainvoke()` or `graph.astream()`

---

## Notes

- All routing functions are pure (no side effects, no LLM calls)
- The graph is stateless - all state passed in and returned on every invocation
- Three specialist nodes point to same specialist_agent function (tier differentiation via state)
- interrupt_after enables multi-turn conversation pattern
- Tests can run without LLM access (routing logic only)
- File: `app/graph/pipeline.py` (main implementation)
- File: `tests/test_pipeline.py` (test suite)
