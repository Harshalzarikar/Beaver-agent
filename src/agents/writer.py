"""
Writer Agent — The Creator.
Interview Q9 & Q10: Uses ONLY grounded facts + incorporates critique history.
"""
from src.core.state import AgentState
from src.core.factory import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


def writer_node(state: AgentState) -> dict:
    """
    Drafts a personalized sales response.
    
    Production features:
    - Grounding (Q9): Only uses facts from `company_info`, never hallucinated data.
    - Critique History (Q10): Reads previous `critique` to avoid repeating mistakes.
    """
    revision = state.get("revision_count", 0)
    logger.info(f"✍️ Writer: Drafting (revision #{revision})...")

    llm = get_llm(role="writer")

    # Build context from previous critique (Interview Q10: Scenario A fix)
    critique_context = state.get("critique", "")
    if critique_context and critique_context != "":
        feedback_section = f"""
IMPORTANT — Previous Review Feedback (you MUST address this):
{critique_context}
"""
    else:
        feedback_section = ""

    prompt = f"""You are a professional sales representative writing a reply to an inbound lead.

RULES (STRICT):
1. ONLY use facts from the RESEARCH DATA below. Do NOT invent company details.
2. If a fact is missing, say "I'd love to learn more about your needs."
3. Keep the email under 150 words.
4. Be professional, warm, and action-oriented.
5. End with a clear call-to-action (e.g., schedule a call).

--- ORIGINAL EMAIL ---
{state['initial_email']}

--- RESEARCH DATA (Grounded Source) ---
Company: {state.get('company_name', 'Unknown')}
Info: {state.get('company_info', 'No research available.')}

{feedback_section}

Write the reply email now:"""

    res = llm.invoke(prompt)
    draft = res.content if hasattr(res, "content") else str(res)

    return {
        "draft_email": draft,
        "revision_count": revision + 1,
        "messages": [f"✍️ Draft v{revision + 1} created"],
    }
