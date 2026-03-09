"""Specialist Agent for DEUS Bank AI Support System.

This agent handles banking operations fulfillment using tool-calling capabilities.
It receives authenticated, routed customers and fulfills banking requests through
four primary tools: balance inquiry, transaction history, fund transfers, and
lost card reporting.

The agent adapts its persona based on customer tier (Standard/Premium/VIP) and
maintains multi-turn conversation support with automatic termination at turn 10.
"""

import logging
import uuid
import re
from typing import Any

from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

from app.models.database import ACCOUNTS_DB
from app.models.schemas import Transaction
from app.graph.state import State
from app.guardrails.guardrails import check_toxicity, check_pii

logger = logging.getLogger(__name__)


# ============================================================================
# TIER-BASED PERSONAS
# ============================================================================

PERSONA_STANDARD = """You are a helpful bank support agent for DEUS Bank. 
Be concise, efficient, and professional. Focus on resolving the customer's 
request quickly and accurately."""

PERSONA_PREMIUM = """You are a warm and personalized bank support agent for DEUS Bank.
Address customers by name, show empathy, and provide thoughtful service.
Balance efficiency with a friendly, caring tone."""

PERSONA_VIP = """You are a private banking specialist for DEUS Bank's VIP clients.
Provide white-glove service with exceptional attention to detail. Be proactive 
in anticipating needs and offer premium solutions. Address the customer by name
and treat them as a valued high-net-worth individual."""


# ============================================================================
# BANKING TOOLS
# ============================================================================

@tool
def get_account_balance(user_id: str) -> dict:
    """Retrieve the current balance and currency for the authenticated user's account.
    
    Use this tool when the customer asks about their account balance, available funds,
    or how much money they have.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'balance' (float) and 'currency' (str) keys on success,
        or dictionary with 'error' (str) key on failure
        
    Example:
        {"balance": 5420.50, "currency": "EUR"}
    """
    logger.info(f"get_account_balance called for user_id={user_id}")
    
    # Retry logic: attempt once, retry on failure
    for attempt in range(2):
        try:
            account = ACCOUNTS_DB.get(user_id)
            
            if not account:
                logger.warning(f"Account not found for user_id={user_id}")
                return {"error": "Account not found"}
            
            result = {"balance": account.balance, "currency": account.currency}
            logger.info(f"get_account_balance successful for user_id={user_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"get_account_balance failed (attempt {attempt + 1}/2): {e}")
            if attempt == 1:  # Second attempt failed
                return {"error": "Unable to retrieve balance. Please try again later."}
    
    return {"error": "Unable to retrieve balance. Please try again later."}


@tool
def get_transaction_history(user_id: str, limit: int = 5) -> list:
    """Retrieve recent transactions for the authenticated user's account.
    
    Use this tool when the customer asks about their recent transactions, spending history,
    or account activity. The LLM can request a specific number of transactions by changing
    the limit parameter.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        limit: Number of recent transactions to retrieve (1-20, default 5)
        
    Returns:
        List of transaction dictionaries, each with 'date' (str), 'description' (str),
        and 'amount' (float) keys. Returns empty list if account not found.
        
    Example:
        [
            {"date": "2026-03-05", "description": "Utility Bill", "amount": -84.30},
            {"date": "2026-03-04", "description": "Online Transfer", "amount": 150.0}
        ]
    """
    logger.info(f"get_transaction_history called for user_id={user_id}, limit={limit}")
    
    # Clamp limit to valid range [1, 20]
    limit = max(1, min(20, limit))
    logger.debug(f"Clamped limit to {limit}")
    
    # Retry logic: attempt once, retry on failure
    for attempt in range(2):
        try:
            account = ACCOUNTS_DB.get(user_id)
            
            if not account:
                logger.warning(f"Account not found for user_id={user_id}")
                return []
            
            # Get last 'limit' transactions (transactions are ordered oldest to newest)
            recent_transactions = account.transactions[-limit:]
            
            # Convert Transaction objects to dictionaries
            result = [
                {
                    "date": txn.date,
                    "description": txn.description,
                    "amount": txn.amount
                }
                for txn in recent_transactions
            ]
            
            logger.info(f"get_transaction_history successful for user_id={user_id}: returned {len(result)} transactions")
            return result
            
        except Exception as e:
            logger.error(f"get_transaction_history failed (attempt {attempt + 1}/2): {e}")
            if attempt == 1:  # Second attempt failed
                return []
    
    return []


@tool
def transfer_funds(user_id: str, recipient_iban: str, amount: float, description: str) -> dict:
    """Initiate a fund transfer from the authenticated user's account to a recipient.
    
    Use this tool when the customer wants to send money, make a payment, or transfer funds
    to another account. The transfer validates the recipient IBAN format and checks for
    sufficient balance before executing.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        recipient_iban: The IBAN of the recipient account (validated)
        amount: The transfer amount in account currency (must be positive)
        description: Description for the transaction record
        
    Returns:
        Dictionary with 'success' (bool), 'transaction_id' (str or None), and
        optional 'reason' (str) for failures
        
    Example:
        {"success": true, "transaction_id": "TXN-1234-5678"}
        {"success": false, "reason": "Insufficient funds"}
    """
    logger.info(f"transfer_funds called for user_id={user_id}, amount={amount}, recipient={recipient_iban}")
    
    # Retry logic: attempt once, retry on failure
    for attempt in range(2):
        try:
            # Validate account exists
            account = ACCOUNTS_DB.get(user_id)
            if not account:
                logger.warning(f"Account not found for user_id={user_id}")
                return {"success": False, "reason": "Account not found"}
            
            # Validate amount is positive
            if amount <= 0:
                logger.warning(f"Invalid amount: {amount}")
                return {"success": False, "reason": "Amount must be positive"}
            
            # Validate IBAN format (basic check: 15-34 chars, starts with 2 letters)
            iban_pattern = r'^[A-Z]{2}[A-Z0-9]{13,32}$'
            if not re.match(iban_pattern, recipient_iban):
                logger.warning(f"Invalid IBAN format: {recipient_iban}")
                return {"success": False, "reason": "Invalid IBAN format"}
            
            # Check sufficient balance
            if account.balance < amount:
                logger.warning(f"Insufficient funds: balance={account.balance}, amount={amount}")
                return {"success": False, "reason": "Insufficient funds"}
            
            # Execute transfer
            account.balance -= amount
            
            # Record transaction
            transaction = Transaction(
                date="2026-03-07",  # Current date
                description=description,
                amount=-amount  # Negative for debit
            )
            account.transactions.append(transaction)
            
            # Generate transaction ID
            transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
            
            logger.info(f"transfer_funds successful: transaction_id={transaction_id}, new_balance={account.balance}")
            return {"success": True, "transaction_id": transaction_id}
            
        except Exception as e:
            logger.error(f"transfer_funds failed (attempt {attempt + 1}/2): {e}")
            if attempt == 1:  # Second attempt failed
                return {"success": False, "reason": "Transfer failed due to technical error"}
    
    return {"success": False, "reason": "Transfer failed due to technical error"}


@tool
def report_lost_card(user_id: str) -> dict:
    """Report a lost or stolen card and block it immediately.
    
    Use this tool when the customer reports their card as lost, stolen, or needs to
    block their card for security reasons. The card will be blocked immediately and
    a case reference number will be provided for tracking.
    
    Args:
        user_id: The unique identifier of the authenticated customer
        
    Returns:
        Dictionary with 'success' (bool), 'case_id' (str or None), and
        optional 'reason' (str) for failures
        
    Example:
        {"success": true, "case_id": "CASE-ABCD1234"}
        {"success": false, "reason": "Account not found"}
    """
    logger.info(f"report_lost_card called for user_id={user_id}")
    
    # Retry logic: attempt once, retry on failure
    for attempt in range(2):
        try:
            # Validate account exists
            account = ACCOUNTS_DB.get(user_id)
            if not account:
                logger.warning(f"Account not found for user_id={user_id}")
                return {"success": False, "reason": "Account not found"}
            
            # Block the card (idempotent operation - safe to call multiple times)
            account.card_blocked = True
            
            # Generate case ID
            case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
            
            logger.info(f"report_lost_card successful: case_id={case_id}")
            return {"success": True, "case_id": case_id}
            
        except Exception as e:
            logger.error(f"report_lost_card failed (attempt {attempt + 1}/2): {e}")
            if attempt == 1:  # Second attempt failed
                return {"success": False, "reason": "Card blocking failed due to technical error"}
    
    return {"success": False, "reason": "Card blocking failed due to technical error"}


# ============================================================================
# SYSTEM PROMPT BUILDER
# ============================================================================

def build_system_prompt(state: State) -> str:
    """Build a tier-appropriate system prompt for the specialist agent.
    
    Args:
        state: Current conversation state with customer_tier and verified_user
        
    Returns:
        Formatted system prompt string with persona and instructions
    """
    # Extract customer tier with fallback to standard
    customer_tier = state.get("customer_tier", "standard").lower()
    
    # Map tier to persona
    persona_map = {
        "standard": PERSONA_STANDARD,
        "premium": PERSONA_PREMIUM,
        "vip": PERSONA_VIP,
    }
    persona = persona_map.get(customer_tier, PERSONA_STANDARD)
    
    # Extract customer name
    verified_user = state.get("verified_user")
    customer_name = verified_user.name if verified_user else "valued customer"
    
    # Extract customer intent
    customer_intent = state.get("customer_intent", "general inquiry")
    
    # Build formatted system prompt
    system_prompt = f"""{persona}

**Customer Information:**
- Name: {customer_name}
- Tier: {customer_tier.upper()}
- Intent: {customer_intent}

**Critical Instructions:**
1. NEVER expose raw tool output, user IDs, or database references to the customer
2. Always provide conversational, friendly responses - not raw JSON
3. Use the customer's name when appropriate
4. Adapt your tone based on the customer tier
5. Focus on resolving the customer's {customer_intent} request
6. If you need to use tools, call them but present results naturally in conversation
7. Keep responses concise and focused on the customer's needs

**Available Tools:**
- get_account_balance: Check account balance and currency
- get_transaction_history: View recent transactions (default 5, can request 1-20)
- transfer_funds: Send money to another account (requires IBAN, amount, description)
- report_lost_card: Block a lost or stolen card immediately
"""
    
    return system_prompt


# ============================================================================
# SPECIALIST AGENT
# ============================================================================

def specialist_agent(state: State) -> dict:
    """Main specialist agent function - handles banking operations fulfillment.
    
    This agent receives authenticated, routed customers and fulfills banking requests
    using tool-calling capabilities. It adapts its persona based on customer tier
    and manages multi-turn conversations with automatic termination at turn 10.
    
    Args:
        state: GraphState containing messages, verified_user, customer_tier, etc.
        
    Returns:
        Dictionary with updated state fields:
        - messages: Appended with agent response
        - conversation_ended: True if conversation should end (turn 10 or out-of-scope)
        - turn_count: Incremented turn counter (if exists)
        
    Preconditions:
        - state['is_authenticated'] == True
        - state['verified_user'] is not None
        - state['messages'] contains conversation history
    """
    logger.info("specialist_agent invoked")
    
    # Step 1: Apply toxicity check to last user message
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        toxic_warning = check_toxicity(last_message)
        if toxic_warning:
            logger.warning("Specialist blocked toxic input")
            return {
                "messages": [AIMessage(content=toxic_warning)],
                "conversation_ended": True,
            }
    
    # Step 2: Check for out-of-scope requests
    out_of_scope_keywords = [
        "mortgage", "investment", "invest", "new account", "open account",
        "loan", "credit card", "close", "closure", "dispute",
        "financial planning", "financial advice", "stock", "bond"
    ]
    
    if messages:
        last_message_lower = last_message.lower()
        # Special handling to avoid false positives for common banking terms
        # Only trigger out-of-scope if keywords appear in context
        if any(keyword in last_message_lower for keyword in out_of_scope_keywords):
            # Make sure "close" is about account closure, not just "close to" or similar
            if "close" in last_message_lower:
                # Check if it's account closure context
                if "account" in last_message_lower or "closure" in last_message_lower:
                    logger.info(f"Out-of-scope request detected: {last_message}")
                    handoff_message = """I appreciate your interest, but requests for mortgages, investments, 
new accounts, loans, credit cards, account closures, disputes, or financial planning 
require specialized assistance. I'd be happy to connect you with the appropriate team 
member who can help you with this. Would you like me to arrange a callback?"""
                    return {
                        "messages": [AIMessage(content=handoff_message)],
                        "conversation_ended": True,
                    }
            else:
                # Other keywords don't need context checking
                logger.info(f"Out-of-scope request detected: {last_message}")
                handoff_message = """I appreciate your interest, but requests for mortgages, investments, 
new accounts, loans, credit cards, account closures, disputes, or financial planning 
require specialized assistance. I'd be happy to connect you with the appropriate team 
member who can help you with this. Would you like me to arrange a callback?"""
                return {
                    "messages": [AIMessage(content=handoff_message)],
                    "conversation_ended": True,
                }
    
    # Step 3: Check turn count and enforce 10-turn limit
    turn_count = state.get("turn_count", 0)
    if turn_count >= 10:
        logger.info(f"Conversation ending at turn {turn_count} (limit reached)")
        boundary_message = """Thank you for chatting with me today. We've reached the end of our 
conversation window. If you need further assistance, I'd be happy to arrange a callback 
from one of our banking specialists. Have a great day!"""
        return {
            "messages": [AIMessage(content=boundary_message)],
            "conversation_ended": True,
            "turn_count": turn_count + 1,
        }
    
    # Step 4: Initialize LLM with tools
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [get_account_balance, get_transaction_history, transfer_funds, report_lost_card]
    llm_with_tools = llm.bind_tools(tools)
    
    # Step 5: Build system prompt
    system_prompt = build_system_prompt(state)
    
    # Step 6: Get user_id from verified_user for tool calls
    verified_user = state.get("verified_user")
    user_id = verified_user.user_id if hasattr(verified_user, 'user_id') else None
    
    # If user_id is not available, try to infer from iban mapping
    if not user_id and verified_user:
        # Map IBAN to user_id
        iban_to_user_id = {
            "DE89370400440532013000": "user_001",
            "GB29NWBK60161331926819": "user_002",
            "FR7630006000011234567890189": "user_003"
        }
        user_id = iban_to_user_id.get(verified_user.iban, "unknown")
    
    # Step 7: Invoke LLM with conversation history
    try:
        # Build messages for LLM (system prompt as SystemMessage)
        llm_messages = [SystemMessage(content=system_prompt)] + list(messages)

        # Get LLM response
        response = llm_with_tools.invoke(llm_messages)

        # Check if LLM wants to call tools
        if response.tool_calls:
            # Append the assistant message with tool_calls to the conversation
            tool_messages = [response]

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = dict(tool_call["args"])

                # Always force the authenticated user's user_id — the LLM cannot know the internal ID
                tool_args["user_id"] = user_id

                # Find and invoke the tool
                tool_func = next((t for t in tools if t.name == tool_name), None)

                if tool_func:
                    result = tool_func.invoke(tool_args)
                else:
                    result = {"error": f"Tool {tool_name} not found"}

                tool_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                )

            # Get final response with all tool results in context
            final_response = llm.invoke(llm_messages + tool_messages)
            response_message = final_response.content
        else:
            # No tool calls, use direct response
            response_message = response.content
        
        # Apply PII redaction to output
        response_message = check_pii(response_message, state.get("is_authenticated", False))
        
        logger.info(f"specialist_agent response generated successfully")
        
        # Step 8: Return updated state
        return {
            "messages": [AIMessage(content=response_message)],
            "current_agent": "specialist",
            "turn_count": turn_count + 1,
        }
        
    except Exception as e:
        logger.error(f"specialist_agent failed: {e}")
        error_message = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
        return {
            "messages": [AIMessage(content=error_message)],
            "current_agent": "specialist",
            "turn_count": turn_count + 1,
        }
