# Implementation Plan: Greeter Agent

**Branch**: `004-greeter-agent` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-greeter-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement the Greeter Agent, the first node in the DEUS Bank AI Support System LangGraph pipeline. The agent welcomes customers, incrementally collects their identifying information (name, phone, IBAN), verifies their identity using the 2-out-of-3 rule with case-insensitive name matching, and authenticates them via a secret question. The agent handles verification failures gracefully (max 3 attempts), includes database failure retry logic, and applies guardrails to all inputs and outputs.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: LangGraph, LangChain, OpenAI (gpt-4o-mini), Pydantic v2, FastAPI  
**Storage**: In-memory mock database (`app.models.database`)  
**Testing**: pytest + pytest-asyncio  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web service (AI agent system)  
**Performance Goals**: <2s response time for verification workflow  
**Constraints**: Max 3 verification attempts per session, single retry on database error  
**Scale/Scope**: Single agent node, ~5-10 conversation turns per session

**Existing Infrastructure**:
- GraphState TypedDict defined in `app/graph/state.py`
- User model with `secret` and `answer` fields in `app/models/schemas.py`
- `find_user_by_fields()` function in `app/models/database.py` (implements 2/3 matching)
- `run_guardrails()` function in `app/guardrails/guardrails.py`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture** | ✅ PASS | Greeter is a single node with well-defined scope: welcome, collect, verify, authenticate. Does NOT classify tier or route (Bouncer's job). |
| **II. Safety First — Guardrails** | ✅ PASS | Spec requires guardrails on both input (user message) and output (agent response). PII protection enforced (no exposure of `answer` field). |
| **III. Security by Design** | ✅ PASS | Implements 2/3 verification rule with exact matching requirements. Name is case-insensitive, phone/IBAN exact. Max 3 attempts enforced. |
| **IV. Stateful Conversation** | ✅ PASS | Reads from and writes to GraphState. Maintains `collected_fields`, `verification_attempts`, `verified_user`, and conversation history via `messages`. |
| **V. Clean Architecture** | ✅ PASS | Agent lives in `app/agents/greeter.py`. Uses models from `app/models`, guardrails from `app/guardrails`, state from `app/graph`. |

**VERDICT**: ✅ All constitutional principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-greeter-agent/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (dependencies & patterns)
├── data-model.md        # Phase 1 output (Pydantic models)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (public interfaces)
│   └── agent-interface.md
├── checklists/
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── agents/
│   └── greeter.py           # 🆕 Greeter Agent implementation
├── graph/
│   ├── state.py             # ✅ GraphState TypedDict (existing)
│   └── pipeline.py          # 📝 Update: add greeter node
├── guardrails/
│   └── guardrails.py        # ✅ run_guardrails() (existing)
├── models/
│   ├── schemas.py           # ✅ User model (existing)
│   └── database.py          # ✅ find_user_by_fields() (existing)
└── api/
    └── v1/
        └── endpoints/
            └── chat.py      # 📝 Update: wire greeter into graph

tests/
├── test_greeter.py          # 🆕 Greeter Agent tests
├── test_guardrails.py       # ✅ Existing
└── test_data_models.py      # ✅ Existing
```

**Legend**: 🆕 New file | 📝 Modified | ✅ Existing (no changes)

**Structure Decision**: Single-project Python web service. Greeter Agent is the first of three agents (Greeter → Bouncer → Specialist). Agent isolation via `app/agents/` directory follows Constitution Principle V (Clean Architecture).

## Complexity Tracking

No constitutional violations. All principles satisfied—no complexity justification required.

---

## Phase 0: Research & Discovery ✅

**Status**: Complete  
**Artifacts**: [research.md](research.md)

**Key Decisions**:
1. **LangChain Structured Output** — Use `with_structured_output()` with Pydantic models for field extraction
2. **LangGraph Node Pattern** — Agent signature: `(State) -> dict`, return partial state updates
3. **Database Retry Strategy** — Single immediate retry on failure, then graceful termination
4. **Case-Insensitive Matching** — `.lower()` for name comparison, exact for phone/IBAN
5. **Testing Strategy** — Mock LLM/database responses for fast, deterministic unit tests
6. **Guardrails Integration** — Dual guardrails (input + output) within agent function

**Technologies Validated**:
- LangChain `ChatOpenAI` with `gpt-4o-mini`
- Pydantic v2 for data models
- LangGraph state management
- pytest + unittest.mock for testing

**Blockers**: None — all dependencies available and patterns established

---

## Phase 1: Design & Contracts ✅

**Status**: Complete  
**Artifacts**: 
- [data-model.md](data-model.md) — Pydantic models and state schema
- [contracts/agent-interface.md](contracts/agent-interface.md) — Public API contract
- [quickstart.md](quickstart.md) — Developer implementation guide

**New Data Models**:
1. `ExtractedInfo` (Pydantic) — Internal model for LLM structured output
2. `DatabaseUnavailableError` (Exception) — Distinguishes DB failures from "no match"

**State Schema** (no changes required):
- All required fields already exist in `app/graph/state.py`
- Agent reads: `messages`, `collected_fields`, `verification_attempts`, `verified_user`, `is_authenticated`
- Agent writes: All of the above plus `current_agent`, `conversation_ended`

**Public Interface**:
```python
def greeter_agent(state: State) -> dict:
    """Main entry point — LangGraph node function."""
    pass
```

**Integration Points**:
- LangGraph: `builder.add_node("greeter", greeter_agent)`
- Routing: After greeter → "bouncer" (if authenticated) or "end" (if conversation ended)
- Dependencies: `find_user_by_fields()`, `run_guardrails()`, OpenAI LLM

---

## Constitution Check (Post-Design) ✅

**Re-evaluated after Phase 1 design completion**

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture** | ✅ PASS | Design confirms single-responsibility node. Clear handoff to Bouncer via `current_agent="bouncer"`. |
| **II. Safety First — Guardrails** | ✅ PASS | Dual guardrails implemented in quickstart (input before processing, output before return). PII protection in contract. |
| **III. Security by Design** | ✅ PASS | 2/3 verification with retry logic in data model. `answer` field never exposed (see security contract). |
| **IV. Stateful Conversation** | ✅ PASS | State read/write contract defined. Uses `add_messages` for history. Incremental field collection via `collected_fields`. |
| **V. Clean Architecture** | ✅ PASS | File structure validated: `app/agents/greeter.py`, dependencies from `app/models`, `app/guardrails`, `app/graph`. |

**VERDICT**: ✅ All principles still satisfied post-design. Design artifacts align with constitution.

---

## Implementation Readiness

**Ready to Proceed**: ✅ Yes

**Artifacts Generated**:
- ✅ research.md — Technical decisions documented
- ✅ data-model.md — All data structures defined
- ✅ contracts/agent-interface.md — Public API contract
- ✅ quickstart.md — Step-by-step implementation guide
- ✅ Agent context updated — GitHub Copilot context file

**Next Command**: `/speckit.tasks`

**Next Phase**: Task generation (Phase 2)
- Break down implementation into concrete, actionable tasks
- Define acceptance criteria for each task
- Establish dependency order
- Generate tasks.md

---

## Summary for Implementation Team

**What**: Implement Greeter Agent — first node in DEUS Bank AI Support System

**Core Workflow**:
1. Welcome customer
2. Extract identity fields (name, phone, IBAN) via LLM
3. Verify identity (2/3 match with database)
4. Ask secret question
5. Authenticate customer
6. Hand off to Bouncer Agent

**Key Technical Patterns**:
- LangChain structured output for field extraction
- LangGraph state management for conversation flow
- Retry-once pattern for database failures
- Dual guardrails (input/output)
- Case-insensitive name matching, exact phone/IBAN

**Testing Approach**:
- Mock LLM responses for deterministic tests
- Mock database lookups
- Unit test each stage independently
- Integration test full conversation flow

**File Locations**:
- Implementation: `app/agents/greeter.py`
- Tests: `tests/test_greeter.py`
- State: `app/graph/state.py` (existing)
- Models: `app/models/` (existing)

**Estimated Complexity**: Medium
- ~200-300 lines of code
- ~10-15 unit tests
- 1-2 days implementation + testing

**Branch**: `004-greeter-agent`  
**Spec**: [spec.md](spec.md)  
**Developer Guide**: [quickstart.md](quickstart.md)
