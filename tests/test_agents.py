"""
Unit tests for agent nodes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.agents import router_node, writer_node, verifier_node, support_node
from src.state import AgentState


class TestRouterNode:
    """Tests for router_node."""
    
    def test_spam_detection_with_obvious_spam(self, sample_spam_email, sample_state):
        """Test that obvious spam is detected."""
        state = sample_state.copy()
        state["input_text"] = sample_spam_email
        
        with patch("src.agents.pii_manager") as mock_pii:
            mock_pii.anonymize.return_value = sample_spam_email
            
            result = router_node(state)
            
            assert result["category"] == "spam"
    
    @patch("src.agents.get_classifier")
    def test_lead_classification(self, mock_get_classifier, sample_lead_email, sample_state):
        """Test that sales leads are classified correctly."""
        state = sample_state.copy()
        state["input_text"] = sample_lead_email
        
        # Mock classifier response
        mock_pipeline = Mock()
        mock_pipeline.return_value = {
            "labels": ["sales lead", "customer complaint", "spam or junk"],
            "scores": [0.95, 0.03, 0.02]
        }
        mock_get_classifier.return_value = mock_pipeline
        
        with patch("src.agents.pii_manager") as mock_pii:
            mock_pii.anonymize.return_value = sample_lead_email
            
            result = router_node(state)
            
            assert result["category"] == "lead"
    
    @patch("src.agents.get_classifier")
    def test_complaint_classification(self, mock_get_classifier, sample_complaint_email, sample_state):
        """Test that complaints are classified correctly."""
        state = sample_state.copy()
        state["input_text"] = sample_complaint_email
        
        # Mock classifier response
        mock_pipeline = Mock()
        mock_pipeline.return_value = {
            "labels": ["customer complaint", "sales lead", "spam or junk"],
            "scores": [0.92, 0.05, 0.03]
        }
        mock_get_classifier.return_value = mock_pipeline
        
        with patch("src.agents.pii_manager") as mock_pii:
            mock_pii.anonymize.return_value = sample_complaint_email
            
            result = router_node(state)
            
            assert result["category"] == "complaint"


class TestWriterNode:
    """Tests for writer_node."""
    
    @patch("src.agents.get_llm")
    def test_writer_generates_draft(self, mock_get_llm, sample_state):
        """Test that writer node generates an email draft."""
        state = sample_state.copy()
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "Dear Test Corp,\n\nThank you for your interest.\n\nBest regards"
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = writer_node(state)
        
        assert "email_draft" in result
        assert len(result["email_draft"]) > 0
        assert result["revision_count"] == 1
    
    @patch("src.agents.get_llm")
    def test_writer_blocks_risky_content(self, mock_get_llm, sample_state):
        """Test that writer blocks risky patterns."""
        state = sample_state.copy()
        
        # Mock LLM response with risky content
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "We offer $500 discount! Click here now!"
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = writer_node(state)
        
        assert "[SYSTEM BLOCK]" in result["email_draft"]


class TestVerifierNode:
    """Tests for verifier_node."""
    
    @patch("src.agents.get_llm")
    def test_verifier_approves_good_draft(self, mock_get_llm, sample_state):
        """Test that verifier approves good drafts."""
        state = sample_state.copy()
        state["email_draft"] = "Professional email content"
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "APPROVE - This email is professional"
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = verifier_node(state)
        
        assert result["final_status"] == "approved"
    
    @patch("src.agents.get_llm")
    def test_verifier_rejects_bad_draft(self, mock_get_llm, sample_state):
        """Test that verifier rejects bad drafts."""
        state = sample_state.copy()
        state["email_draft"] = "Unprofessional content"
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "REJECT - This email needs improvement"
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = verifier_node(state)
        
        assert result["final_status"] == "rejected"


class TestSupportNode:
    """Tests for support_node."""
    
    @patch("src.agents.get_llm")
    def test_support_generates_apology(self, mock_get_llm, sample_complaint_email, sample_state):
        """Test that support node generates apology."""
        state = sample_state.copy()
        state["input_text"] = sample_complaint_email
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_response = Mock()
        mock_response.content = "We apologize for the inconvenience..."
        mock_llm_instance.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm_instance
        
        result = support_node(state)
        
        assert "email_draft" in result
        assert result["final_status"] == "escalated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
