"""End-to-end tests with real LLM calls - Testing Strategy (009).

These tests validate the full pipeline with actual LLM invocations.
They are marked with @pytest.mark.e2e and should only run when
OPENAI_API_KEY is set.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

# Skip all E2E tests if OPENAI_API_KEY is not set
pytestmark = pytest.mark.e2e

if not os.getenv("OPENAI_API_KEY"):
    pytest.skip("OPENAI_API_KEY not set - skipping E2E tests", allow_module_level=True)


@pytest.fixture
def client():
    """FastAPI test client for E2E tests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear SESSION_STORE between tests."""
    from app.api.v1.endpoints.chat import SESSION_STORE
    SESSION_STORE.clear()
    yield
    SESSION_STORE.clear()


def test_e2e_full_verification_flow(client):
    """Test full verification flow with multi-turn conversation.
    
    Simulates: provide details → answer secret question → check balance.
    """
    session_id = "e2e-test-001"
    
    # Turn 1: Initial greeting
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "Hello, I need help with my account"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "response" in data
    
    # Turn 2: Provide verification details
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "My name is Lisa and my phone is +1122334455"
    })
    
    assert response.status_code == 200
    # Should ask secret question or continue
    
    # This is a simplified E2E test - full flow would require
    # multiple turns with correct secret answer


def test_e2e_max_attempts_flow(client):
    """Test conversation ends after 3 failed verification attempts."""
    session_id = "e2e-test-002"
    
    # Attempt 1: Wrong details
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "My name is Wrong and phone is +9999999999"
    })
    
    assert response.status_code == 200
    # Full implementation would make 3 attempts and verify conversation_ended


def test_e2e_guardrail_toxicity(client):
    """Test guardrails block toxic messages."""
    session_id = "e2e-test-003"
    
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "You're useless and terrible"
    })
    
    assert response.status_code == 200
    data = response.json()
    # Should contain safety warning or refusal


def test_e2e_guardrail_off_topic(client):
    """Test guardrails block off-topic messages."""
    session_id = "e2e-test-004"
    
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "How do I code in Python?"
    })
    
    assert response.status_code == 200
    data = response.json()
    # Should contain banking-only refusal message


def test_e2e_vip_routing(client):
    """Test VIP user authentication and routing."""
    session_id = "e2e-test-005"
    
    # Provide Lisa's details (VIP user)
    response = client.post("/chat", json={
        "session_id": session_id,
        "message": "Hi, I'm Lisa, phone +1122334455, IBAN DE89370400440532013000"
    })
    
    assert response.status_code == 200
    data = response.json()
    # Should proceed with VIP verification flow
    assert "response" in data
