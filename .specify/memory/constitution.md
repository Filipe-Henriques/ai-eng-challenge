<!--
  SYNC IMPACT REPORT
  ==================
  
  Version Change: (none) → 1.0
  Date: 2026-03-07
  Type: Initial ratification
  
  Summary:
  This is the initial constitution for the DEUS Bank AI Support System project.
  
  Core Principles Established:
  I.   Multi-Agent Architecture with LangGraph
  II.  Safety First — Guardrails as a Cross-Cutting Concern
  III. Security by Design — Strict Verification
  IV.  Stateful Conversation History
  V.   Clean Architecture — Separation of Concerns
  
  Sections Added:
  - Mission
  - Core Principles (5 principles)
  - Technology Stack
  - Project Structure
  - Development Workflow
  - Governance
  
  Templates Requiring Review:
  ⚠ .specify/templates/spec-template.md - Review for alignment with principles
  ⚠ .specify/templates/plan-template.md - Verify Constitution Check section aligns
  ⚠ .specify/templates/tasks-template.md - Ensure task organization reflects principles
  
  Follow-up Actions:
  - Ensure all templates reference the correct governance rules
  - Update any agent-specific commands to align with LangGraph architecture
  - Verify project structure in templates matches Section 4
  
-->

# DEUS Bank AI Support System — Constitution

**Version:** 1.0
**Date:** 2026-03-07

---

## 1. Mission

This project is an AI Engineer code challenge. The goal is to build an **AI-powered customer support system** for DEUS Bank, where multiple specialised agents work together to identify a customer and route them to the right place — without the pain of endless phone menus. The system is built with a focus on clean architecture, safety, and production-readiness.

---

## 2. Core Principles

### I. Multi-Agent Architecture with LangGraph

The system MUST be implemented as a **stateful multi-agent pipeline** using **LangGraph**. Each agent is a distinct node in the graph with a single, well-defined responsibility. Agents MUST NOT perform tasks outside their defined scope.

**Rationale**: LangGraph provides a clean, auditable, and controllable way to manage the flow between agents, making the system easy to reason about, test, and extend.

### II. Safety First — Guardrails as a Cross-Cutting Concern

Guardrails are not optional. They MUST be applied at every agent node to ensure all responses are safe, professional, on-topic, and compliant with bank policies. The guardrails layer is responsible for:
- **Topic Filtering**: Rejecting off-topic conversations (e.g., asking the bot to write code).
- **PII Protection**: Ensuring sensitive data (e.g., phone numbers, IBANs) is never leaked to unverified users.
- **Toxicity Check**: Preventing harmful or abusive language in responses.

### III. Security by Design — Strict Verification

Customer identity MUST be verified before any account information is disclosed. The verification logic MUST require a match of **at least 2 out of 3** identifying fields (`name`, `phone`, `iban`). Only after this check passes may the system proceed to ask the customer's secret question.

**Rationale**: This prevents social engineering attacks and protects customer data.

### IV. Stateful Conversation History

The system MUST maintain conversation history within a session. This allows agents to reference previous turns, creating a natural and context-aware experience. History is managed via the LangGraph `State` object and MUST NOT be persisted to a database in this version.

### V. Clean Architecture — Separation of Concerns

The codebase MUST follow a strict separation of concerns:
- **`app/agents/`**: One file per agent, containing only the agent's logic.
- **`app/graph/`**: The LangGraph pipeline definition (nodes, edges, routing).
- **`app/guardrails/`**: All guardrail logic.
- **`app/models/`**: Pydantic data models and the mock in-memory database.
- **`app/api/`**: FastAPI endpoint definitions.
- **`tests/`**: All unit and integration tests.

---

## 3. Technology Stack

| Component | Technology |
| :--- | :--- |
| Agent Framework | LangGraph |
| LLM | `gpt-4o-mini` (via OpenAI API) |
| API Framework | FastAPI |
| Data Validation | Pydantic v2 |
| Testing | Pytest + pytest-asyncio |
| Containerisation | Docker + Docker Compose |
| Code Formatting | Black |
| Docstring Style | Google Style |

---

## 4. Project Structure

```
deus-bank-support/
├── app/
│   ├── main.py                  # FastAPI entrypoint
│   ├── agents/
│   │   ├── greeter.py           # Greeter Agent
│   │   ├── bouncer.py           # Bouncer Agent
│   │   └── specialist.py        # Specialist Agent
│   ├── graph/
│   │   ├── state.py             # LangGraph State definition
│   │   ├── pipeline.py          # Graph nodes, edges, and routing logic
│   │   └── router.py            # Conditional edge functions
│   ├── guardrails/
│   │   └── guardrails.py        # All guardrail checks
│   ├── models/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── database.py          # Mock in-memory data store
│   └── api/
│       └── v1/
│           └── endpoints/
│               └── chat.py      # Chat endpoint
├── tests/
│   ├── test_guardrails.py
│   ├── test_greeter.py
│   ├── test_bouncer.py
│   ├── test_specialist.py
│   └── test_api.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── constitution.md
```

---

## 5. Development Workflow

- All Python code MUST be formatted with **Black** before commit.
- All functions, classes, and modules MUST include **Google Style docstrings**.
- All commits MUST follow the **Conventional Commits** format: `type(scope): description`.
- All new features MUST be developed in a feature branch following **GitFlow**.

---

## 6. Governance

This constitution supersedes all other development practices for this project. Any deviation requires explicit justification. Amendments must be documented and versioned.
