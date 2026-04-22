"""
Production LLM Factory — Implements Model Routing.
Interview Q8: Different models for different agent roles to optimize cost.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_llm(role: str = "default", structured_output=None):
    """
    Factory that returns a model tuned for the agent's role.
    Supports structured output and automatic fallback.
    """
    model_map = {
        "router":     (settings.router_model, settings.router_temperature),
        "writer":     (settings.writer_model, settings.writer_temperature),
        "verifier":   (settings.verifier_model, settings.verifier_temperature),
        "researcher": (settings.researcher_model, settings.researcher_temperature),
    }

    model_name, temperature = model_map.get(role, (settings.router_model, 0.3))

    logger.info(f"LLM Factory → role={role}, model={model_name}, temp={temperature}")

    # Primary: Google Gemini
    primary_llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.google_api_key,
        temperature=temperature,
        max_retries=1,
    )
    
    if structured_output:
        try:
            primary_llm = primary_llm.with_structured_output(structured_output)
        except Exception as e:
            logger.warning(f"Primary LLM structured output config failed: {e}")

    # Fallback: Groq (Llama 3.3)
    if settings.groq_api_key:
        fallback_llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=settings.groq_api_key,
            temperature=temperature,
        )
        if structured_output:
            try:
                fallback_llm = fallback_llm.with_structured_output(structured_output)
            except Exception as e:
                logger.warning(f"Fallback LLM structured output config failed: {e}")
            
        return primary_llm.with_fallbacks([fallback_llm])

    return primary_llm


def get_search_tool():
    """Returns configured Tavily search tool, or None if key is missing."""
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not configured. Research will be skipped.")
        return None
    return TavilySearchResults(max_results=2, tavily_api_key=settings.tavily_api_key)
