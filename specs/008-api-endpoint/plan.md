# Implementation Plan: API Endpoint

**Branch**: `008-api-endpoint` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-api-endpoint/spec.md`

**Note**: This plan follows the `/speckit.plan` workflow. Generated on 2026-03-07.

## Summary

Implement the FastAPI endpoint that serves as the external interface for the DEUS Bank AI Support System. The endpoint exposes `POST /chat` to receive customer messages, manages session state in memory, invokes the LangGraph pipeline, and returns structured responses. The implementation includes request/response validation with Pydantic models, async graph invocation, proper error handling, and a health check endpoint. The API layer acts as a stateless orchestrator that maintains session state externally to the graph, enabling multi-turn conversations with proper state persistence across HTTP requests.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI (web framework), Pydantic v2 (data validation), LangGraph (graph invocation), LangChain Core (message types), uvicorn (ASGI server)  
**Storage**: In-memory session store (`dict[str, GraphState]` at module level) - no persistence required  
**Testing**: pytest with pytest-asyncio for async endpoint testing, FastAPI TestClient for integration tests, unittest.mock for graph mocking  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web service (REST API)  
**Performance Goals**: <5 seconds response time per request under normal load (as specified in success criteria)  
**Constraints**: Must be fully async to support async graph invocation; session store resets on server restart (intentional); no authentication or CORS required  
**Scale/Scope**: Supports concurrent sessions with in-memory state management; single endpoint with health check

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Pre-Research)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture with LangGraph** | ✅ PASS | API endpoint orchestrates graph invocation without implementing agent logic; stateless entry point that delegates to LangGraph pipeline |
| **II. Safety First — Guardrails as Cross-Cutting Concern** | ✅ PASS | API layer does not bypass guardrails; all safety checks remain within agents as designed; endpoint only manages session state and invocation |
| **III. Security by Design — Strict Verification** | ✅ PASS | API preserves authentication state from graph; does not implement or modify verification logic; respects `is_authenticated` flag in responses |
| **IV. Stateful Conversation History** | ✅ PASS | API is the session state manager per constitution; maintains conversation history via SESSION_STORE between graph invocations; enables stateful conversations |
| **V. Clean Architecture — Separation of Concerns** | ✅ PASS | New code lives in `app/api/v1/endpoints/chat.py` and `app/main.py` per constitution Section 4; clear separation between API layer (session management) and graph layer (business logic) |

**Technology Stack Alignment**:
- ✅ Uses FastAPI per constitution Section 3
- ✅ Uses Pydantic v2 per constitution Section 3
- ✅ Testing with pytest per constitution Section 3
- ✅ Follows Google Style docstring standard per constitution Section 5

**Project Structure Alignment**:
- ✅ Will create `app/main.py` as specified in constitution Section 4
- ✅ Will create `app/api/` directory (new) with chat endpoint per constitution patterns
- ✅ Will create `tests/test_api.py` per constitution testing requirements

**Gate Result**: ✅ **PASS** - All constitutional principles satisfied; no violations or justifications needed.

## Project Structure

### Documentation (this feature)

```text
specs/008-api-endpoint/
├── spec.md              # Feature specification (input)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (generated below)
├── data-model.md        # Phase 1 output (generated below)
├── quickstart.md        # Phase 1 output (generated below)
├── contracts/           # Phase 1 output (generated below)
│   └── api-contract.md  # HTTP API contract (endpoint, models, error codes)
├── checklists/          # Quality validation
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # NOT created by /speckit.plan (use /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── main.py                  # NEW: FastAPI application entry point
├── api/                     # NEW: This feature
│   ├── __init__.py          # NEW
│   └── v1/                  # NEW: API version 1
│       ├── __init__.py      # NEW
│       └── endpoints/       # NEW
│           ├── __init__.py  # NEW
│           └── chat.py      # NEW: Chat endpoint, SESSION_STORE, request handler
├── models/                  # EXISTING: From spec 001
│   ├── __init__.py
│   ├── schemas.py           # MODIFIED: Add ChatRequest and ChatResponse (if not present)
│   └── database.py          # EXISTING: Mock in-memory data store
├── graph/                   # EXISTING: From spec 002, 007
│   ├── __init__.py
│   ├── state.py             # EXISTING: GraphState definition
│   └── pipeline.py          # EXISTING: Compiled graph to be invoked
├── agents/                  # EXISTING: From specs 004, 005, 006
│   ├── greeter.py
│   ├── bouncer.py
│   └── specialist.py
├── guardrails/              # EXISTING: From spec 003
│   └── guardrails.py
└── __init__.py

tests/
├── test_api.py              # NEW: Integration tests for /chat endpoint
├── test_pipeline.py         # EXISTING: From spec 007
├── test_specialist.py       # EXISTING: From spec 006
├── test_bouncer.py          # EXISTING: From spec 005
├── test_greeter.py          # EXISTING: From spec 004
├── test_guardrails.py       # EXISTING: From spec 003
├── test_graph_state.py      # EXISTING: From spec 002
└── test_data_models.py      # EXISTING: From spec 001
```

**Structure Decision**: Single project layout per constitution Section 4. The API layer is a new module that provides the HTTP interface to the existing LangGraph pipeline. `app/main.py` is the application entry point that wires together the FastAPI app and includes the chat router from `app/api/v1/endpoints/chat.py`. All API logic is contained within `app/api/v1/endpoints/` to maintain separation of concerns and enable API versioning (Constitution Principle V). The SESSION_STORE lives in `app/api/v1/endpoints/chat.py` as a module-level variable, keeping session management isolated from business logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations**: Constitution Check passed completely. No complexity justifications required.

---

## Phase 0: Research & Discovery

*Objective: Resolve unknowns and establish best practices for implementation*

Research artifacts generated: [research.md](research.md)

---

## Phase 1: Design Artifacts

*Objective: Define data models, contracts, and usage patterns*

Design artifacts generated:
- [data-model.md](data-model.md) - ChatRequest and ChatResponse Pydantic models
- [contracts/api-contract.md](contracts/api-contract.md) - HTTP API contract specification
- [quickstart.md](quickstart.md) - API usage guide and integration examples

---

## Post-Design Constitution Check

*Re-evaluate after Phase 1 design artifacts are complete*

### Design Review (Post-Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture with LangGraph** | ✅ PASS | API design confirms clean separation: endpoint orchestrates without implementing logic; all agent behavior remains in graph nodes |
| **II. Safety First — Guardrails as Cross-Cutting Concern** | ✅ PASS | API does not bypass safety layer; guardrails remain integrated in agent nodes; endpoint only manages HTTP layer |
| **III. Security by Design — Strict Verification** | ✅ PASS | API preserves authentication state; verification logic stays in Greeter agent; endpoint respects `is_authenticated` without modifying it |
| **IV. Stateful Conversation History** | ✅ PASS | SESSION_STORE design enables full conversation history persistence; messages accumulate across turns; state managed externally to graph per architecture |
| **V. Clean Architecture — Separation of Concerns** | ✅ PASS | Implementation in `app/api/v1/endpoints/chat.py` and `app/main.py` per constitution; clear separation: API (HTTP/session), Graph (business logic), Agents (domain) |

**Artifacts Review**:
- ✅ `data-model.md`: ChatRequest/ChatResponse models align with Pydantic v2 requirement
- ✅ `contracts/api-contract.md`: Complete HTTP contract with status codes, error handling, behavioral guarantees
- ✅ `quickstart.md`: Implementation patterns follow FastAPI best practices; testing with TestClient per constitution
- ✅ `research.md`: All decisions (async handlers, in-memory sessions, HTTPException) align with constitution stack

**Technology Additions**:
- ✅ FastAPI - already in stack (constitution Section 3)
- ✅ Pydantic v2 - already in stack (constitution Section 3)
- ✅ uvicorn - added to agent context (ASGI server for FastAPI)
- ✅ LangGraph/LangChain Core - already in stack (constitution Section 3)

**Structure Additions**:
- ✅ `app/main.py` - new file per constitution Section 4
- ✅ `app/api/v1/endpoints/` - new directory structure per constitution Section 4
- ✅ `tests/test_api.py` - new test file per constitution Section 4

**Model Modifications Required**:
- ⚠️ `app/models/schemas.py` - ChatResponse needs 2 new fields (`is_authenticated`, `conversation_ended`) and 1 rename (`agent` → `current_agent`)

**Gate Result**: ✅ **PASS** - Design maintains full constitutional compliance. Ready for implementation.

---

## Next Steps

1. ✅ **Phase 0 Complete**: Generated [research.md](research.md) with best practices for FastAPI async design, session management, error handling, LangGraph integration, and testing
2. ✅ **Phase 1 Complete**: Generated design artifacts:
   - [data-model.md](data-model.md) - ChatRequest and ChatResponse Pydantic models
   - [contracts/api-contract.md](contracts/api-contract.md) - Complete HTTP API contract
   - [quickstart.md](quickstart.md) - Implementation guide with code examples and testing patterns
3. ✅ **Agent Context Updated**: Added uvicorn, in-memory session management to technology stack
4. ✅ **Post-Design Check**: Constitution compliance verified - all gates passed
5. ⏳ **Phase 2 Pending**: Use `/speckit.tasks` command to generate [tasks.md](tasks.md) with implementation tasks

**Planning Complete** - Ready for task generation and implementation.
