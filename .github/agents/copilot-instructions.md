# ai-eng-challenge Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-07

## Active Technologies
- Python 3.11+ + OpenAI API (gpt-4o-mini for toxicity/topic classification), Pydantic v2 (data validation), Python re module (PII regex detection) (003-guardrails)
- N/A (stateless evaluation functions) (003-guardrails)
- Python 3.11+ + LangGraph, LangChain, OpenAI (gpt-4o-mini), Pydantic v2, FastAPI (004-greeter-agent)
- In-memory mock database (`app.models.database`) (004-greeter-agent)
- Python 3.11 + LangGraph, LangChain (structured output), OpenAI (gpt-4o-mini), Pydantic v2 (005-bouncer-agent)
- In-memory (GraphState object, no persistence) (005-bouncer-agent)

- Python 3.11+ + Pydantic v2, FastAPI (for data models), pytest + pytest-asyncio (testing) (001-data-models)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 006-specialist-agent: Added Python 3.11+ + LangGraph, LangChain, OpenAI (gpt-4o-mini), Pydantic v2
- 005-bouncer-agent: Added Python 3.11 + LangGraph, LangChain (structured output), OpenAI (gpt-4o-mini), Pydantic v2
- 004-greeter-agent: Added Python 3.11+ + LangGraph, LangChain, OpenAI (gpt-4o-mini), Pydantic v2, FastAPI


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
