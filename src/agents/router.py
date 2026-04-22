"""
Router Agent — The Traffic Cop.
Interview Q1 & Q6: Classifies inbound email using Structured Output.
"""
from pydantic import BaseModel, Field
from src.core.state import AgentState
from src.core.factory import get_llm
from src.utils.redactor import redactor
from src.utils.logger import get_logger

logger = get_logger(__name__)


# --- Structured Output Schema (Interview Q6) ---
class EmailClassification(BaseModel):
    """Forces the LLM to return valid, parseable JSON."""
    category: str = Field(description="One of: Lead, Complaint, Spam")
    sender_name: str = Field(description="Name of the email sender, or 'Unknown'")
    reasoning: str = Field(description="Brief explanation of why this category was chosen")


def router_node(state: AgentState) -> dict:
    """
    Classifies the inbound email into Lead, Complaint, or Spam.
    Uses Structured Output (Interview Q6) for reliable parsing.
    """
    logger.info("🚦 Router: Classifying email...")

    # PII Redaction before sending to LLM
    safe_email = redactor.redact(state["initial_email"])

    # Use get_llm with the schema directly for robust fallback (factory handles the schema propagation)
    llm = get_llm(role="router", structured_output=EmailClassification)
    
    prompt = f"""You are a mail sorter for a sales team. Classify this email.
    
Rules:
- "Lead": Someone interested in buying a product or service.
- "Complaint": An existing customer reporting an issue.
- "Spam": Marketing, phishing, or irrelevant mail.

Email:
{safe_email}

Return your classification as JSON with keys: category, sender_name, reasoning."""

    try:
        # Attempt structured output (the factory returned a runnable that handles fallbacks)
        result = llm.invoke(prompt)
        
        # Check if result is the expected Pydantic model
        if isinstance(result, EmailClassification):
            category = result.category.capitalize()
            sender = result.sender_name
        else:
            # If factory returned a raw response (e.g. if structured output failed configuration)
            raw = str(result.content if hasattr(result, 'content') else result).lower()
            category = "Lead" if "lead" in raw else "Complaint" if "complaint" in raw else "Spam"
            sender = "Unknown"
            
        logger.info(f"🚦 Router Result: {category} (sender: {sender})")
    except Exception as e:
        # Fallback: if BOTH providers fail completely, do raw parse on a non-structured LLM
        logger.warning(f"Router invocation failed: {e}")
        try:
            raw_llm = get_llm(role="router") 
            raw_response = raw_llm.invoke(prompt)
            raw = raw_response.content.lower()
            category = "Lead" if "lead" in raw else "Complaint" if "complaint" in raw else "Spam"
            sender = "Unknown"
            logger.info(f"🚦 Router Fallback Result: {category}")
        except Exception as fallback_err:
            logger.error(f"Critical failure in Router fallback: {fallback_err}")
            category = "Lead" 
            sender = "Unknown"

    return {
        "category": category,
        "sender_name": sender,
        "revision_count": 0,
        "messages": [f"📧 Email classified as: {category}"],
    }
