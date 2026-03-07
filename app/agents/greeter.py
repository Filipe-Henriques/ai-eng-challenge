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
from app.guardrails.guardrails import run_guardrails

# Configure logging
logger = logging.getLogger(__name__)


class ExtractedInfo(BaseModel):
    """Structured extraction of identity fields from user message.

    Used with LangChain's with_structured_output() to parse user-provided
    identifying information. All fields are optional because the user may
    provide them incrementally across multiple turns.

    Attributes:
        name: Customer's full name, or None if not mentioned in message
        phone: Customer's phone number with country code (e.g., "+1122334455"),
               or None if not mentioned
        iban: Customer's IBAN (International Bank Account Number), or None if
              not mentioned

    Examples:
        >>> # User says: "I'm Lisa and my phone is +1122334455"
        >>> ExtractedInfo(name="Lisa", phone="+1122334455", iban=None)

        >>> # User says: "My IBAN is DE89370400440532013000"
        >>> ExtractedInfo(name=None, phone=None, iban="DE89370400440532013000")
    """

    name: str | None = Field(
        default=None, description="Customer's full name as mentioned in the message"
    )
    phone: str | None = Field(
        default=None, description="Phone number with country code (e.g., '+1122334455')"
    )
    iban: str | None = Field(default=None, description="IBAN (International Bank Account Number)")


def greeter_agent(state: State) -> dict:
    """Greeter Agent node for customer identity verification and authentication.

    This is the entry point to the DEUS Bank AI Support System. The agent welcomes
    customers, collects their identifying information incrementally, verifies their
    identity using the 2-out-of-3 rule, and authenticates them via a secret question.

    Args:
        state: The current LangGraph State containing conversation history,
               collected fields, verification attempts, and user information

    Returns:
        dict: Partial state updates to be merged into the graph state.
              May include: messages, collected_fields, verification_attempts,
              verified_user, is_authenticated, current_agent, conversation_ended

    Behavior:
        - Reads latest user message from state["messages"][-1]
        - Applies input guardrails (rejects unsafe/off-topic messages)
        - Extracts identity fields (name, phone, iban) using LLM structured output
        - Attempts 2/3 verification when >= 2 fields collected
        - Asks secret question after identity verified
        - Checks secret answer (case-insensitive)
        - Applies output guardrails before returning response
        - Enforces max 3 attempts (verification + authentication failures combined)
        - Handles database failures with single retry

    Termination Conditions:
        - is_authenticated set to True → hands off to Bouncer (current_agent="bouncer")
        - verification_attempts >= 3 → ends conversation (conversation_ended=True)
        - Database failure after retry → ends conversation (conversation_ended=True)

    Side Effects:
        - Calls run_guardrails() for input/output safety checks
        - Calls find_user_with_retry() for database lookups (with retry)
        - Uses OpenAI LLM (gpt-4o-mini) for response generation and field extraction

    Raises:
        No exceptions raised (all errors handled internally with conversation_ended)

    Examples:
        >>> # First turn - welcome message
        >>> state = {"messages": [HumanMessage(content="Hi")], ...}
        >>> result = greeter_agent(state)
        >>> result["messages"][0].content
        "Welcome to DEUS Bank! To assist you, I'll need to verify your identity..."

        >>> # Successful verification
        >>> state = {
        ...     "messages": [..., HumanMessage(content="I'm Lisa, phone +1122334455")],
        ...     "collected_fields": {},
        ...     ...
        ... }
        >>> result = greeter_agent(state)
        >>> result["verified_user"].name
        "Lisa"
    """
    # Get current state
    messages = state.get("messages", [])
    verification_attempts = state.get("verification_attempts", 0)
    collected_fields = state.get("collected_fields", {"name": None, "phone": None, "iban": None})
    verified_user = state.get("verified_user")
    is_authenticated = state.get("is_authenticated", False)

    # Get latest user message
    if not messages:
        logger.warning("No messages in state")
        return {
            "messages": [AIMessage(content="Welcome to DEUS Bank! How can I help you today?")],
            "conversation_ended": False,
        }

    user_message = messages[-1].content

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

    # Apply input guardrails
    guardrail_result = run_guardrails(user_message, is_authenticated)

    if not guardrail_result.is_safe:
        logger.info(f"Input blocked by guardrail: {guardrail_result.blocked_reason}")
        return {
            "messages": [AIMessage(content=guardrail_result.safe_response)],
            "conversation_ended": True,
        }

    # First turn: Welcome message
    if len(messages) == 1:
        welcome_message = (
            "Welcome to DEUS Bank! I'm here to help you today. "
            "To assist you securely, I'll need to verify your identity. "
            "Could you please provide your full name, phone number, and IBAN?"
        )

        # Apply output guardrails
        output_check = run_guardrails(welcome_message, is_authenticated)
        response_content = welcome_message if output_check.is_safe else output_check.safe_response

        return {"messages": [AIMessage(content=response_content)], "conversation_ended": False}

    # Subsequent turns: Extract fields from user message
    # Initialize LLM for field extraction
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    extractor = llm.with_structured_output(ExtractedInfo)

    # System prompt for field extraction
    extraction_prompt = SystemMessage(content="""
Extract the customer's identity information from their message.
Look for:
- name: Full name (first and last name)
- phone: Phone number with country code (e.g., +1122334455)
- iban: IBAN (International Bank Account Number, e.g., DE89370400440532013000)

Only extract fields that are explicitly mentioned. Set to null if not mentioned.
Be flexible with formatting - customers may provide information in various ways.
""")

    # Extract fields from user message
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

    # Count how many fields we have collected
    non_none_count = sum(1 for v in updated_fields.values() if v is not None)

    # If we have fewer than 2 fields, ask for more information
    if non_none_count < 2:
        missing_fields = [k for k, v in updated_fields.items() if v is None]
        response_message = (
            f"Thank you for that information. To verify your identity, "
            f"I'll need at least two of the following: name, phone number, and IBAN. "
            f"Could you also provide your {' or '.join(missing_fields)}?"
        )

        # Apply output guardrails
        output_check = run_guardrails(response_message, is_authenticated)
        response_content = response_message if output_check.is_safe else output_check.safe_response

        return {
            "messages": [AIMessage(content=response_content)],
            "collected_fields": updated_fields,
            "conversation_ended": False,
        }

    # Increment 3: Identity Verification (2-out-of-3 rule)
    # If user not verified yet and we have 2+ fields, attempt verification
    if verified_user is None and non_none_count >= 2:
        logger.info(f"Attempting identity verification with {non_none_count} fields")

        try:
            # Attempt database lookup with retry
            user = find_user_with_retry(updated_fields)

            if user is not None:
                # Verification successful - ask secret question
                logger.info(f"Identity verified for user: {user.name}")
                response_message = f"Great! {user.secret}"

                # Apply output guardrails
                output_check = run_guardrails(response_message, is_authenticated)
                response_content = (
                    response_message if output_check.is_safe else output_check.safe_response
                )

                return {
                    "messages": [AIMessage(content=response_content)],
                    "collected_fields": updated_fields,
                    "verified_user": user,
                    "conversation_ended": False,
                }
            else:
                # Verification failed - no match or multiple matches
                logger.warning("Identity verification failed - no match found")
                response_message = (
                    "I wasn't able to verify your identity with the information provided. "
                    "Please double-check your details and try again. "
                    "You can provide your name, phone number, or IBAN."
                )

                # Apply output guardrails
                output_check = run_guardrails(response_message, is_authenticated)
                response_content = (
                    response_message if output_check.is_safe else output_check.safe_response
                )

                return {
                    "messages": [AIMessage(content=response_content)],
                    "collected_fields": updated_fields,
                    "verification_attempts": verification_attempts + 1,
                    "conversation_ended": False,
                }

        except DatabaseUnavailableError:
            # Database failure after retry
            logger.error("Database unavailable after retry")
            response_message = (
                "I'm having trouble accessing your information right now. "
                "Please try again in a moment, or contact our support team at "
                "support@deusbank.com for assistance."
            )

            # Apply output guardrails
            output_check = run_guardrails(response_message, is_authenticated)
            response_content = (
                response_message if output_check.is_safe else output_check.safe_response
            )

            return {
                "messages": [AIMessage(content=response_content)],
                "collected_fields": updated_fields,
                "conversation_ended": True,
            }

    # Increment 4: Secret Question Authentication
    # If user is verified but not authenticated, check their secret answer
    if verified_user is not None and not is_authenticated:
        logger.info("Checking secret answer for authenticated user")

        # Extract answer from user message (case-insensitive comparison)
        user_answer = user_message.strip().lower()
        expected_answer = verified_user.answer.lower()

        if user_answer == expected_answer:
            # Authentication successful
            logger.info("Secret answer correct - authentication successful")
            response_message = (
                "Perfect! You're all set. Let me connect you with the right team "
                "who can help you with your request."
            )

            # Apply output guardrails
            output_check = run_guardrails(response_message, is_authenticated)
            response_content = (
                response_message if output_check.is_safe else output_check.safe_response
            )

            return {
                "messages": [AIMessage(content=response_content)],
                "is_authenticated": True,
                "current_agent": "bouncer",
                "conversation_ended": False,
            }
        else:
            # Authentication failed
            logger.warning("Secret answer incorrect")
            response_message = (
                "That doesn't seem to match our records. "
                f"Let me ask again: {verified_user.secret}"
            )

            # Apply output guardrails
            output_check = run_guardrails(response_message, is_authenticated)
            response_content = (
                response_message if output_check.is_safe else output_check.safe_response
            )

            return {
                "messages": [AIMessage(content=response_content)],
                "verification_attempts": verification_attempts + 1,
                "conversation_ended": False,
            }

    # Fallback: Should not reach here
    logger.warning("Unexpected state in greeter_agent")
    response_message = (
        "I'm sorry, I'm having trouble processing your request. Could you please start over?"
    )

    # Apply output guardrails
    output_check = run_guardrails(response_message, is_authenticated)
    response_content = response_message if output_check.is_safe else output_check.safe_response

    return {"messages": [AIMessage(content=response_content)], "conversation_ended": False}
