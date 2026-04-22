"""
Support Agent — Handles customer complaints on a separate path.
"""
from src.core.state import AgentState
from src.core.factory import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


def support_node(state: AgentState) -> dict:
    """
    Generates an empathetic support response for customer complaints.
    This runs on the 'complaint' branch and goes directly to END.
    """
    logger.info("🛡️ Support: Drafting complaint response...")

    llm = get_llm(role="writer")

    prompt = f"""You are a customer success manager. A customer has submitted a complaint.

Write an empathetic, professional response that:
1. Acknowledges their frustration
2. Takes ownership of the issue
3. Proposes a concrete next step or resolution
4. Keeps it under 100 words

Complaint:
{state['initial_email']}"""

    draft = llm.invoke(prompt).content

    return {
        "draft_email": draft,
        "messages": ["🛡️ Support response drafted"],
    }
