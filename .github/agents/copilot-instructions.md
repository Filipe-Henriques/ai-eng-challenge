# ai-eng-challenge Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-07

## Active Technologies
- Python 3.11+ + OpenAI API (gpt-4o-mini for toxicity/topic classification), Pydantic v2 (data validation), Python re module (PII regex detection) (003-guardrails)
- N/A (stateless evaluation functions) (003-guardrails)

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
- 003-guardrails: Added Python 3.11+ + OpenAI API (gpt-4o-mini for toxicity/topic classification), Pydantic v2 (data validation), Python re module (PII regex detection)

- 001-data-models: Added Python 3.11+ + Pydantic v2, FastAPI (for data models), pytest + pytest-asyncio (testing)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
