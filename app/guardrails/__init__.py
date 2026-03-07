"""Guardrails safety layer for DEUS Bank AI Support System.

This module provides composable safety checks for customer interactions:
- Toxicity detection: Blocks abusive language
- Topic filtering: Ensures queries are banking-related
- PII protection: Redacts sensitive data for unauthenticated users

Usage:
    from app.guardrails import run_guardrails, GuardrailResult
    
    result = run_guardrails(
        message="customer message",
        proposed_response="agent response",
        is_authenticated=True
    )
"""

from app.guardrails.guardrails import GuardrailResult, run_guardrails

__all__ = ["GuardrailResult", "run_guardrails"]
