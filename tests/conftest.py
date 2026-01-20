"""
Pytest configuration and fixtures for testing.
"""
import pytest
import asyncio
from typing import Generator
from unittest.mock import Mock, MagicMock
import redis

from src.config import settings
from src.state import AgentState


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = MagicMock(spec=redis.Redis)
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    return mock


@pytest.fixture
def mock_llm_response():
    """Mock LLM response."""
    mock = Mock()
    mock.content = "This is a test response"
    return mock


@pytest.fixture
def sample_lead_email():
    """Sample sales lead email for testing."""
    return """
    Hi, I am John Doe from Acme Corp.
    We want to buy your enterprise license.
    Call me at 555-123-4567 or email john@acme.com.
    """


@pytest.fixture
def sample_spam_email():
    """Sample spam email for testing."""
    return "Click here for free iPhone! You won $1000!"


@pytest.fixture
def sample_complaint_email():
    """Sample complaint email for testing."""
    return "My service is down and I need help immediately. User ID: 12345"


@pytest.fixture
def sample_state() -> AgentState:
    """Sample agent state for testing."""
    return {
        "input_text": "Test email content",
        "trace_id": "test-trace-123",
        "category": "lead",
        "revision_count": 0,
        "final_status": "approved",
        "company_name": "Test Corp",
        "company_info": "Test company information",
        "email_draft": "Test draft",
        "feedback": "",
        "messages": []
    }


@pytest.fixture
def test_config():
    """Test configuration overrides."""
    # Store original values
    original_env = settings.environment
    original_log_level = settings.log_level
    
    # Set test values
    settings.environment = "development"
    settings.log_level = "DEBUG"
    
    yield settings
    
    # Restore original values
    settings.environment = original_env
    settings.log_level = original_log_level
