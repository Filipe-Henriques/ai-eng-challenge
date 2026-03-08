"""Chat API endpoint for the DEUS Bank AI Support System.

This module defines the POST /chat endpoint that manages session state,
invokes the LangGraph pipeline, and returns structured responses.
"""

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage
import logging

from app.models.schemas import ChatRequest, ChatResponse
from app.graph.state import State
from app.graph.pipeline import graph

logger = logging.getLogger(__name__)

# Module-level session store
SESSION_STORE: dict[str, State] = {}

router = APIRouter()


def create_initial_state(session_id: str) -> State:
    """Create a new State with default values for a new session.
    
    Args:
        session_id: Unique identifier for the session
        
    Returns:
        State: Initialized state with all default fields
    """
    return {
        "messages": [],
        "session_id": session_id,
        "verified_user": None,
        "is_authenticated": False,
        "customer_tier": None,
        "customer_intent": None,
        "current_agent": "greeter",
        "collected_fields": {},
        "verification_attempts": 0,
        "specialist_needed": False,
        "conversation_ended": False,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Handle chat requests and return agent responses.
    
    This endpoint manages the conversation session lifecycle:
    1. Loads or creates a session state
    2. Guards against ended conversations
    3. Appends the user message to conversation history
    4. Invokes the LangGraph pipeline asynchronously
    5. Saves the updated state
    6. Extracts and returns the agent's response
    
    Args:
        request: ChatRequest with session_id and message
        
    Returns:
        ChatResponse: Agent's response with session metadata
        
    Raises:
        HTTPException: 500 if graph invocation fails or response extraction fails
    """
    # Load or create session
    if request.session_id not in SESSION_STORE:
        SESSION_STORE[request.session_id] = create_initial_state(request.session_id)
    
    state = SESSION_STORE[request.session_id]
    
    # Guard: Check if conversation has ended
    if state["conversation_ended"]:
        return ChatResponse(
            session_id=request.session_id,
            response="This conversation has ended. Please start a new session.",
            current_agent=state["current_agent"],
            is_authenticated=state["is_authenticated"],
            conversation_ended=True,
        )
    
    # Append user message to conversation history
    state["messages"].append(HumanMessage(content=request.message))
    
    # Invoke graph with error handling
    try:
        updated_state = await graph.ainvoke(state)
    except Exception as e:
        logger.error(
            f"Graph invocation failed for session {request.session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred.",
        )
    
    # Save updated state
    SESSION_STORE[request.session_id] = updated_state
    
    # Extract response from last message
    if not updated_state["messages"]:
        logger.error(
            f"No messages in state after graph invocation for session {request.session_id}"
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred.",
        )
    
    last_message = updated_state["messages"][-1]
    
    if not isinstance(last_message, AIMessage):
        logger.error(
            f"Last message is not AIMessage for session {request.session_id}: {type(last_message)}"
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred.",
        )
    
    # Build and return response
    return ChatResponse(
        session_id=request.session_id,
        response=last_message.content,
        current_agent=updated_state["current_agent"],
        is_authenticated=updated_state["is_authenticated"],
        conversation_ended=updated_state["conversation_ended"],
    )
