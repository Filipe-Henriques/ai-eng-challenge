"""Guardrails safety layer for DEUS Bank AI Support System.

Agents use the individual checks directly:
    check_toxicity(message)           → blocks abusive language (input)
    check_pii(response, is_auth)      → redacts PII for unauthenticated users (output)

The run_guardrails() orchestrator is available for tests and full-pipeline evaluation.

Usage:
    from app.guardrails import check_toxicity, check_pii

    warning = check_toxicity(user_message)
    safe_response = check_pii(agent_response, is_authenticated)
"""

from app.guardrails.guardrails import (
    GuardrailResult,
    check_toxicity,
    check_pii,
    check_topic,
    run_guardrails,
)

__all__ = ["GuardrailResult", "check_toxicity", "check_pii", "check_topic", "run_guardrails"]
