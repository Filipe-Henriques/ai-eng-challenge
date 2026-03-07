"""LangGraph components for DEUS Bank AI Support System.

This package provides the shared state structure and initialization logic
for the conversation graph pipeline.

Exports:
    State: TypedDict defining all shared state fields
    create_initial_state: Factory function for initializing new conversation state
"""

from app.graph.state import State, create_initial_state

__all__ = ["State", "create_initial_state"]

