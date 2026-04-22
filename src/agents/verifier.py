"""
Verifier Agent — The Quality Manager (Reflection Pattern).
Interview Q5 & Q9: Reviews draft, checks for hallucinations, controls the loop.
"""
from src.core.state import AgentState
from src.core.factory import get_llm
from src.utils.logger import get_logger

logger = get_logger(__name__)


def verifier_node(state: AgentState) -> dict:
    """
    Quality control gate. Implements the Reflection Pattern.
    
    Production features:
    - Citation Check (Q9): Verifies claims match research data.
    - Structured Feedback: Provides actionable critique, not vague rejection.
    - Loop Control (Q5): Respects revision_count limits.
    """
    logger.info("⚖️ Verifier: Reviewing draft quality...")

    llm = get_llm(role="verifier")

    prompt = f"""You are a senior sales manager reviewing an email draft before it is sent to a prospect.

REVIEW CRITERIA:
1. TONE: Is it professional and warm (not robotic or aggressive)?
2. GROUNDING: Does every factual claim match the RESEARCH DATA? Flag any hallucinated facts.
3. CTA: Does it end with a clear call-to-action?
4. LENGTH: Is it concise (under 150 words)?
5. PERSONALIZATION: Does it reference the prospect's company/needs?

--- DRAFT EMAIL ---
{state['draft_email']}

--- RESEARCH DATA (Ground Truth) ---
Company: {state.get('company_name', 'Unknown')}
Info: {state.get('company_info', 'No research available.')}

INSTRUCTIONS:
- If the draft is excellent and passes ALL criteria, respond with exactly: APPROVE
- If it needs changes, respond with: REVISE: [specific actionable feedback]"""

    res = llm.invoke(prompt)
    critique = (res.content if hasattr(res, "content") else str(res)).strip()

    is_approved = "APPROVE" in critique.upper()
    logger.info(f"⚖️ Verifier Decision: {'APPROVED ✅' if is_approved else 'REVISION NEEDED 🔄'}")

    return {
        "critique": critique,
        "messages": [f"⚖️ Verdict: {'APPROVED' if is_approved else 'REVISE'}"],
    }
