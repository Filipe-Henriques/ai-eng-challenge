"""Greeter Agent for DEUS Bank AI Support System.

This module implements the first node in the LangGraph pipeline. The Greeter Agent
is responsible for welcoming customers, collecting their identity information
incrementally, verifying their identity using the 2-out-of-3 rule, and
authenticating them via their secret question.

Responsibilities:
    - Welcome customers on first turn
    - Extract identity fields (name, phone, IBAN) from user messages
    - Verify identity when 2+ fields collected (2-out-of-3 matching)
    - Ask secret question after verification passes
    - Authenticate customer when secret answer is correct
    - Handle failures gracefully (max 3 attempts)
    - Apply guardrails to all inputs and outputs

State Transitions:
    Welcome → Collect Fields → Verify Identity → Ask Secret → Authenticate → Bouncer
    Any step can fail → Retry (up to 3 attempts) → End conversation

Architecture:
    - Stateless function (reads from State, returns partial updates)
    - Uses LLM for response generation and field extraction
    - Integrates with guardrails for safety checks
    - Handles database failures with retry logic
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.graph.state import State
from app.models.schemas import User
from app.models.database import find_user_with_retry, DatabaseUnavailableError
from app.guardrails.guardrails import check_toxicity, check_pii
from app.guardrails.config import TOXICITY_WARNING

# Configure logging
logger = logging.getLogger(__name__)


class ExtractedInfo(BaseModel):
    """Structured extraction of identity fields from user message."""

    name: str | None = Field(
        default=None, description="Customer's full name as mentioned in the message"
    )
    phone: str | None = Field(
        default=None, description="Phone number with country code (e.g., '+1122334455')"
    )
    iban: str | None = Field(default=None, description="IBAN (International Bank Account Number)")


def greeter_agent(state: State) -> dict:
    """Greeter Agent node for customer identity verification and authentication."""

    # Get current state
    messages = state.get("messages", [])
    verification_attempts = state.get("verification_attempts", 0)
    collected_fields = state.get("collected_fields", {"name": None, "phone": None, "iban": None})
    verified_user = state.get("verified_user")
    is_authenticated = state.get("is_authenticated", False)

    # Early return: user already authenticated — pass through to bouncer with no new message
    # LangGraph requires at least one state field to be written, so we echo current_agent
    if is_authenticated:
        logger.info("User already authenticated, passing through to bouncer")
        return {"current_agent": state.get("current_agent", "bouncer")}

    # Get latest user message
    if not messages:
        logger.warning("No messages in state")
        return {
            "messages": [AIMessage(content="Welcome to DEUS Bank! How can I help you today?")],
            "conversation_ended": False,
        }

    user_message = messages[-1].content

    # Always check toxicity, even on first turn
    toxic_warning = check_toxicity(user_message)
    if toxic_warning:
        logger.info("Input blocked: toxic content detected")
        return {
            "messages": [AIMessage(content=toxic_warning)],
            "conversation_ended": True,
        }

    # First turn: welcome message — topic check doesn't apply to a greeting
    if len(messages) == 1:
        welcome_message = (
            "Welcome to DEUS Bank! I'm here to help you today. "
            "To assist you securely, I'll need to verify your identity. "
            "Could you please provide your full name, phone number, and IBAN?"
        )
        return {"messages": [AIMessage(content=welcome_message)], "conversation_ended": False}

    # Check for max attempts (3 failures)
    if verification_attempts >= 3:
        logger.info("Max verification attempts reached")
        return {
            "messages": [
                AIMessage(
                    content="I'm sorry, but I wasn't able to verify your identity. "
                    "Please contact our support team at support@deusbank.com or call 1-800-DEUS-BANK for assistance."
                )
            ],
            "conversation_ended": True,
        }

    # Subsequent turns: Extract fields from user message
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    extractor = llm.with_structured_output(ExtractedInfo)

    extraction_prompt = SystemMessage(content="""
Extract the customer's identity information from their message.
Look for:
- name: Full name (first and last name)
- phone: Phone number with country code (e.g., +1122334455)
- iban: IBAN (International Bank Account Number, e.g., DE89370400440532013000)

Only extract fields that are explicitly mentioned. Set to null if not mentioned.
Be flexible with formatting - customers may provide information in various ways.
""")

    try:
        extracted = extractor.invoke([extraction_prompt, HumanMessage(content=user_message)])
    except Exception as e:
        logger.error(f"Field extraction failed: {e}")
        extracted = ExtractedInfo(name=None, phone=None, iban=None)

    # Merge extracted fields into collected_fields (only non-None values)
    updated_fields = collected_fields.copy()
    if extracted.name is not None:
        updated_fields["name"] = extracted.name
    if extracted.phone is not None:
        updated_fields["phone"] = extracted.phone
    if extracted.iban is not None:
        updated_fields["iban"] = extracted.iban

    non_none_count = sum(1 for v in updated_fields.values() if v is not None)

    # If we have fewer than 2 fields, ask for more information
    if non_none_count < 2:
        missing_fields = [k for k, v in updated_fields.items() if v is None]
        response_message = (
            f"Thank you for that information. To verify your identity, "
            f"I'll need at least two of the following: name, phone number, and IBAN. "
            f"Could you also provide your {' or '.join(missing_fields)}?"
        )
        return {
            "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
            "collected_fields": updated_fields,
            "conversation_ended": False,
        }

    # Identity Verification (2-out-of-3 rule)
    if verified_user is None and non_none_count >= 2:
        logger.info(f"Attempting identity verification with {non_none_count} fields")

        try:
            user = find_user_with_retry(updated_fields)

            if user is not None:
                logger.info(f"Identity verified for user: {user.name}")
                response_message = f"Great! {user.secret}"
                return {
                    "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
                    "collected_fields": updated_fields,
                    "verified_user": user,
                    "conversation_ended": False,
                }
            else:
                logger.warning("Identity verification failed - no match found")
                response_message = (
                    "I wasn't able to verify your identity with the information provided. "
                    "Please double-check your details and try again. "
                    "You can provide your name, phone number, or IBAN."
                )
                return {
                    "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
                    "collected_fields": updated_fields,
                    "verification_attempts": verification_attempts + 1,
                    "conversation_ended": False,
                }

        except DatabaseUnavailableError:
            logger.error("Database unavailable after retry")
            response_message = (
                "I'm having trouble accessing your information right now. "
                "Please try again in a moment, or contact our support team at "
                "support@deusbank.com for assistance."
            )
            return {
                "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
                "collected_fields": updated_fields,
                "conversation_ended": True,
            }

    # Secret Question Authentication
    if verified_user is not None and not is_authenticated:
        logger.info("Checking secret answer")
        user_answer = user_message.strip().lower()
        expected_answer = verified_user.answer.lower()

        if user_answer == expected_answer:
            logger.info("Secret answer correct - authentication successful")
            response_message = (
                "Perfect! You're all set. Let me connect you with the right team "
                "who can help you with your request."
            )
            return {
                "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
                "is_authenticated": True,
                "current_agent": "bouncer",
                "conversation_ended": False,
            }
        else:
            logger.warning("Secret answer incorrect")
            response_message = (
                "That doesn't seem to match our records. "
                f"Let me ask again: {verified_user.secret}"
            )
            return {
                "messages": [AIMessage(content=check_pii(response_message, is_authenticated))],
                "verification_attempts": verification_attempts + 1,
                "conversation_ended": False,
            }

    # Fallback: Should not reach here
    logger.warning("Unexpected state in greeter_agent")
    response_message = (
        "I'm sorry, I'm having trouble processing your request. Could you please start over?"
    )
    return {"messages": [AIMessage(content=check_pii(response_message, is_authenticated))], "conversation_ended": False}
