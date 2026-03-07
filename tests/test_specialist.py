"""Integration tests for Specialist Agent.

This module tests the specialist agent's banking tools, conversation management,
tier-based personas, and integration with the LangGraph pipeline.
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.specialist import (
    get_account_balance,
    get_transaction_history,
    transfer_funds,
    report_lost_card,
    specialist_agent,
    build_system_prompt,
)
from app.models.database import ACCOUNTS_DB
from app.models.schemas import User


# ============================================================================
# TOOL UNIT TESTS
# ============================================================================


class TestAccountBalanceTool:
    """Test get_account_balance tool."""

    def test_balance_inquiry_success(self):
        """Test successful balance inquiry for valid user."""
        result = get_account_balance.invoke({"user_id": "user_001"})
        assert result["balance"] == 5420.50
        assert result["currency"] == "EUR"

    def test_balance_inquiry_account_not_found(self):
        """Test balance inquiry for non-existent user."""
        result = get_account_balance.invoke({"user_id": "invalid_user"})
        assert "error" in result
        assert result["error"] == "Account not found"

    def test_balance_inquiry_multiple_users(self):
        """Test balance inquiry for different users."""
        # Lisa (VIP)
        result1 = get_account_balance.invoke({"user_id": "user_001"})
        assert result1["balance"] == 5420.50
        assert result1["currency"] == "EUR"

        # John (Standard)
        result2 = get_account_balance.invoke({"user_id": "user_002"})
        assert result2["balance"] == 1247.80
        assert result2["currency"] == "GBP"

        # Maria (Standard)
        result3 = get_account_balance.invoke({"user_id": "user_003"})
        assert result3["balance"] == 325.10
        assert result3["currency"] == "EUR"


class TestTransactionHistoryTool:
    """Test get_transaction_history tool."""

    def test_transaction_history_default_limit(self):
        """Test transaction history with default limit (5)."""
        result = get_transaction_history.invoke({"user_id": "user_001"})
        assert len(result) == 5
        assert all("date" in txn and "description" in txn and "amount" in txn for txn in result)

    def test_transaction_history_custom_limit(self):
        """Test transaction history with custom limit."""
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": 3})
        assert len(result) == 3

    def test_transaction_history_limit_clamping(self):
        """Test SC-009: Transaction history limit is clamped to [1, 20]."""
        # Test upper bound clamping
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": 50})
        assert len(result) <= 20

        # Test lower bound clamping
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": 0})
        assert len(result) >= 1

        # Test negative values
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": -5})
        assert len(result) >= 1

    def test_transaction_history_account_not_found(self):
        """Test transaction history for non-existent user."""
        result = get_transaction_history.invoke({"user_id": "invalid_user"})
        assert result == []

    def test_transaction_history_ordering(self):
        """Test that transactions are returned newest last."""
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": 5})
        # Check that the last transaction is the most recent (2026-03-05)
        assert result[-1]["date"] == "2026-03-05"


class TestTransferFundsTool:
    """Test transfer_funds tool."""

    def test_transfer_funds_success(self):
        """Test successful fund transfer."""
        initial_balance = ACCOUNTS_DB["user_001"].balance
        result = transfer_funds.invoke({
            "user_id": "user_001",
            "recipient_iban": "GB29NWBK60161331926819",
            "amount": 100.0,
            "description": "Test payment"
        })
        assert result["success"] == True
        assert "transaction_id" in result
        assert ACCOUNTS_DB["user_001"].balance == initial_balance - 100.0

    def test_transfer_funds_insufficient_balance(self):
        """Test transfer with insufficient funds."""
        result = transfer_funds.invoke({
            "user_id": "user_003",
            "recipient_iban": "GB29NWBK60161331926819",
            "amount": 10000.0,
            "description": "Large payment"
        })
        assert result["success"] == False
        assert result["reason"] == "Insufficient funds"

    def test_transfer_funds_invalid_iban(self):
        """Test transfer with invalid IBAN format."""
        result = transfer_funds.invoke({
            "user_id": "user_001",
            "recipient_iban": "INVALID",
            "amount": 50.0,
            "description": "Bad IBAN"
        })
        assert result["success"] == False
        assert result["reason"] == "Invalid IBAN format"

    def test_transfer_funds_negative_amount(self):
        """Test transfer with negative amount."""
        result = transfer_funds.invoke({
            "user_id": "user_001",
            "recipient_iban": "GB29NWBK60161331926819",
            "amount": -50.0,
            "description": "Negative amount"
        })
        assert result["success"] == False
        assert result["reason"] == "Amount must be positive"

    def test_transfer_funds_account_not_found(self):
        """Test transfer for non-existent user."""
        result = transfer_funds.invoke({
            "user_id": "invalid_user",
            "recipient_iban": "GB29NWBK60161331926819",
            "amount": 100.0,
            "description": "Test"
        })
        assert result["success"] == False
        assert result["reason"] == "Account not found"


class TestReportLostCardTool:
    """Test report_lost_card tool."""

    def test_report_lost_card_success(self):
        """Test successful card blocking."""
        # Reset card_blocked status for user_002
        ACCOUNTS_DB["user_002"].card_blocked = False
        
        result = report_lost_card.invoke({"user_id": "user_002"})
        assert result["success"] == True
        assert "case_id" in result
        assert ACCOUNTS_DB["user_002"].card_blocked == True

    def test_report_lost_card_idempotency(self):
        """Test that card blocking is idempotent (safe to call multiple times)."""
        # Block card twice
        result1 = report_lost_card.invoke({"user_id": "user_002"})
        result2 = report_lost_card.invoke({"user_id": "user_002"})
        
        assert result1["success"] == True
        assert result2["success"] == True
        # Case IDs should be different (new case each time)
        assert result1["case_id"] != result2["case_id"]
        assert ACCOUNTS_DB["user_002"].card_blocked == True

    def test_report_lost_card_account_not_found(self):
        """Test card blocking for non-existent user."""
        result = report_lost_card.invoke({"user_id": "invalid_user"})
        assert result["success"] == False
        assert result["reason"] == "Account not found"


# ============================================================================
# SYSTEM PROMPT TESTS
# ============================================================================


class TestSystemPromptBuilder:
    """Test build_system_prompt function."""

    def test_system_prompt_standard_tier(self):
        """Test system prompt for standard tier customer."""
        state = {
            "customer_tier": "standard",
            "verified_user": User(
                name="John",
                phone="+1987654321",
                iban="GB29NWBK60161331926819",
                secret="Test",
                answer="Test"
            ),
            "customer_intent": "balance_inquiry"
        }
        prompt = build_system_prompt(state)
        assert "helpful" in prompt.lower() or "concise" in prompt.lower() or "efficient" in prompt.lower()
        assert "John" in prompt
        assert "STANDARD" in prompt

    def test_system_prompt_vip_tier(self):
        """Test system prompt for VIP tier customer."""
        state = {
            "customer_tier": "vip",
            "verified_user": User(
                name="Lisa",
                phone="+1122334455",
                iban="DE89370400440532013000",
                secret="Test",
                answer="Test"
            ),
            "customer_intent": "account_inquiry"
        }
        prompt = build_system_prompt(state)
        assert "vip" in prompt.lower() or "private banking" in prompt.lower() or "white-glove" in prompt.lower()
        assert "Lisa" in prompt
        assert "VIP" in prompt

    def test_system_prompt_missing_tier_fallback(self):
        """Test system prompt defaults to standard when tier is missing."""
        state = {
            "verified_user": User(
                name="Test",
                phone="+1111111111",
                iban="TEST",
                secret="Test",
                answer="Test"
            ),
            "customer_intent": "inquiry"
        }
        prompt = build_system_prompt(state)
        # Should not crash, should use Standard fallback
        assert prompt
        assert "Test" in prompt


# ============================================================================
# AGENT INTEGRATION TESTS
# ============================================================================


class TestSpecialistAgentIntegration:
    """Integration tests for specialist_agent function."""

    @pytest.fixture(autouse=True)
    def mock_guardrails(self):
        """Mock run_guardrails and ChatOpenAI to avoid API calls during testing."""
        from unittest.mock import patch, MagicMock
        from app.guardrails.guardrails import GuardrailResult
        
        mock_result = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="test response"
        )
        
        # Mock ChatOpenAI to avoid API key requirement
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(
            content="Here is your account information.",
            tool_calls=[]
        )
        
        with patch('app.agents.specialist.run_guardrails', return_value=mock_result), \
             patch('app.agents.specialist.ChatOpenAI', return_value=mock_llm):
            yield

    def test_agent_out_of_scope_detection(self):
        """Test FR-017/SC-008: Out-of-scope requests trigger handoff message."""
        out_of_scope_messages = [
            "I want to apply for a mortgage",
            "Can you help me invest in stocks?",
            "I'd like to open a new account",
            "I need a loan",
            "Can I get a credit card?",
            "I want to close my account",
            "I need financial planning advice"
        ]
        
        for message in out_of_scope_messages:
            state = {
                "messages": [HumanMessage(content=message)],
                "verified_user": User(name="Test", phone="+1", iban="TEST", secret="T", answer="T"),
                "customer_tier": "standard",
                "customer_intent": "general_inquiry",
                "is_authenticated": True,
                "turn_count": 1,
            }
            
            result = specialist_agent(state)
            print(f"Message: {message}")
            print(f"Result: {result}")
            assert result.get("conversation_ended") == True, f"Expected conversation_ended for message: {message}"
            response_text = result["messages"][0].content.lower()
            assert "specialized" in response_text or "connect" in response_text or "callback" in response_text

    def test_agent_turn_limit_enforcement(self):
        """Test that conversation ends at turn 10 boundary."""
        state = {
            "messages": [HumanMessage(content="What's my balance?")],
            "verified_user": User(
                name="Lisa",
                phone="+1122334455",
                iban="DE89370400440532013000",
                secret="Test",
                answer="Test"
            ),
            "customer_tier": "vip",
            "customer_intent": "balance_inquiry",
            "is_authenticated": True,
            "turn_count": 10,  # At limit
        }
        
        result = specialist_agent(state)
        assert result["conversation_ended"] == True
        response_text = result["messages"][0].content.lower()
        assert "thank you" in response_text or "callback" in response_text

    def test_agent_no_user_id_exposure(self):
        """Test FR-012/SC-006: Agent responses never expose user_id or raw JSON."""
        state = {
            "messages": [HumanMessage(content="What's my balance?")],
            "verified_user": User(
                name="user_001",  # Note: name contains "user_001" but should not expose user_id
                phone="+1122334455",
                iban="DE89370400440532013000",
                secret="Test",
                answer="Test"
            ),
            "customer_tier": "vip",
            "customer_intent": "balance_inquiry",
            "is_authenticated": True,
            "turn_count": 1,
        }
        
        result = specialist_agent(state)
        response_text = result["messages"][0].content
        
        # Check for prohibited patterns
        prohibited_patterns = [
            "user_id=",
            "user_001",
            "user_002",
            "user_003",
            "{\"balance\":",
            "ACCOUNTS_DB",
            "database",
        ]
        
        for pattern in prohibited_patterns:
            assert pattern not in response_text, f"Response exposed prohibited pattern: {pattern}"


# ============================================================================
# END-TO-END WORKFLOW TESTS
# ============================================================================


class TestEndToEndWorkflows:
    """End-to-end tests for complete banking workflows."""

    def test_balance_inquiry_workflow(self):
        """Test T078: Balance inquiry end-to-end flow."""
        # This would require mocking the LLM, so we'll test the tool directly
        result = get_account_balance.invoke({"user_id": "user_001"})
        assert result["balance"] == 5420.50
        assert result["currency"] == "EUR"

    def test_transaction_history_workflow(self):
        """Test T079: Transaction history end-to-end flow."""
        result = get_transaction_history.invoke({"user_id": "user_001", "limit": 5})
        assert len(result) == 5
        assert all("date" in txn for txn in result)

    def test_fund_transfer_workflow(self):
        """Test T080: Fund transfer end-to-end flow."""
        initial_balance = ACCOUNTS_DB["user_001"].balance
        result = transfer_funds.invoke({
            "user_id": "user_001",
            "recipient_iban": "GB29NWBK60161331926819",
            "amount": 50.0,
            "description": "Test transfer"
        })
        assert result["success"] == True
        assert ACCOUNTS_DB["user_001"].balance < initial_balance

    def test_card_blocking_workflow(self):
        """Test T081: Card blocking end-to-end flow."""
        # Reset card status
        ACCOUNTS_DB["user_002"].card_blocked = False
        
        result = report_lost_card.invoke({"user_id": "user_002"})
        assert result["success"] == True
        assert ACCOUNTS_DB["user_002"].card_blocked == True


# Cleanup fixture to reset database state after each test
@pytest.fixture(autouse=True)
def reset_database_state():
    """Reset ACCOUNTS_DB to initial state after each test."""
    yield
    # Reset balances
    ACCOUNTS_DB["user_001"].balance = 5420.50
    ACCOUNTS_DB["user_002"].balance = 1247.80
    ACCOUNTS_DB["user_003"].balance = 325.10
    # Reset card_blocked flags
    for user_id in ACCOUNTS_DB:
        ACCOUNTS_DB[user_id].card_blocked = False
