"""Core guardrails implementation for DEUS Bank AI Support System.

This module provides three independent safety checks:
1. Toxicity detection - Blocks abusive, threatening, or harassing language
2. Topic filtering - Ensures queries are banking-related
3. PII protection - Redacts sensitive information for unauthenticated users

Architecture:
    - Each check is an independent function with a single responsibility
    - The run_guardrails() orchestrator composes checks with short-circuit evaluation
    - All checks are stateless and deterministic (given same input + auth state)
    - Failures are handled with fail-closed behavior (block vs allow unchecked)

Performance:
    - Target: <200ms average, <500ms p95
    - Toxicity/Topic: LLM API calls with 5-second timeout
    - PII: Regex-based, negligible latency (<1ms)
"""

import re
import os
import logging
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from openai import OpenAI, OpenAIError

from app.guardrails.config import (
    OFF_TOPIC_REFUSAL,
    TOXICITY_WARNING,
    ERROR_MESSAGE,
)

# Configure logging
logger = logging.getLogger(__name__)

# Compile PII regex patterns at module level for performance
PHONE_PATTERN = re.compile(r'\+?[0-9\s\-\(\)]{7,15}')
IBAN_PATTERN = re.compile(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}')

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


class GuardrailResult(BaseModel):
    """Structured output from guardrail evaluation.
    
    Encapsulates blocking decisions and sanitized content for agent consumption.
    
    Attributes:
        is_safe: True if message passed all checks; False if blocked.
        blocked_reason: Reason for blocking ("toxic" | "off_topic" | "error") or None.
        safe_response: Pre-defined message for blocked requests, or None.
        sanitised_response: Response with PII redacted (if unauthenticated).
    
    Validation Rules:
        - If is_safe=False, blocked_reason and safe_response must not be None
        - If is_safe=True, blocked_reason and safe_response must be None
        - sanitised_response is always present
    
    Examples:
        >>> # Safe message
        >>> GuardrailResult(
        ...     is_safe=True,
        ...     blocked_reason=None,
        ...     safe_response=None,
        ...     sanitised_response="Your balance is $1,234.56"
        ... )
        
        >>> # Blocked message
        >>> GuardrailResult(
        ...     is_safe=False,
        ...     blocked_reason="toxic",
        ...     safe_response="Please be respectful.",
        ...     sanitised_response=""
        ... )
    """
    
    is_safe: bool
    blocked_reason: Optional[str] = None
    safe_response: Optional[str] = None
    sanitised_response: str
    
    @model_validator(mode='after')
    def validate_field_consistency(self) -> 'GuardrailResult':
        """Ensure consistency between is_safe flag and blocking fields."""
        if self.is_safe:
            # Safe messages must not have blocking fields set
            if self.blocked_reason is not None:
                raise ValueError(
                    "is_safe=True requires blocked_reason=None, "
                    f"got blocked_reason='{self.blocked_reason}'"
                )
            if self.safe_response is not None:
                raise ValueError(
                    "is_safe=True requires safe_response=None, "
                    f"got safe_response='{self.safe_response}'"
                )
        else:
            # Blocked messages must have blocking fields set
            if self.blocked_reason is None:
                raise ValueError(
                    "is_safe=False requires blocked_reason to be set"
                )
            if self.safe_response is None:
                raise ValueError(
                    "is_safe=False requires safe_response to be set"
                )
        
        return self


def check_toxicity(message: str) -> Optional[str]:
    """Check if message contains toxic language using LLM classification.
    
    Uses OpenAI gpt-4o-mini to perform binary toxicity classification.
    Toxic content includes: profanity, threats, harassment, abuse, hate speech.
    
    This function implements fail-closed behavior: on error or timeout,
    returns error message (blocks conversation vs allowing unchecked content).
    
    Args:
        message: Customer message to evaluate for toxicity.
    
    Returns:
        Toxicity warning message if toxic detected, None if safe.
    
    Examples:
        >>> check_toxicity("What's my balance?")
        None
        
        >>> check_toxicity("You're useless!")
        "I understand you're frustrated, but I need you to communicate..."
    
    Performance:
        - Target: <100ms average
        - Timeout: 5 seconds
        - Model: gpt-4o-mini (temperature=0, max_tokens=10)
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content moderator for a banking support system. "
                        "Classify messages as exactly 'safe' or 'toxic'.\n\n"
                        "Toxic means: profanity, threats, harassment, abuse, hate speech.\n"
                        "Safe means: any legitimate banking inquiry, even if frustrated.\n\n"
                        "Examples:\n"
                        "- 'I hate this stupid bank' → toxic\n"
                        "- 'I need help urgently' → safe\n"
                        "- 'You're useless' → toxic\n\n"
                        "Respond with only one word: 'safe' or 'toxic'."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0,
            max_tokens=10,
            timeout=5.0
        )
        
        classification = response.choices[0].message.content.strip().lower()
        
        if "toxic" in classification:
            return TOXICITY_WARNING
        
        return None
    
    except (OpenAIError, Exception) as e:
        # Fail-closed: block on error
        logger.error(f"Toxicity check failed: {type(e).__name__}", exc_info=False)
        return ERROR_MESSAGE


def check_topic(message: str) -> Optional[str]:
    """Check if message relates to banking services using LLM classification.
    
    Uses OpenAI gpt-4o-mini to determine if message is within banking scope.
    Banking topics include: accounts, transfers, loans, cards, balance, IBAN,
    transactions, fees, fraud, disputes, authentication, account access.
    
    This function implements fail-closed behavior: on error or timeout,
    returns error message (blocks conversation vs allowing unchecked content).
    
    Args:
        message: Customer message to evaluate for topic relevance.
    
    Returns:
        Refusal message if off-topic detected, None if on-topic.
    
    Examples:
        >>> check_topic("What's my account balance?")
        None
        
        >>> check_topic("How do I code in Python?")
        "I'm here to help with banking services..."
    
    Performance:
        - Target: <100ms average
        - Timeout: 5 seconds
        - Model: gpt-4o-mini (temperature=0, max_tokens=10)
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Classify if this message relates to banking or financial services.\n\n"
                        "Banking topics include: accounts, balance, transfers, loans, credit cards, "
                        "debit cards, IBAN, transactions, fees, fraud, disputes, authentication, "
                        "account access.\n\n"
                        "Non-banking topics include: general knowledge, coding, politics, "
                        "unrelated services.\n\n"
                        "Note: Frustrated complaints ABOUT banking services are still 'on_topic'.\n\n"
                        "Respond with only: 'on_topic' or 'off_topic'."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0,
            max_tokens=10,
            timeout=5.0
        )
        
        classification = response.choices[0].message.content.strip().lower()
        
        if "off_topic" in classification or "off-topic" in classification:
            return OFF_TOPIC_REFUSAL
        
        return None
    
    except (OpenAIError, Exception) as e:
        # Fail-closed: block on error
        logger.error(f"Topic check failed: {type(e).__name__}", exc_info=False)
        return ERROR_MESSAGE


def check_pii(response: str, is_authenticated: bool) -> str:
    """Redact PII (phone numbers, IBANs) from response for unauthenticated users.
    
    Uses regex patterns to detect and replace sensitive information with [REDACTED].
    If user is authenticated, returns response unchanged (they're authorized to
    see their own PII).
    
    PII Patterns Detected:
        - Phone numbers: International and local formats
        - IBANs: ISO 13616 format (15-34 characters)
    
    Args:
        response: Agent's proposed response to sanitize.
        is_authenticated: Whether customer passed identity verification.
    
    Returns:
        Original response if authenticated, redacted response if not.
    
    Examples:
        >>> check_pii("Call us at +1122334455", is_authenticated=False)
        "Call us at [REDACTED]"
        
        >>> check_pii("Call us at +1122334455", is_authenticated=True)
        "Call us at +1122334455"
        
        >>> check_pii("Your IBAN is DE89370400440532013000", is_authenticated=False)
        "Your IBAN is [REDACTED]"
    
    Performance:
        - Negligible latency (<1ms per check)
        - Deterministic: same input always produces same output
    """
    # Early return if authenticated - user can see their own PII
    if is_authenticated:
        return response
    
    # Redact phone numbers
    sanitized = PHONE_PATTERN.sub('[REDACTED]', response)
    
    # Redact IBANs
    sanitized = IBAN_PATTERN.sub('[REDACTED]', sanitized)
    
    return sanitized


def run_guardrails(
    message: str,
    proposed_response: str,
    is_authenticated: bool
) -> GuardrailResult:
    """Orchestrate all safety checks and return unified evaluation result.
    
    Performs three safety checks in priority order:
    1. Toxicity detection (blocks abusive language)
    2. Topic filtering (blocks off-topic requests)
    3. PII protection (redacts sensitive data for unauthenticated users)
    
    Short-circuit evaluation: If message is blocked (toxic/off-topic),
    proposed_response is not evaluated for PII.
    
    Args:
        message: Customer's incoming message to evaluate for safety.
        proposed_response: Agent's proposed response to check for PII leakage.
        is_authenticated: Whether customer has passed identity verification.
    
    Returns:
        GuardrailResult with blocking decision and sanitized response.
    
    Raises:
        Does not raise exceptions. Failures are caught and returned as
        GuardrailResult(is_safe=False, blocked_reason="error", ...).
    
    Examples:
        >>> # Safe message, no PII
        >>> result = run_guardrails(
        ...     message="What's my balance?",
        ...     proposed_response="Your balance is $1,234.56",
        ...     is_authenticated=True
        ... )
        >>> result.is_safe
        True
        >>> result.sanitised_response
        "Your balance is $1,234.56"
        
        >>> # Safe message, PII redacted
        >>> result = run_guardrails(
        ...     message="How do I contact you?",
        ...     proposed_response="Call us at +1122334455",
        ...     is_authenticated=False
        ... )
        >>> result.is_safe
        True
        >>> result.sanitised_response
        "Call us at [REDACTED]"
        
        >>> # Toxic message blocked
        >>> result = run_guardrails(
        ...     message="You're useless!",
        ...     proposed_response="",
        ...     is_authenticated=False
        ... )
        >>> result.is_safe
        False
        >>> result.blocked_reason
        "toxic"
    
    Performance:
        - Target: <200ms average, <500ms p95
        - Concurrent-safe: Stateless, no shared mutable state
    """
    import time
    start_time = time.time()
    
    try:
        # Check 1: Toxicity (highest priority - immediate safety concern)
        toxic_warning = check_toxicity(message)
        if toxic_warning:
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Guardrail blocked: reason=toxic, "
                f"latency_ms={latency_ms:.2f}, "
                f"auth={is_authenticated}"
            )
            return GuardrailResult(
                is_safe=False,
                blocked_reason="toxic",
                safe_response=toxic_warning,
                sanitised_response=""
            )
        
        # Check 2: Topic filtering (resource protection)
        topic_refusal = check_topic(message)
        if topic_refusal:
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Guardrail blocked: reason=off_topic, "
                f"latency_ms={latency_ms:.2f}, "
                f"auth={is_authenticated}"
            )
            return GuardrailResult(
                is_safe=False,
                blocked_reason="off_topic",
                safe_response=topic_refusal,
                sanitised_response=""
            )
        
        # Check 3: PII protection (privacy compliance)
        sanitised = check_pii(proposed_response, is_authenticated)
        
        # Count PII redactions for metrics
        pii_redacted = sanitised.count("[REDACTED]")
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Guardrail passed: "
            f"latency_ms={latency_ms:.2f}, "
            f"pii_redacted={pii_redacted}, "
            f"auth={is_authenticated}"
        )
        
        # All checks passed
        return GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response=sanitised
        )
    
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        # Unexpected error - fail closed
        logger.error(
            f"Guardrail error: error_type={type(e).__name__}, "
            f"latency_ms={latency_ms:.2f}",
            exc_info=True
        )
        return GuardrailResult(
            is_safe=False,
            blocked_reason="error",
            safe_response=ERROR_MESSAGE,
            sanitised_response=""
        )
