"""
API endpoint tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
import time

from src.api import app
from src.config import settings

@pytest.fixture
def client():
    """Create a TestClient instance."""
    with TestClient(app) as c:
        yield c

class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "version" in data
    
    def test_ready_endpoint(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "checks" in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestEmailProcessing:
    """Tests for email processing endpoint."""
    
    def test_process_email_missing_text(self, client):
        """Test that empty email text is rejected."""
        response = client.post(
            "/process-email",
            json={"email_text": ""}
        )
        assert response.status_code == 422
    
    def test_process_email_too_long(self, client):
        """Test that overly long emails are rejected."""
        long_text = "a" * 25000
        response = client.post(
            "/process-email",
            json={"email_text": long_text}
        )
        assert response.status_code == 422
    
    @patch("src.api.graph")
    def test_process_email_success(self, mock_graph, client):
        """Test successful email processing."""
        # Fix: Use AsyncMock for async ainvoke method
        mock_graph.ainvoke = AsyncMock(return_value={
            "category": "lead",
            "confidence_score": 0.95,
            "company_name": "Test Corp",
            "email_draft": "Test draft email",
            "trace_id": "test-id"
        })
        
        response = client.post(
            "/process-email",
            json={"email_text": "I want to buy your product"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "lead"
        assert data["company"] == "Test Corp"
        assert "trace_id" in data
    
    def test_rate_limiting(self, client):
        """Test that rate limiting works."""
        # Note: IP is constant 'testclient' in TestClient
        # We need to ensure limits are low enough to trigger or mock limiter
        # But for now, let's just spam
        responses = []
        for _ in range(20):
            response = client.post(
                "/process-email",
                json={"email_text": "limit test"}
            )
            responses.append(response)
            if response.status_code == 429:
                break
        
        # Check if we hit the limit (429)
        assert any(r.status_code == 429 for r in responses)


class TestAuthentication:
    """Tests for API key authentication."""
    
    def test_missing_api_key(self, client):
        """Test that missing API key is rejected."""
        # Override settings for this test
        original_keys = settings.api_keys
        original_env = settings.environment
        
        try:
            settings.api_keys = ["test-key-123"]
            settings.environment = "production" # Enforce auth
            
            response = client.post(
                "/process-email",
                json={"email_text": "test"}
            )
            assert response.status_code == 401
            
        finally:
            settings.api_keys = original_keys
            settings.environment = original_env

    def test_valid_api_key(self, client):
        """Test with valid API key."""
        original_keys = settings.api_keys
        original_env = settings.environment
        
        try:
            settings.api_keys = ["test-key-123"]
            settings.environment = "production"
            
            # We also need to mock graph to avoid errors
            with patch("src.api.graph") as mock_graph:
                mock_graph.ainvoke = AsyncMock(return_value={
                    "category": "spam", 
                    "confidence_score": 0.99,
                    "company_name": "Unknown", 
                    "email_draft": "None"
                })
                
                response = client.post(
                    "/process-email",
                    json={"email_text": "test"},
                    headers={"X-API-Key": "test-key-123"}
                )
                assert response.status_code == 200
                
        finally:
            settings.api_keys = original_keys
            settings.environment = original_env

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
