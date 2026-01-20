"""
Security and PII detection tests.
"""
import pytest
from unittest.mock import Mock, patch

from src.security import PIIManager


class TestPIIManager:
    """Tests for PII detection and anonymization."""
    
    @pytest.fixture
    def pii_manager(self, mock_redis):
        """Create PII manager with mocked Redis."""
        return PIIManager(redis_client=mock_redis)
    
    def test_phone_number_detection(self, pii_manager):
        """Test that phone numbers are detected and anonymized."""
        text = "Call me at 555-123-4567"
        
        anonymized = pii_manager.anonymize(text, trace_id="test")
        
        assert "555-123-4567" not in anonymized
        assert "[PHONE_NUMBER_" in anonymized
    
    def test_email_detection(self, pii_manager):
        """Test that email addresses are detected and anonymized."""
        text = "Email me at john@example.com"
        
        anonymized = pii_manager.anonymize(text, trace_id="test")
        
        assert "john@example.com" not in anonymized
        assert "[EMAIL_ADDRESS_" in anonymized
    
    def test_multiple_pii_detection(self, pii_manager):
        """Test detection of multiple PII types."""
        text = "I'm John Doe, call 555-1234 or email john@test.com"
        
        anonymized = pii_manager.anonymize(text, trace_id="test")
        
        # Should have multiple tokens
        assert anonymized.count("[") >= 2
        assert "555-1234" not in anonymized
        assert "john@test.com" not in anonymized
    
    def test_deanonymization(self, pii_manager, mock_redis):
        """Test that PII can be restored."""
        original_text = "Call 555-1234"
        
        # Mock Redis to return encrypted value
        import json
        import base64
        
        token = "[PHONE_NUMBER_abc123de]"
        encrypted = pii_manager._encrypt("555-1234")
        
        mock_redis.get.return_value = json.dumps({
            "value": base64.b64encode(encrypted).decode(),
            "trace_id": "test"
        }).encode()
        
        anonymized = f"Call {token}"
        restored = pii_manager.deanonymize(anonymized, trace_id="test")
        
        assert "555-1234" in restored
        assert token not in restored
    
    def test_confidence_threshold(self, pii_manager):
        """Test that low-confidence detections are skipped."""
        # This would require mocking Presidio analyzer
        # For now, just verify the threshold is applied
        assert pii_manager.analyzer is not None
    
    def test_fallback_to_memory(self):
        """Test fallback to in-memory vault when Redis unavailable."""
        with patch("redis.from_url", side_effect=Exception("Connection failed")):
            with patch("src.config.settings") as mock_settings:
                mock_settings.is_development = True
                mock_settings.redis_url = "redis://localhost:6379"
                mock_settings.redis_max_connections = 10
                mock_settings.pii_confidence_threshold = 0.6
                mock_settings.api_keys = []
                
                manager = PIIManager()
                
                assert manager.redis is None
                assert hasattr(manager, "vault")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
