# Implementation Plan: LangGraph Pipeline

## 1. Goal

Implement the LangGraph Pipeline as defined in `spec-langgraph-pipeline.md`. The result will be a compiled `StateGraph` exported as a module-level `graph` constant from `app/graph/pipeline.py`. This is the central orchestration object that the FastAPI layer will invoke on every conversation turn.

## 2. Technical Context

- **Framework**: LangGraph `StateGraph` with `GraphState` as the state schema.
- **Nodes**: 5 nodes  `greeter`, `bouncer`, `specialist_standard`, `specialist_premium`, `specialist_vip`.
- **Edges**: Conditional edges driven by pure routing functions.
- **Pattern**: `interrupt_after` on every node to enable multi-turn conversation.
- **File Location**: `app/graph/pipeline.py`.
- **Exports**: `graph` (compiled) and `build_graph()` (factory function for testing).

## 3. Task Breakdown

### Task 1: Set Up the Module and Imports

- **Description**: Create the pipeline module with all necessary imports.
- **Action**:
  1. Create `app/graph/pipeline.py`.
  2. Import `StateGraph`, `START`, `END` from `langgraph.graph`.
  3. Import `GraphState` from `app.graph.state`.
  4. Import `greeter_agent` from `app.agents.greeter`.
  5. Import `bouncer_agent` from `app.agents.bouncer`.
  6. Import `specialist_agent` from `app.agents.specialist`.
- **Acceptance**: The module imports without errors.

### Task 2: Implement the `route_after_greeter` Conditional Edge

- **Description**: Define the routing function that decides what happens after the Greeter Agent runs.
- **Action**:
  1. Define `route_after_greeter(state: GraphState) -> str`.
  2. If `state["conversation_ended"]` is `True`, return `END`.
  3. If `state["is_authenticated"]` is `True`, return `"bouncer"`.
  4. Otherwise, return `END` (conversation is paused, waiting for the next user message).
- **Acceptance**: The function returns the correct node name for all three scenarios.

### Task 3: Implement the `route_after_bouncer` Conditional Edge

- **Description**: Define the routing function that decides which specialist to route to after the Bouncer Agent runs.
- **Action**:
  1. Define `route_after_bouncer(state: GraphState) -> str`.
  2. Return `state["current_agent"]` directly (one of `"specialist_standard"`, `"specialist_premium"`, `"specialist_vip"`).
  3. Add a defensive fallback: if `state["current_agent"]` is not one of the three valid values, return `"specialist_standard"`.
- **Acceptance**: The function correctly maps all three tier values and handles unexpected values gracefully.

### Task 4: Implement the `route_after_specialist` Conditional Edge

- **Description**: Define the routing function that decides whether the specialist loops or ends.
- **Action**:
  1. Define `route_after_specialist(state: GraphState) -> str`.
  2. If `state["conversation_ended"]` is `True`, return `END`.
  3. Otherwise, return `state["current_agent"]` to loop back to the same specialist node.
- **Acceptance**: The function correctly loops the specialist for multi-turn conversations and terminates when done.

### Task 5: Implement the `build_graph()` Factory Function

- **Description**: Assemble and compile the full `StateGraph`.
- **Action**:
  1. Define `build_graph() -> CompiledStateGraph`.
  2. Instantiate `workflow = StateGraph(GraphState)`.
  3. **Add nodes**:
     - `workflow.add_node("greeter", greeter_agent)`
     - `workflow.add_node("bouncer", bouncer_agent)`
     - `workflow.add_node("specialist_standard", specialist_agent)`
     - `workflow.add_node("specialist_premium", specialist_agent)`
     - `workflow.add_node("specialist_vip", specialist_agent)`
  4. **Set entry point**: `workflow.set_entry_point("greeter")`
  5. **Add conditional edge from `greeter`**:
     ```python
     workflow.add_conditional_edges(
         "greeter",
         route_after_greeter,
         {"bouncer": "bouncer", END: END}
     )
     ```
  6. **Add conditional edge from `bouncer`**:
     ```python
     workflow.add_conditional_edges(
         "bouncer",
         route_after_bouncer,
         {
             "specialist_standard": "specialist_standard",
             "specialist_premium": "specialist_premium",
             "specialist_vip": "specialist_vip",
         }
     )
     ```
  7. **Add conditional edges from each specialist node** (same logic for all three):
     ```python
     for node in ["specialist_standard", "specialist_premium", "specialist_vip"]:
         workflow.add_conditional_edges(
             node,
             route_after_specialist,
             {node: node, END: END}
         )
     ```
  8. **Compile** with interrupt support:
     ```python
     return workflow.compile(
         interrupt_after=[
             "greeter",
             "bouncer",
             "specialist_standard",
             "specialist_premium",
             "specialist_vip",
         ]
     )
     ```
- **Acceptance**: `build_graph()` returns a compiled graph without errors. The graph's structure matches the spec.

### Task 6: Export the Module-Level `graph` Constant

- **Description**: Create the singleton graph instance used by the FastAPI layer.
- **Action**:
  1. At the bottom of `app/graph/pipeline.py`, add: `graph = build_graph()`.
- **Acceptance**: `from app.graph.pipeline import graph` works without errors.

### Task 7: Write Unit Tests (`tests/test_pipeline.py`)

- **Description**: Verify the graph structure and routing logic.
- **Action**:
  1. Create `tests/test_pipeline.py`.
  2. **Test `build_graph`**: Assert that `build_graph()` returns a compiled graph without raising exceptions.
  3. **Test `route_after_greeter`**: Assert correct output for all three state scenarios (ended, authenticated, still verifying).
  4. **Test `route_after_bouncer`**: Assert correct output for all three tier values and the defensive fallback.
  5. **Test `route_after_specialist`**: Assert correct output for both the loop and termination scenarios.
  6. **Test graph nodes**: Assert that the compiled graph contains all five expected nodes.
- **Acceptance**: All pipeline tests pass without requiring any LLM calls (routing functions are pure).

## 4. Next Steps

With the pipeline wired up, the next step is to expose it via the **FastAPI Endpoint** defined in `spec-api-endpoint.md`. The API layer will manage sessions, receive user messages, invoke the graph, and return the agent's response.
