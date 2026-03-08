# Spec: LangGraph Pipeline — DEUS Bank AI Support System

## 1. Description

This spec defines the **LangGraph Pipeline**, the central orchestration layer of the system. It wires together the three agents (Greeter, Bouncer, Specialist) into a compiled `StateGraph` that manages the full conversation lifecycle. It lives in `app/graph/pipeline.py`.

The pipeline is the single source of truth for conversation routing. It defines which agent runs next based on the current state, enforcing the correct flow without any agent needing to know about the others.

## 2. Graph Structure

The pipeline is a `StateGraph` built on top of `GraphState`. It has the following nodes and edges:

### Nodes

| Node Name | Function | Description |
| :--- | :--- | :--- |
| `greeter` | `greeter_agent` | Handles identity verification and authentication |
| `bouncer` | `bouncer_agent` | Classifies intent and routes to specialist |
| `specialist_standard` | `specialist_agent` | Serves standard-tier customers |
| `specialist_premium` | `specialist_agent` | Serves premium-tier customers |
| `specialist_vip` | `specialist_agent` | Serves VIP-tier customers |

Note: All three specialist nodes point to the **same** `specialist_agent` function. The tier-specific behaviour is handled internally by the agent via the `customer_tier` state field.

### Entry Point

The graph entry point is always the `greeter` node.

### Edges

| From | To | Condition |
| :--- | :--- | :--- |
| `START` | `greeter` | Always (entry point) |
| `greeter` | `END` | `conversation_ended = True` OR `is_authenticated = False` (still verifying) |
| `greeter` | `bouncer` | `is_authenticated = True` |
| `bouncer` | `specialist_standard` | `current_agent = "specialist_standard"` |
| `bouncer` | `specialist_premium` | `current_agent = "specialist_premium"` |
| `bouncer` | `specialist_vip` | `current_agent = "specialist_vip"` |
| `specialist_*` | `END` | `conversation_ended = True` |
| `specialist_*` | `specialist_*` | `conversation_ended = False` (loop back for multi-turn) |

## 3. Conditional Routing Logic

All routing decisions are made by **conditional edge functions** — pure Python functions that inspect the state and return the name of the next node (as a string) or the `END` symbol (imported from `langgraph.graph`).

### `route_after_greeter(state: GraphState) -> str`

```python
from langgraph.graph import END

if state["conversation_ended"]:
    return END  # Symbol, not string
if state["is_authenticated"]:
    return "bouncer"  # Node name as string
return END  # waiting for next user message
```

### `route_after_bouncer(state: GraphState) -> str`

```python
# Return the tier-specific specialist node name
current = state["current_agent"]
if current in ["specialist_standard", "specialist_premium", "specialist_vip"]:
    return current
# Defensive fallback for unexpected values
return "specialist_standard"
```

### `route_after_specialist(state: GraphState) -> str`

```python
if state["conversation_ended"]:
    return END  # Symbol, not string
return state["current_agent"]  # loop back to same specialist
```

## 4. Graph Compilation

The compiled graph is exported as a module-level constant `graph` from `app/graph/pipeline.py`. It is the object that the FastAPI endpoint will call.

```python
# app/graph/pipeline.py

graph = build_graph()  # returns a compiled StateGraph
```

The `build_graph()` factory function constructs and compiles the graph. This pattern makes the graph testable by allowing tests to call `build_graph()` independently.

## 5. Session Management

The pipeline does NOT manage sessions itself. Session state is managed externally by the FastAPI layer (Spec 8). Each call to `graph.invoke()` or `graph.astream()` receives the full `GraphState` for that session, including the complete messages history.

The pipeline is stateless between invocations. All state is passed in and returned on every call.

## 6. Async Support

The compiled graph MUST support async invocation via `graph.ainvoke()`. All agent functions MUST be defined as `async def` to support this. LangChain's AgentExecutor supports async via `.ainvoke()`.

## 7. Interrupt Behaviour

The graph uses `interrupt_after` to pause execution after each agent turn and return control to the FastAPI layer. This is what enables the multi-turn conversation pattern: the graph runs one agent turn, returns the updated state, and waits for the next user message before resuming.

The `interrupt_after` nodes are: `["greeter", "bouncer", "specialist_standard", "specialist_premium", "specialist_vip"]`.

## 8. Clarifications

- The `specialist_standard`, `specialist_premium`, and `specialist_vip` nodes all call the same `specialist_agent` function. This is intentional — it avoids code duplication while still allowing the graph to route to the correct node name.
- The graph does NOT use LangGraph's built-in checkpointing or persistence. Session state is managed by the FastAPI layer using an in-memory dictionary.
- The `END` node is LangGraph's built-in terminal node imported from `langgraph.graph`.
- The graph MUST be compiled with `graph.compile(interrupt_after=[...])` to enable the multi-turn pattern.
