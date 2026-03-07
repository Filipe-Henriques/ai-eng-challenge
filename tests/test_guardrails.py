"""Unit and integration tests for guardrails safety layer.

This module tests all three guardrail functions (toxicity, topic, PII)
as well as the orchestrator function that combines them.
"""

import pytest
import time
from unittest.mock import Mock, patch
from app.guardrails.guardrails import (
    GuardrailResult,
    check_toxicity,
    check_topic,
    check_pii,
    run_guardrails,
)


class TestGuardrailResult:
    """Tests for GuardrailResult Pydantic model."""
    
    def test_safe_result_validation(self):
        """Test that safe results must have None for blocking fields."""
        result = GuardrailResult(
            is_safe=True,
            blocked_reason=None,
            safe_response=None,
            sanitised_response="test response"
        )
        assert result.is_safe is True
        assert result.blocked_reason is None
        assert result.safe_response is None
    
    def test_blocked_result_validation(self):
        """Test that blocked results must have non-None blocking fields."""
        result = GuardrailResult(
            is_safe=False,
            blocked_reason="toxic",
            safe_response="Please be respectful",
            sanitised_response=""
        )
        assert result.is_safe is False
        assert result.blocked_reason == "toxic"
        assert result.safe_response is not None
    
    def test_invalid_safe_with_blocked_reason_fails(self):
        """Test that is_safe=True with blocked_reason raises validation error."""
        with pytest.raises(ValueError):
            GuardrailResult(
                is_safe=True,
                blocked_reason="toxic",
                safe_response=None,
                sanitised_response="test"
            )
    
    def test_invalid_blocked_without_reason_fails(self):
        """Test that is_safe=False without blocked_reason raises validation error."""
        with pytest.raises(ValueError):
            GuardrailResult(
                is_safe=False,
                blocked_reason=None,
                safe_response="test",
                sanitised_response=""
            )


class TestToxicityDetection:
    """Tests for check_toxicity function."""
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_toxic_message_returns_warning(self, mock_client):
        """Test that toxic messages return warning message."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "toxic"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = check_toxicity("You're useless!")
        
        assert result is not None
        assert "frustrated" in result.lower() or "respectful" in result.lower()
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_safe_message_returns_none(self, mock_client):
        """Test that safe messages return None."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "safe"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = check_toxicity("What's my account balance?")
        
        assert result is None
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_llm_timeout_returns_error_message(self, mock_client):
        """Test that LLM timeout returns error message (fail-closed)."""
        from openai import APITimeoutError
        mock_client.chat.completions.create.side_effect = APITimeoutError("timeout")
        
        result = check_toxicity("Test message")
        
        assert result is not None
        assert "technical difficulties" in result.lower() or "error" in result.lower()
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_llm_error_returns_error_message(self, mock_client):
        """Test that LLM errors return error message (fail-closed)."""
        mock_client.chat.completions.create.side_effect = Exception("API error")
        
        result = check_toxicity("Test message")
        
        assert result is not None


class TestTopicFiltering:
    """Tests for check_topic function."""
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_off_topic_message_returns_refusal(self, mock_client):
        """Test that off-topic messages return refusal message."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "off_topic"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = check_topic("How do I code in Python?")
        
        assert result is not None
        assert "banking" in result.lower()
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_on_topic_message_returns_none(self, mock_client):
        """Test that on-topic messages return None."""
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "on_topic"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = check_topic("What's my account balance?")
        
        assert result is None
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_llm_timeout_returns_error_message(self, mock_client):
        """Test that LLM timeout returns error message (fail-closed)."""
        from openai import APITimeoutError
        mock_client.chat.completions.create.side_effect = APITimeoutError("timeout")
        
        result = check_topic("Test message")
        
        assert result is not None
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_banking_complaint_is_on_topic(self, mock_client):
        """Test that frustrated banking complaints are still on-topic."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "on_topic"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = check_topic("I hate waiting so long for transfers!")
        
        assert result is None


class TestPIIProtection:
    """Tests for check_pii function."""
    
    def test_phone_number_redacted_when_unauthenticated(self):
        """Test that phone numbers are redacted for unauthenticated users."""
        response = "Call us at +1122334455"
        result = check_pii(response, is_authenticated=False)
        
        assert "[REDACTED]" in result
        assert "+1122334455" not in result
    
    def test_iban_redacted_when_unauthenticated(self):
        """Test that IBANs are redacted for unauthenticated users."""
        response = "Your IBAN is DE89370400440532013000"
        result = check_pii(response, is_authenticated=False)
        
        assert "[REDACTED]" in result
        assert "DE89370400440532013000" not in result
    
    def test_phone_number_visible_when_authenticated(self):
        """Test that phone numbers are visible for authenticated users."""
        response = "Call us at +1122334455"
        result = check_pii(response, is_authenticated=True)
        
        assert "+1122334455" in result
        assert "[REDACTED]" not in result
    
    def test_iban_visible_when_authenticated(self):
        """Test that IBANs are visible for authenticated users."""
        response = "Your IBAN is DE89370400440532013000"
        result = check_pii(response, is_authenticated=True)
        
        assert "DE89370400440532013000" in result
        assert "[REDACTED]" not in result
    
    def test_multiple_pii_instances_all_redacted(self):
        """Test that multiple PII instances are all redacted."""
        response = "Call +1234567890 or +9876543210 for IBAN GB82WEST12345698765432"
        result = check_pii(response, is_authenticated=False)
        
        assert result.count("[REDACTED]") == 3
        assert "+1234567890" not in result
        assert "+9876543210" not in result
        assert "GB82WEST12345698765432" not in result
    
    def test_no_pii_returns_unchanged(self):
        """Test that responses without PII return unchanged."""
        response = "Your balance is $1,234.56"
        result = check_pii(response, is_authenticated=False)
        
        assert result == response
    
    def test_international_phone_formats(self):
        """Test various international phone number formats are detected."""
        test_cases = [
            "+1 122 334 455",
            "+1-122-334-455",
            "+1 (122) 334-455",
            "1223344556",
        ]
        
        for phone in test_cases:
            response = f"Contact: {phone}"
            result = check_pii(response, is_authenticated=False)
            assert "[REDACTED]" in result, f"Failed to redact: {phone}"
    
    def test_various_iban_formats(self):
        """Test various European IBAN formats are detected."""
        test_cases = [
            "DE89370400440532013000",  # Germany
            "GB82WEST12345698765432",  # UK
            "FR1420041010050500013M02606",  # France
        ]
        
        for iban in test_cases:
            response = f"IBAN: {iban}"
            result = check_pii(response, is_authenticated=False)
            assert "[REDACTED]" in result, f"Failed to redact: {iban}"


class TestGuardrailsOrchestrator:
    """Tests for run_guardrails orchestrator function."""
    
    @patch('app.guardrails.guardrails.check_toxicity')
    @patch('app.guardrails.guardrails.check_topic')
    @patch('app.guardrails.guardrails.check_pii')
    def test_toxic_message_short_circuits(self, mock_pii, mock_topic, mock_toxicity):
        """Test that toxic messages short-circuit before topic/PII checks."""
        mock_toxicity.return_value = "Toxic warning"
        mock_topic.return_value = None
        mock_pii.return_value = "response"
        
        result = run_guardrails(
            message="Toxic message",
            proposed_response="Some response",
            is_authenticated=True
        )
        
        assert result.is_safe is False
        assert result.blocked_reason == "toxic"
        # Topic and PII should not be called due to short-circuit
        mock_topic.assert_not_called()
        mock_pii.assert_not_called()
    
    @patch('app.guardrails.guardrails.check_toxicity')
    @patch('app.guardrails.guardrails.check_topic')
    @patch('app.guardrails.guardrails.check_pii')
    def test_off_topic_message_short_circuits(self, mock_pii, mock_topic, mock_toxicity):
        """Test that off-topic messages short-circuit before PII check."""
        mock_toxicity.return_value = None
        mock_topic.return_value = "Off-topic refusal"
        mock_pii.return_value = "response"
        
        result = run_guardrails(
            message="Off-topic message",
            proposed_response="Some response",
            is_authenticated=True
        )
        
        assert result.is_safe is False
        assert result.blocked_reason == "off_topic"
        # PII should not be called due to short-circuit
        mock_pii.assert_not_called()
    
    @patch('app.guardrails.guardrails.check_toxicity')
    @patch('app.guardrails.guardrails.check_topic')
    @patch('app.guardrails.guardrails.check_pii')
    def test_safe_message_runs_all_checks(self, mock_pii, mock_topic, mock_toxicity):
        """Test that safe messages run all checks and return sanitized response."""
        mock_toxicity.return_value = None
        mock_topic.return_value = None
        mock_pii.return_value = "Sanitized response"
        
        result = run_guardrails(
            message="What's my balance?",
            proposed_response="Your balance is $1,234.56",
            is_authenticated=True
        )
        
        assert result.is_safe is True
        assert result.blocked_reason is None
        assert result.safe_response is None
        assert result.sanitised_response == "Sanitized response"
        
        # All checks should be called
        mock_toxicity.assert_called_once()
        mock_topic.assert_called_once()
        mock_pii.assert_called_once()
    
    @patch('app.guardrails.guardrails.check_toxicity')
    def test_unexpected_exception_returns_error_result(self, mock_toxicity):
        """Test that unexpected exceptions return error GuardrailResult."""
        mock_toxicity.side_effect = Exception("Unexpected error")
        
        result = run_guardrails(
            message="Test message",
            proposed_response="Test response",
            is_authenticated=True
        )
        
        assert result.is_safe is False
        assert result.blocked_reason == "error"
        assert result.safe_response is not None
    
    def test_integration_safe_message_with_pii_redaction(self):
        """Integration test: Safe message with PII redaction."""
        # This test uses mocked LLM but real PII detection
        with patch('app.guardrails.guardrails.openai_client') as mock_client:
            # Mock safe responses from LLM
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "safe"
            mock_client.chat.completions.create.return_value = mock_response
            
            result = run_guardrails(
                message="How can I contact you?",
                proposed_response="Call us at +1122334455",
                is_authenticated=False
            )
            
            assert result.is_safe is True
            assert "[REDACTED]" in result.sanitised_response
            assert "+1122334455" not in result.sanitised_response


class TestPerformance:
    """Performance tests for guardrails."""
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_p95_latency_under_500ms(self, mock_client):
        """Test that p95 latency is under 500ms."""
        import time
        
        # Mock fast LLM responses
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "safe"
        mock_client.chat.completions.create.return_value = mock_response
        
        latencies = []
        for _ in range(100):
            start = time.time()
            run_guardrails(
                message="What's my balance?",
                proposed_response="Your balance is $1,234.56",
                is_authenticated=True
            )
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
        
        latencies.sort()
        p95_latency = latencies[94]  # 95th percentile
        
        assert p95_latency < 500, f"P95 latency {p95_latency:.2f}ms exceeds 500ms target"
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_average_latency_under_200ms(self, mock_client):
        """Test that average latency is under 200ms."""
        import time
        
        # Mock fast LLM responses
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "safe"
        mock_client.chat.completions.create.return_value = mock_response
        
        latencies = []
        for _ in range(50):
            start = time.time()
            run_guardrails(
                message="What's my balance?",
                proposed_response="Your balance is $1,234.56",
                is_authenticated=True
            )
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        
        assert avg_latency < 200, f"Average latency {avg_latency:.2f}ms exceeds 200ms target"


class TestFalsePositiveRate:
    """Test false positive rate for legitimate frustrated messages."""
    
    @patch('app.guardrails.guardrails.openai_client')
    def test_frustrated_banking_messages_low_false_positive_rate(self, mock_client):
        """Test that frustrated but legitimate banking messages have <5% false positive rate."""
        # Mock LLM to always return safe for legitimate banking queries
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "safe"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Sample of frustrated but legitimate banking messages
        frustrated_messages = [
            "I've been waiting forever for my transfer!",
            "This is taking way too long!",
            "I'm very frustrated with this delay",
            "Why is this so slow?",
            "I need help NOW!",
            "This is unacceptable!",
            "I'm not happy with this service",
            "Can someone please help me urgently?",
            "I've called three times already!",
            "This is ridiculous!",
        ]
        
        false_positives = 0
        for message in frustrated_messages:
            result = run_guardrails(
                message=message,
                proposed_response="I understand your frustration. Let me help.",
                is_authenticated=True
            )
            if not result.is_safe:
                false_positives += 1
        
        false_positive_rate = (false_positives / len(frustrated_messages)) * 100
        
        assert false_positive_rate < 5, (
            f"False positive rate {false_positive_rate:.1f}% exceeds 5% target "
            f"({false_positives}/{len(frustrated_messages)} messages blocked)"
        )

# =============================================================================
# Feature 009-testing-strategy: Required Test Names
# =============================================================================
# The following tests implement the specific test names required by
# the testing strategy spec (009). Some overlap with existing tests above.


@patch("app.guardrails.guardrails.openai_client")
def test_toxicity_detected(mock_client):
    """Test check_toxicity returns warning when LLM classifies message as toxic."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "toxic"
    mock_client.chat.completions.create.return_value = mock_response
    
    from app.guardrails.config import TOXICITY_WARNING
    result = check_toxicity("You're useless!")
    
    assert result == TOXICITY_WARNING


@patch("app.guardrails.guardrails.openai_client")
def test_toxicity_safe(mock_client):
    """Test check_toxicity returns None when LLM classifies message as safe."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "safe"
    mock_client.chat.completions.create.return_value = mock_response
    
    result = check_toxicity("What's my account balance?")
    
    assert result is None


@patch("app.guardrails.guardrails.openai_client")
def test_topic_off_topic(mock_client):
    """Test check_topic returns refusal when LLM classifies as off-topic."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "off_topic"
    mock_client.chat.completions.create.return_value = mock_response
    
    from app.guardrails.config import OFF_TOPIC_REFUSAL
    result = check_topic("How do I code in Python?")
    
    assert result == OFF_TOPIC_REFUSAL


@patch("app.guardrails.guardrails.openai_client")
def test_topic_on_topic(mock_client):
    """Test check_topic returns None when LLM classifies as on-topic."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "on_topic"
    mock_client.chat.completions.create.return_value = mock_response
    
    result = check_topic("What's my account balance?")
    
    assert result is None


def test_pii_phone_redacted():
    """Test check_pii redacts phone numbers for unauthenticated users."""
    response = "Please call us at +1122334455 for assistance."
    result = check_pii(response, is_authenticated=False)
    
    assert "[REDACTED]" in result
    assert "+1122334455" not in result


def test_pii_iban_redacted():
    """Test check_pii redacts IBANs for unauthenticated users."""
    response = "Your IBAN is DE89370400440532013000."
    result = check_pii(response, is_authenticated=False)
    
    assert "[REDACTED]" in result
    assert "DE89370400440532013000" not in result


def test_pii_authenticated_unchanged():
    """Test check_pii returns response unchanged for authenticated users."""
    response = "Your phone is +1122334455 and IBAN is DE89370400440532013000."
    result = check_pii(response, is_authenticated=True)
    
    assert result == response
    assert "+1122334455" in result
    assert "DE89370400440532013000" in result
    assert "[REDACTED]" not in result


@patch("app.guardrails.guardrails.check_toxicity")
@patch("app.guardrails.guardrails.check_topic")
@patch("app.guardrails.guardrails.check_pii")
def test_guardrails_short_circuit_toxicity(mock_pii, mock_topic, mock_toxicity):
    """Test run_guardrails short-circuits when toxicity is detected."""
    from app.guardrails.config import TOXICITY_WARNING
    mock_toxicity.return_value = TOXICITY_WARNING
    
    result = run_guardrails(
        message="You're useless!",
        proposed_response="",
        is_authenticated=False
    )
    
    assert result.is_safe is False
    assert result.blocked_reason == "toxic"
    assert not mock_topic.called
    assert not mock_pii.called


@patch("app.guardrails.guardrails.check_toxicity")
@patch("app.guardrails.guardrails.check_topic")
@patch("app.guardrails.guardrails.check_pii")
def test_guardrails_short_circuit_topic(mock_pii, mock_topic, mock_toxicity):
    """Test run_guardrails short-circuits when off-topic is detected."""
    from app.guardrails.config import OFF_TOPIC_REFUSAL
    mock_toxicity.return_value = None
    mock_topic.return_value = OFF_TOPIC_REFUSAL
    
    result = run_guardrails(
        message="How do I code in Python?",
        proposed_response="",
        is_authenticated=False
    )
    
    assert result.is_safe is False
    assert result.blocked_reason == "off_topic"
    assert not mock_pii.called


@patch("app.guardrails.guardrails.check_toxicity")
@patch("app.guardrails.guardrails.check_topic")
@patch("app.guardrails.guardrails.check_pii")
def test_guardrails_safe_applies_pii(mock_pii, mock_topic, mock_toxicity):
    """Test run_guardrails applies PII redaction when all checks pass."""
    mock_toxicity.return_value = None
    mock_topic.return_value = None
    mock_pii.return_value = "Your balance is [REDACTED]"
    
    result = run_guardrails(
        message="What's my balance?",
        proposed_response="Your balance is 5000.00 EUR",
        is_authenticated=False
    )
    
    assert result.is_safe is True
    assert result.blocked_reason is None
    assert result.safe_response is None
    assert result.sanitised_response == "Your balance is [REDACTED]"
    assert mock_pii.called
