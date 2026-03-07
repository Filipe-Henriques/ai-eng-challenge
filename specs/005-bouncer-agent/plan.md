# Implementation Plan: Bouncer Agent

**Branch**: `005-bouncer-agent` | **Date**: 2026-03-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-bouncer-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implement the Bouncer Agent, the second node in the LangGraph pipeline, responsible for tier determination and intent classification. After the Greeter Agent authenticates a customer, the Bouncer reads the verified user's tier, classifies their intent from conversation history using an LLM with structured output, and routes them to the appropriate Specialist Agent. This is a single-turn agent that performs no banking operations—it purely orchestrates the handoff.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: LangGraph, LangChain (structured output), OpenAI (gpt-4o-mini), Pydantic v2  
**Storage**: In-memory (GraphState object, no persistence)  
**Testing**: pytest  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Web service component (LangGraph agent node)  
**Performance Goals**: Single-turn execution <500ms  
**Constraints**: Must not loop or engage in multi-turn conversation; strictly stateless operation after handoff  
**Scale/Scope**: Part of 3-agent pipeline (Greeter → Bouncer → Specialist)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Before Phase 0)

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Multi-Agent Architecture** | Bouncer MUST be a single-purpose LangGraph node that only classifies and routes | ✅ PASS: Spec clearly defines single-turn routing behavior with no business logic |
| **II. Safety First** | Bouncer MUST apply guardrails to input messages and output responses | ✅ PASS: Guardrails will be integrated at input and output |
| **III. Security by Design** | Bouncer MUST only operate on authenticated users (is_authenticated = True) | ✅ PASS: Spec requires is_authenticated check via conditional edge |
| **IV. Stateful History** | Bouncer MUST use conversation history for intent classification | ✅ PASS: Intent classification explicitly uses messages array |
| **V. Clean Architecture** | Agent code MUST reside in app/agents/bouncer.py | ✅ PASS: File location specified in spec |

**Decision**: ✅ All gates PASSED. Proceeded to Phase 0.

---

### Post-Design Check (After Phase 1)

| Principle | Verification | Status |
|-----------|--------------|--------|
| **I. Multi-Agent Architecture** | Design uses LangGraph node pattern; single `bouncer_agent()` function; no multi-turn conversation | ✅ PASS |
| **II. Safety First** | Design includes `run_guardrails()` at input check (line 1) and output sanitization (line 5) per quickstart | ✅ PASS |
| **III. Security by Design** | Design enforces `is_authenticated = True` via conditional edge; agent assumes preconditions met | ✅ PASS |
| **IV. Stateful History** | Design passes full `state['messages']` to LLM for intent classification via conversation_history string | ✅ PASS |
| **V. Clean Architecture** | All code in `app/agents/bouncer.py`; separates model (ClassifiedIntent), routing (TIER_ROUTING), and logic | ✅ PASS |

**Additional Design Validations**:
- ✅ No direct database access (reads from `verified_user` state)
- ✅ LLM configuration uses `gpt-4o-mini` per constitution tech stack
- ✅ Pydantic v2 for data validation (ClassifiedIntent model)
- ✅ Error handling with defensive defaults (no exceptions thrown)
- ✅ Test coverage includes mocked LLM and guardrails

**Decision**: ✅ All constitution principles satisfied in design. Ready for implementation.

## Project Structure

### Documentation (this feature)

```text
specs/005-bouncer-agent/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── agent-interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── agents/
│   ├── __init__.py
│   ├── greeter.py           # Existing: Greeter Agent
│   └── bouncer.py           # NEW: Bouncer Agent (this feature)
├── graph/
│   ├── state.py             # Update: Add customer_tier, customer_intent fields
│   └── pipeline.py          # Update: Add bouncer node and routing edges
├── guardrails/
│   └── guardrails.py        # Reuse: Apply to bouncer input/output
└── models/
    └── database.py          # No changes (reuse existing User model)

tests/
├── test_greeter.py          # Existing
├── test_bouncer.py          # NEW: Bouncer Agent tests
└── test_guardrails.py       # Existing: Reuse for bouncer
```

**Structure Decision**: Follows established single-project layout per Constitution Principle V (Clean Architecture). Bouncer agent is a new node in the existing LangGraph pipeline, requiring minimal changes to shared state and graph routing.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected.** All constitution principles are satisfied by the Bouncer Agent design.
