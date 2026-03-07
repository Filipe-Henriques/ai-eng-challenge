# Implementation Plan: Guardrails System

**Branch**: `003-guardrails` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-guardrails/spec.md`

**Note**: This plan follows the `/speckit.plan` workflow. Generated on 2026-03-07.

## Summary

Implement a composable safety layer that ensures all customer interactions are safe, professional, on-topic, and compliant with banking regulations. The guardrails system provides three independent checks (toxicity detection, topic filtering, PII protection) orchestrated through a single evaluation function. This layer is a cross-cutting concern that must be applied at every agent node in the LangGraph pipeline to protect customers, employees, and the bank from harmful, inappropriate, or non-compliant interactions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: OpenAI API (gpt-4o-mini for toxicity/topic classification), Pydantic v2 (data validation), Python re module (PII regex detection)  
**Storage**: N/A (stateless evaluation functions)  
**Testing**: pytest with unittest.mock for LLM call mocking  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Library module (safety layer integrated into LangGraph pipeline)  
**Performance Goals**: <500ms per guardrail evaluation for 95% of requests; <200ms average processing time  
**Constraints**: Fail-closed on errors (block conversation vs allow unchecked content); <5% false positive rate; 99% toxicity detection accuracy  
**Scale/Scope**: Must handle 1000+ concurrent evaluations without degradation; applies to every message in every conversation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Pre-Research)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture with LangGraph** | ✅ PASS | Guardrails integrate as a cross-cutting concern at every agent node; evaluation functions are pure and composable within the graph |
| **II. Safety First — Guardrails as Cross-Cutting Concern** | ✅ PASS | This feature IS the guardrails implementation mandated by the constitution; implements all three required checks (topic filtering, PII protection, toxicity) |
| **III. Security by Design — Strict Verification** | ✅ PASS | PII protection respects `is_authenticated` flag from verification system; prevents data leakage to unverified users |
| **IV. Stateful Conversation History** | ✅ PASS | Guardrails are stateless functions that operate on messages without modifying conversation history; compatible with State-based architecture |
| **V. Clean Architecture — Separation of Concerns** | ✅ PASS | All guardrail logic lives in `app/guardrails/guardrails.py` as mandated; agents call guardrails without implementing safety logic |

**Technology Stack Alignment**:
- ✅ Uses `gpt-4o-mini` (OpenAI API) for toxicity/topic classification per constitution
- ✅ Uses Pydantic v2 for `GuardrailResult` model per constitution
- ✅ Testing with pytest per constitution
- ✅ Follows Google Style docstring standard per constitution

**Project Structure Alignment**:
- ✅ Will create `app/guardrails/guardrails.py` as specified in constitution Section 4
- ✅ Will create `tests/test_guardrails.py` as specified in constitution Section 4

**Gate Result**: ✅ **PASS** - All constitutional principles satisfied; no violations or justifications needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-guardrails/
├── spec.md              # Feature specification (input)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (generated below)
├── data-model.md        # Phase 1 output (generated below)
├── quickstart.md        # Phase 1 output (generated below)
├── contracts/           # Phase 1 output (generated below)
│   └── guardrails.md    # Public API contract for guardrail system
├── checklists/          # Quality validation
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # NOT created by /speckit.plan (use /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── guardrails/              # NEW: This feature
│   ├── __init__.py
│   └── guardrails.py        # All guardrail functions and GuardrailResult model
├── models/                  # EXISTING: From spec 001
│   ├── schemas.py           # Pydantic models (User, Account, ChatRequest, ChatResponse)
│   └── database.py          # Mock in-memory data store
├── graph/                   # EXISTING: From spec 002
│   ├── state.py             # LangGraph State definition
│   └── __init__.py
└── __init__.py

tests/
├── test_guardrails.py       # NEW: Unit tests for this feature
├── test_data_models.py      # EXISTING: From spec 001
└── test_graph_state.py      # EXISTING: From spec 002
```

**Structure Decision**: Single project layout per constitution Section 4. The guardrails module is a new library component that provides safety functions callable from any agent node. All guardrail logic is contained in `app/guardrails/guardrails.py` to maintain separation of concerns (Constitution Principle V).

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
- [data-model.md](data-model.md) - GuardrailResult model structure
- [contracts/guardrails.md](contracts/guardrails.md) - Public API contract
- [quickstart.md](quickstart.md) - Integration guide for agents

---

## Post-Design Constitution Check

*Re-evaluate after Phase 1 design artifacts are complete*

### Design Review (Post-Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Multi-Agent Architecture with LangGraph** | ✅ PASS | Design confirms stateless functions integrate cleanly; no state mutations |
| **II. Safety First — Guardrails as Cross-Cutting Concern** | ✅ PASS | Complete API contract ensures all agents can integrate consistently; three checks implemented per constitution |
| **III. Security by Design — Strict Verification** | ✅ PASS | PII protection contract explicitly respects `is_authenticated` flag; fail-closed on errors |
| **IV. Stateful Conversation History** | ✅ PASS | GuardrailResult design shows agents update state appropriately without guardrails modifying it |
| **V. Clean Architecture — Separation of Concerns** | ✅ PASS | All logic in `app/guardrails/guardrails.py`; clear separation from agent responsibilities |

**Artifacts Review**:
- ✅ `data-model.md`: GuardrailResult model aligns with Pydantic v2 requirement
- ✅ `contracts/guardrails.md`: Single entry point per constitution (agents call orchestrator, not individual checks)
- ✅ `quickstart.md`: Integration patterns follow LangGraph state-based architecture
- ✅ `research.md`: All technology choices (gpt-4o-mini, Python re, fail-closed) align with stack

**Technology Additions**:
- ✅ OpenAI API (`gpt-4o-mini`) - added to agent context
- ✅ Python `re` module - stdlib, no new dependency
- ✅ Pydantic v2 - already in stack

**Structure Additions**:
- ✅ `app/guardrails/` - new directory per constitution Section 4
- ✅ `tests/test_guardrails.py` - new test file per constitution Section 4

**Gate Result**: ✅ **PASS** - Design maintains full constitutional compliance. Ready for implementation.

---

## Next Steps

1. ✅ **Phase 0 Complete**: Generated [research.md](research.md) with best practices for LLM-based moderation, PII detection, and fail-closed error handling
2. ✅ **Phase 1 Complete**: Generated design artifacts:
   - [data-model.md](data-model.md) - GuardrailResult Pydantic model specification
   - [contracts/guardrails.md](contracts/guardrails.md) - Public API contract for `run_guardrails()`
   - [quickstart.md](quickstart.md) - Integration guide with patterns and examples
3. ✅ **Agent Context Updated**: Added OpenAI API, Pydantic v2, Python re to technology stack
4. ✅ **Post-Design Check**: Constitution compliance verified - all gates passed
5. ⏳ **Phase 2 Pending**: Use `/speckit.tasks` command to generate [tasks.md](tasks.md) with implementation tasks

**Planning Complete** - Ready for task generation and implementation.
