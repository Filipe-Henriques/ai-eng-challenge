"""Configuration for guardrails safety messages.

Pre-defined messages for blocking scenarios. These can be customized
via environment variables or left as defaults.

Environment Variables:
    GUARDRAILS_OFF_TOPIC_MSG: Custom off-topic refusal message
    GUARDRAILS_TOXICITY_MSG: Custom toxicity warning message
    GUARDRAILS_ERROR_MSG: Custom error message
"""

import os

# Default messages (can be overridden via environment variables)
OFF_TOPIC_REFUSAL = os.environ.get(
    "GUARDRAILS_OFF_TOPIC_MSG",
    "I'm here to help with banking services like accounts, transfers, loans, and cards. "
    "I'm unable to assist with topics outside of banking. "
    "Is there a banking question I can help you with today?"
)

TOXICITY_WARNING = os.environ.get(
    "GUARDRAILS_TOXICITY_MSG",
    "I understand you're frustrated, but I need you to communicate respectfully. "
    "I'm here to help resolve your banking concerns. "
    "Can we start over with your question?"
)

ERROR_MESSAGE = os.environ.get(
    "GUARDRAILS_ERROR_MSG",
    "I'm experiencing technical difficulties validating your message. "
    "For your security, I need to pause this conversation. "
    "Please try again in a moment, or contact our support line for immediate assistance."
)
