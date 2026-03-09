"""Bouncer Agent: Intent classification and specialist routing.

This module implements the Bouncer Agent, which is responsible for:
1. Reading the authenticated customer's tier from verified_user
2. Classifying customer intent from conversation history using LLM
3. Routing customers to the appropriate Specialist Agent
4. Generating professional handoff messages

The Bouncer is a single-turn agent that does not engage in multi-turn
conversation. It operates strictly between the Greeter and Specialist agents.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from app.graph.state import State
from app.guardrails.guardrails import check_toxicity, check_pii

# =============================================================================
# Data Models
# =============================================================================


class ClassifiedIntent(BaseModel):
    """Structured output model for LLM intent classification.

    This Pydantic model enforces type safety and validation for the LLM's
    intent classification output. It ensures the intent is one of five
    supported values and the confidence score is between 0.0 and 1.0.

    Attributes:
        intent: The classified customer intent. Must be one of:
                - account_balance: Customer wants to check their balance
                - transaction_history: Customer wants to review past transactions
                - fund_transfer: Customer wants to transfer money
                - lost_card: Customer needs to report a lost/stolen card
                - general_inquiry: Customer has a general question
        confidence: Classification confidence score between 0.0 and 1.0.
                   Higher values indicate stronger confidence in the classification.
    """

    intent: Literal[
        "account_balance",
        "transaction_history",
        "fund_transfer",
        "lost_card",
        "general_inquiry",
    ] = Field(description="Customer's intent classified from conversation history")

    confidence: float = Field(
        ge=0.0, le=1.0, description="Classification confidence score (0.0-1.0)"
    )


# =============================================================================
# Routing Configuration
# =============================================================================

# Tier-to-specialist routing table.
# Maps customer tier values to their corresponding Specialist Agent node names.
# Tier determination logic:
#   - premium: Account exists and Account.premium == True
#   - standard: Account exists and Account.premium == False, OR no Account found
# Defensive: If tier is not in this dict, defaults to specialist_standard.
TIER_ROUTING: dict[str, str] = {
    "standard": "specialist_standard",
    "premium": "specialist_premium",
}


# =============================================================================
# Agent Implementation
# =============================================================================


def bouncer_agent(state: State) -> dict:
    """Bouncer Agent: Classifies customer intent and routes to appropriate specialist.

    This single-turn agent performs the following steps:
    1. Apply input guardrails to customer messages
    2. Read customer tier from Account lookup via verified_user.iban
    3. Classify customer intent from conversation history using LLM
    4. Generate professional handoff message
    5. Route to appropriate Specialist Agent based on tier

    Args:
        state: Current graph state with authenticated user and conversation history.

    Returns:
        Dictionary with state updates:
        - customer_tier: Customer tier ("standard" or "premium")
        - customer_intent: Classified intent or "general_inquiry" if low confidence
        - current_agent: Target specialist agent name for routing
        - messages: Original messages plus new handoff AIMessage

    Preconditions (enforced by LangGraph conditional edges):
        - state['is_authenticated'] == True
        - state['verified_user'] is not None
        - state['messages'] contains conversation history

    Postconditions:
        - customer_tier is set
        - customer_intent is set
        - current_agent is set to specialist name
        - Handoff message is appended to messages
    """
    from app.models.database import find_account_by_iban

    # Step 1: Apply input guardrails to last user message
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    if messages:
        toxic_warning = check_toxicity(last_message)
        if toxic_warning:
            return {
                "messages": [AIMessage(content=toxic_warning)],
                "conversation_ended": True,
            }

    # Step 2: Determine customer tier from Account lookup
    verified_user = state["verified_user"]
    account = find_account_by_iban(verified_user.iban)

    if account and account.premium:
        customer_tier = "premium"
    else:
        customer_tier = "standard"  # Default for non-premium or no account

    # Step 3: Route to appropriate specialist based on tier
    specialist_agent = TIER_ROUTING.get(customer_tier, "specialist_standard")

    # Step 4: Classify customer intent from conversation history using LLM
    # Build conversation history string for LLM
    conversation_history = "\n".join(
        [
            f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.content}"
            for i, msg in enumerate(messages)
        ]
    )

    # System prompt for intent classification
    intent_system_prompt = """You are an intent classifier for a banking support system.
Analyze the conversation history and classify the customer's primary intent.

Supported intents:
- account_balance: Customer wants to check their account balance
- transaction_history: Customer wants to review past transactions
- fund_transfer: Customer wants to transfer money
- lost_card: Customer needs to report a lost/stolen card
- general_inquiry: Customer has a general question

Return the intent and your confidence score (0.0-1.0)."""

    # Initialize LLM for intent classification
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, timeout=10.0)

        # Create structured output chain
        structured_llm = llm.with_structured_output(ClassifiedIntent)

        # Invoke LLM with conversation history
        classified = structured_llm.invoke(
            [
                {"role": "system", "content": intent_system_prompt},
                {
                    "role": "user",
                    "content": f"Conversation:\n{conversation_history}\n\nClassify the customer's intent.",
                },
            ]
        )

        # Apply confidence threshold - if confidence < 0.5, fall back to general_inquiry
        if classified.confidence < 0.5:
            customer_intent = "general_inquiry"
        else:
            customer_intent = classified.intent

    except Exception as e:
        # Error handling: single retry on timeout, then fallback to general_inquiry
        try:
            classified = structured_llm.invoke(
                [
                    {"role": "system", "content": intent_system_prompt},
                    {
                        "role": "user",
                        "content": f"Conversation:\n{conversation_history}\n\nClassify the customer's intent.",
                    },
                ]
            )

            if classified.confidence < 0.5:
                customer_intent = "general_inquiry"
            else:
                customer_intent = classified.intent
        except Exception:
            # After retry failure, default to general_inquiry
            customer_intent = "general_inquiry"

    # Step 5: Generate handoff message
    handoff_message = "Connecting you to a specialist..."

    # Apply PII check to handoff message
    final_message = check_pii(handoff_message, state.get("is_authenticated", False))

    # Step 6: Return state updates
    return {
        "customer_tier": customer_tier,
        "customer_intent": customer_intent,
        "current_agent": specialist_agent,
        "messages": [AIMessage(content=final_message)],
    }
