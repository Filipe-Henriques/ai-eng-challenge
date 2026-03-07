"""Pydantic data models for DEUS Bank AI Support System.

This module defines all data models used across agents, guardrails, and the API layer.
All models use Pydantic v2 for validation and serialization.
"""

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """Represents a single banking transaction.
    
    Attributes:
        date: Transaction date in ISO 8601 format (YYYY-MM-DD)
        description: Human-readable transaction description
        amount: Transaction amount (negative for debits, positive for credits)
    """
    date: str
    description: str
    amount: float


class User(BaseModel):
    """Represents a registered bank customer used for identity verification.
    
    Attributes:
        name: Customer's full name
        phone: Phone number in international format (e.g., +1122334455)
        iban: IBAN in standard format (e.g., DE89370400440532013000)
        secret: Security question shown to the customer
        answer: Correct answer to the security question
    """
    name: str
    phone: str
    iban: str
    secret: str
    answer: str


class Account(BaseModel):
    """Represents a bank account with full transaction history.
    
    This model extends the original Account to support the Specialist Agent's
    banking tools.
    
    Attributes:
        user_id: Unique identifier linking to User (for ACCOUNTS_DB lookup)
        iban: Account IBAN (International Bank Account Number)
        premium: Whether the account holder is a premium client (determines tier)
        balance: Current account balance
        currency: Account currency code (e.g., "EUR", "USD", "GBP")
        transactions: List of recent transactions (newest last)
        card_blocked: Whether the account's card has been reported lost/stolen
    """
    user_id: str
    iban: str
    premium: bool
    balance: float
    currency: str
    transactions: list[Transaction]
    card_blocked: bool


class ChatRequest(BaseModel):
    """Request body for the chat API endpoint.
    
    Attributes:
        session_id: Unique identifier for the conversation session
        message: The customer's input message
    """
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    message: str = Field(..., min_length=1, description="Customer's message text")


class ChatResponse(BaseModel):
    """Response body for the chat API endpoint.
    
    Attributes:
        session_id: The conversation session identifier (matches request)
        response: The agent's response message
        current_agent: Name of the agent that handled this turn
        is_authenticated: Whether the customer has been authenticated
        conversation_ended: Whether the conversation has ended
    """
    session_id: str
    response: str
    current_agent: str
    is_authenticated: bool
    conversation_ended: bool
