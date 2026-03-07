"""Pydantic data models for DEUS Bank AI Support System.

This module defines all data models used across agents, guardrails, and the API layer.
All models use Pydantic v2 for validation and serialization.
"""

from pydantic import BaseModel


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
    """Represents a bank account used to determine customer tier.
    
    Attributes:
        iban: Account IBAN (used as primary key for lookups)
        premium: Whether the account holder is a premium client
    """
    iban: str
    premium: bool


class ChatRequest(BaseModel):
    """Request body for the chat API endpoint.
    
    Attributes:
        session_id: Unique identifier for the conversation session
        message: The customer's input message
    """
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Response body for the chat API endpoint.
    
    Attributes:
        session_id: The conversation session identifier (matches request)
        response: The agent's response message
        agent: Name of the agent that produced the response (e.g., "greeter", "bouncer", "specialist")
    """
    session_id: str
    response: str
    agent: str
