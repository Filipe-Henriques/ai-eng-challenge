# Implementation Plan: Specialist Agent

**Branch**: `006-specialist-agent` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-specialist-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement the Specialist Agent, the third and final node in the DEUS Bank AI Support System LangGraph pipeline. The agent receives authenticated, routed customers and fulfils banking requests using tool-calling capabilities. It implements a ReAct-style agent via LangChain's `AgentExecutor`, adapts its persona based on customer tier (Standard/Premium/VIP), and provides multi-turn conversation support with four banking tools: account balance inquiry, transaction history retrieval, fund transfers, and lost card reporting. All operations use the in-memory mock database without external API calls.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: LangGraph, LangChain, OpenAI (gpt-4o-mini), Pydantic v2  
**Storage**: In-memory mock database (`app.models.database`)  
**Testing**: pytest + pytest-asyncio  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web service (AI agent system)  
**Performance Goals**: <3s for fund transfers, <2s for balance/card reports  
**Constraints**: Max 10 conversation turns, 1-20 transaction history items, basic IBAN validation only  
**Scale/Scope**: Single agent node with 4 tools, ~5-10 conversation turns per session

**Existing Infrastructure**:
- GraphState (State) TypedDict in `app/graph/state.py` with tier and intent fields
- User and Account models with tier in `app/models/schemas.py`
- Mock database access in `app/models/database.py`
- `run_guardrails()` function in `app/guardrails/guardrails.py`
- Greeter Agent (authentication) and Bouncer Agent (routing) already implemented

## Constitution Check

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture** | ✅ PASS | Specialist is a single node with well-defined scope: banking operations fulfillment. Does NOT authenticate (Greeter's job) or route (Bouncer's job). |
| **II. Safety First — Guardrails** | ✅ PASS | Spec requires guardrails on every turn for both input (user message) and output (agent response). Never exposes raw tool output, user IDs, or database references. |
| **III. Security by Design** | ✅ PASS | Operates only on authenticated customers (`is_authenticated=True`). Uses `verified_user.id` from state (never asks customer for ID). IBAN validation with basic format check. |
| **IV. Stateful Conversation** | ✅ PASS | Reads from and writes to GraphState. Maintains conversation history via `messages`, sets `conversation_ended` when resolved. Max 10-turn limit enforced. |
| **V. Clean Architecture** | ✅ PASS | Agent lives in `app/agents/specialist.py`. Tools defined inline with `@tool` decorator. Uses models from `app/models`, guardrails from `app/guardrails`, state from `app/graph`. |

**VERDICT**: ✅ All constitutional principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-specialist-agent/
├── spec.md              # Feature specification (complete, clarified)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (LangChain patterns, tools)
├── data-model.md        # Phase 1 output (Account model extensions)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (tool interfaces)
│   └── tool-interface.md
├── checklists/
│   └── requirements.md  # Specification quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── agents/
│   ├── greeter.py           # ✅ Greeter Agent (existing)
│   ├── bouncer.py           # ✅ Bouncer Agent (existing)
│   └── specialist.py        # 🆕 Specialist Agent implementation
├── graph/
│   ├── state.py             # ✅ GraphState with tier/intent (existing)
│   └── pipeline.py          # 📝 Update: add specialist node + routing
├── guardrails/
│   └── guardrails.py        # ✅ run_guardrails() (existing)
├── models/
│   ├── schemas.py           # 📝 Update: extend Account model with banking fields
│   └── database.py          # 📝 Update: add ACCOUNTS_DB with mock data
└── api/
    └── v1/
        └── endpoints/
            └── chat.py      # 📝 Update: wire specialist into graph

tests/
├── test_specialist.py       # 🆕 Specialist Agent and tools tests
├── test_greeter.py          # ✅ Existing
├── test_bouncer.py          # ✅ Existing
├── test_guardrails.py       # ✅ Existing
└── test_data_models.py      # 📝 Update: test extended Account model
```

**Legend**: 🆕 New file | 📝 Modified | ✅ Existing (no changes)

**Structure Decision**: Single-project Python web service. Specialist Agent is the final of three agents (Greeter → Bouncer → Specialist). Agent isolation via `app/agents/` directory follows Constitution Principle V (Clean Architecture). Tools are defined inline within specialist.py using LangChain's `@tool` decorator.

## Complexity Tracking

No constitutional violations. All principles satisfied—no complexity justification required.

---

## Phase 0: Research & Discovery ✅

**Status**: Complete  
**Artifacts**: [research.md](research.md)

**Key Decisions**:
1. **LangChain AgentExecutor with ReAct Pattern** — Use `create_tool_calling_agent()` + `AgentExecutor` for automatic tool orchestration
2. **Inline Tool Definitions** — Define tools with `@tool` decorator in `specialist.py` for colocated logic
3. **Tier-Based System Prompts** — Use Python f-strings with tier-specific persona constants
4. **Extended Account Model** — Add balance, currency, transactions, card_blocked to support all tools
5. **Basic IBAN Validation** — Format check only (15-34 chars, starts with 2 letters)
6. **Tool Retry Strategy** — Single retry attempt, then escalate to human advisor
7. **Turn Limit Enforcement** — Automatic termination at 10 turns (5 customer messages)
8. **Transaction History Limits** — Default 5, allow 1-20 on customer request

**Technologies Validated**:
- LangChain AgentExecutor (tool-calling agent pattern)
- OpenAI gpt-4o-mini function calling
- Pydantic v2 for extended models
- pytest for tool and agent testing

**Blockers**: None — all dependencies available, patterns established by existing agents

---

## Phase 1: Design & Contracts ✅

**Status**: Complete  
**Artifacts**: 
- [data-model.md](data-model.md) — Extended Account and Transaction models
- [contracts/tool-interface.md](contracts/tool-interface.md) — Banking tool API specifications
- [quickstart.md](quickstart.md) — Developer implementation guide

**New Data Models**:
1. `Transaction` (Pydantic) — date, description, amount for transaction history
2. Extended `Account` (Pydantic) — Added user_id, balance, currency, transactions list, card_blocked flag
3. `ACCOUNTS_DB` (dict[str, Account]) — Mock data with 3 accounts for testing

**Banking Tools Designed** (4 tools):
1. `get_account_balance(user_id)` → {balance, currency}
2. `get_transaction_history(user_id, limit=5)` → [transactions]
3. `transfer_funds(user_id, recipient_iban, amount, description)` → {success, transaction_id}
4. `report_lost_card(user_id)` → {success, case_id}

**Public Interface**:
```python
def specialist_agent(state: State) -> dict:
    """Main entry point — LangGraph node function with tool-calling capabilities."""
    pass
```

**Integration Points**:
- LangGraph: `builder.add_node("specialist", specialist_agent)`
- Routing: Bouncer → Specialist (if specialist_needed=True) → END
- State: Reads `verified_user`, `customer_tier`, `customer_intent`, `messages` | Writes `messages`, `conversation_ended`
- Tools access: ACCOUNTS_DB via user_id from verified_user
- Guardrails: Applied to both input and output on every turn

**Constitution Re-Check**: ✅ All principles still satisfied post-design

---
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
