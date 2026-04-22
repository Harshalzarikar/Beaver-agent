"""
Research Agent — The Intelligence Gatherer.
Interview Q9: Provides GROUNDED facts for the Writer to use.
"""
from src.core.state import AgentState
from src.core.factory import get_llm, get_search_tool
from src.utils.logger import get_logger

logger = get_logger(__name__)


def researcher_node(state: AgentState) -> dict:
    """
    Extracts company name and fetches real-time data via Tavily.
    This data becomes the 'grounding source' for the Writer (Interview Q9).
    """
    logger.info("🔍 Researcher: Gathering intelligence...")

    search = get_search_tool()
    if not search:
        return {
            "company_name": "Unknown",
            "company_info": "No research data available (Tavily API key not set).",
            "messages": ["⚠️ Research skipped: no search API key"],
        }

    llm = get_llm(role="researcher")

    # Step 1: Extract company name from the email
    extract_prompt = f"""Extract the company or organization name from this email. 
Return ONLY the company name, nothing else. If none found, return 'Unknown'.

Email: {state['initial_email']}"""

    res = llm.invoke(extract_prompt)
    company = (res.content if hasattr(res, "content") else str(res)).strip()
    logger.info(f"🔍 Company extracted: {company}")

    # Step 2: Search for grounded facts
    try:
        results = search.invoke(f"{company} company overview products industry")
        # Handle both string and list returns from Tavily
        if isinstance(results, str):
            info = results
        elif results and isinstance(results, list):
            info = "\n".join(
                r.get("content", str(r)) if isinstance(r, dict) else str(r)
                for r in results
            )
        else:
            info = "No search results found."
    except Exception as e:
        logger.error(f"Research failed: {e}")
        info = f"Research failed: {e}"

    return {
        "company_name": company,
        "company_info": info,
        "messages": [f"🔍 Researched: {company}"],
    }
