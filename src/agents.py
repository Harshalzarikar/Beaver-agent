import os
import re
import sys
from functools import lru_cache
from dotenv import load_dotenv, find_dotenv

# LLM Providers
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Tools & Pipelines
from transformers import pipeline
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.chains.summarize import load_summarize_chain

# Handle Tavily Import
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults

# Internal Imports
from src.state import AgentState
from src.security import pii_manager
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)

# --- 1. CONFIGURATION & SETUP ---
load_dotenv(find_dotenv())

# ⚡ TEST CONFIG
TEST_MODE = False 

# --- 2. DYNAMIC RESOURCE INITIALIZATION ---
@lru_cache(maxsize=1)
def get_classifier():
    """Lazy load classifier."""
    logger.info("Loading Classifier...")
    try:
        # Try local folder first
        return pipeline("zero-shot-classification", model="./my_local_model")
    except:
        # Fallback to download
        logger.info("Downloading Classifier (One-time)...")
        return pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")



@lru_cache(maxsize=1)
def get_llm():
    """Factory function to initialize the selected LLM."""
    provider = settings.model_provider
    
    if provider == "groq":
        if not settings.groq_api_key:
            logger.error("GROQ_API_KEY is missing")
            raise ValueError("GROQ_API_KEY is required")
            
        logger.info("Connecting to Groq LPU...")
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=settings.model_temperature,
            max_retries=settings.model_max_retries
        )
        
    elif provider == "gemini":
        if not settings.google_api_key:
            logger.error("GOOGLE_API_KEY is missing")
            raise ValueError("GOOGLE_API_KEY is required")
            
        logger.info("Connecting to Google Gemini...")
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=settings.model_temperature,
            max_retries=settings.model_max_retries
        )
    
    raise ValueError(f"Unknown provider: {provider}")

@lru_cache(maxsize=1)
def get_search_tool():
    """Lazy load search tool."""
    return TavilySearchResults(
        max_results=3,
        tavily_api_key=settings.tavily_api_key
    )

# --- 3. AGENT NODES ---

def router_node(state: AgentState):
    """Traffic Controller: PII Redaction -> Regex Spam -> AI Classify"""
    tid = state.get("trace_id", "N/A")
    raw_text = state['input_text']
    
    # 1. PII REDACTION
    clean_text = pii_manager.anonymize(raw_text, trace_id=tid)
    state['input_text'] = clean_text 
    
    logger.info("Router analyzing text", extra={"trace_id": tid})

    # 2. HYBRID SPAM FILTER
    spam_patterns = [
        r"(click here|free iphone|lottery|winner|\$\$\$)",
        r"(?!.*(unsubscribe|privacy policy))\b(buy now|limited time offer)\b",
        r"(congratulations.*you have won)"
    ]
    for pattern in spam_patterns:
        if re.search(pattern, clean_text, re.IGNORECASE):
            logger.info("Spam detected pattern", extra={"trace_id": tid, "pattern": pattern})
            return {"category": "spam", "confidence_score": 1.0}

    # 3. HYBRID CLASSIFICATION (Cost Optimized)
    # Tier 1: Zero-Shot Classifier (Fast & Cheap)
    classifier = get_classifier()
    labels = ["sales lead", "customer complaint", "spam or junk"]
    short_text = clean_text[:2000]
    
    try:
        result = classifier(short_text, labels)
        top_label = result['labels'][0]
        score = result['scores'][0]
        
        logger.info("Zero-Shot result", extra={"trace_id": tid, "label": top_label, "score": score})
        
        # If high confidence, return immediately (Save LLM cost)
        if score > 0.70:
            logger.info("High confidence, skipping LLM", extra={"trace_id": tid})
            if "lead" in top_label: return {"category": "lead", "confidence_score": float(score)}
            elif "complaint" in top_label: return {"category": "complaint", "confidence_score": float(score)}
            else: return {"category": "spam", "confidence_score": float(score)}
            
        logger.info("Low confidence, falling back to LLM", extra={"trace_id": tid, "score": score})
        
    except Exception as e:
        logger.warning("Zero-shot classifier failed", extra={"error": str(e)})

    # Tier 2: LLM Classification (Slower but more accurate)
    llm = get_llm()
    classify_prompt = f"""
    Classify this email into exactly one category: 'lead', 'complaint', or 'spam'.
    
    RULES:
    - 'lead': Wants to buy, inquire about product, or partnership.
    - 'complaint': Unhappy, reporting bug, refund, or unsubscribe.
    - 'spam': Irrelevant, phishing, ads, or nonsense.
    
    Return ONLY the category name.
    
    TEXT: "{clean_text[:5000]}"
    """
    
    try:
        response = llm.invoke(classify_prompt)
        category = response.content.strip().lower()
        
        # Normalize
        if "lead" in category: category = "lead"
        elif "complaint" in category: category = "complaint"
        else: category = "spam"
        
        logger.info("LLM Classification result", extra={
            "trace_id": tid, 
            "category": category,
            "model": settings.model_provider
        })
        
        return {"category": category, "confidence_score": 0.9} # High confidence for LLM
        
    except Exception as e:
        logger.error("Classification failed", extra={"error": str(e)})
        return {"category": "spam", "confidence_score": 0.0} # Fail safe


def summarizer_node(state: AgentState):
    """The Compressor: Handles huge inputs."""
    tid = state.get("trace_id", "N/A")
    raw_text = state['input_text']
    
    if len(raw_text) < settings.summarizer_threshold:
        return {"input_text": raw_text}

    logger.info("Summarizing long text", extra={"trace_id": tid, "length": len(raw_text)})
    
    llm = get_llm()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    
    if settings.model_provider == "gemini":
        docs = text_splitter.create_documents([raw_text])
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        result = chain.invoke(docs)
        return {"input_text": result['output_text']}
    else:
        texts = text_splitter.split_text(raw_text)
        summaries = []
        for chunk in texts:
            response = llm.invoke(f"Summarize this concisely: {chunk}")
            summaries.append(response.content)
        
        final_text = "\n".join(summaries)
        final_response = llm.invoke(f"Combine these summaries: {final_text}")
        return {"input_text": final_response.content}


def researcher_node(state: AgentState):
    """The Detective: Finds company info."""
    tid = state.get("trace_id", "N/A")
    
    if TEST_MODE:
        return {"company_name": "Test Corp", "company_info": "Simulated Research Data"}

    logger.info("Researching sender", extra={"trace_id": tid})
    
    llm = get_llm()
    search_tool = get_search_tool()
    
    company_name = "Unknown"
    summary = "No public information found."

    try:
        # 1. Regex/Heuristic Extraction (Try first to save LLM quota)
        email_match = re.search(r"@([\w.-]+\.\w+)", state['input_text'])
        if email_match:
            company_name = email_match.group(1).split('.')[0].capitalize()
            # common providers check could go here
        
        # 2. AI Extraction (Fallback)
        if not company_name or "Unknown" in company_name or company_name.lower() in ["gmail", "yahoo", "hotmail"]:
            try:
                extract_prompt = f"Extract the company name from this text. Return ONLY the name or 'Unknown'. Text: {state['input_text']}"
                response = llm.invoke(extract_prompt)
                company_name = response.content.strip()
            except Exception as e:
                logger.warning("Company extraction LLM failed", extra={"error": str(e)})
                if not company_name:
                    company_name = "Unknown"
            
            # 3. Search
            if company_name and company_name != "Unknown":
                logger.info(f"Searching for company: {company_name}", extra={"trace_id": tid})
                search_results = search_tool.invoke(f"{company_name} latest news business")
                summary = "\n".join([res['content'] for res in search_results])
        
    except Exception as e:
        logger.error("Research failed", extra={"trace_id": tid, "error": str(e)})

    return {"company_name": company_name, "company_info": summary}


def writer_node(state: AgentState):
    """The Author: Writes the email."""
    tid = state.get("trace_id", "N/A")
    
    if TEST_MODE:
        return {"email_draft": "Simulated Draft.", "revision_count": 1}

    logger.info("Drafting email response", extra={"trace_id": tid})
    
    llm = get_llm()
    sender = settings.get_sender_config()
    
    prompt = f"""
    You are a sales agent from {sender['company_name']}. 
    Write a professional email to {state['company_name']}.

    CONTEXT:
    - Incoming Email: "{state['input_text']}"
    - Research: "{state['company_info']}"

    RULES:
    1. Be polite and helpful.
    2. Do NOT offer discounts.
    3. Keep [PLACEHOLDERS] intact.
    4. Use this signature:
    
    Best regards,
    {sender['name']}
    {sender['title']}
    {sender['company_name']}
    """
    
    response = llm.invoke(prompt)
    email_draft = response.content
    
    # Guardrails
    risky_patterns = [r"\$\d+", r"free (iphone|money)", r"click here"]
    for pattern in risky_patterns:
        if re.search(pattern, email_draft, re.IGNORECASE):
            logger.warning("Blocked risky content", extra={"trace_id": tid, "pattern": pattern})
            email_draft = "[SYSTEM BLOCK] Unsafe content removed."
            break

    return {
        "email_draft": email_draft,
        "revision_count": state.get("revision_count", 0) + 1
    }


def verifier_node(state: AgentState):
    """The Manager: Approves or Rejects."""
    llm = get_llm()
    prompt = f"Review this email. If good, say APPROVE. If bad, say REJECT. Draft: {state['email_draft']}"
    response = llm.invoke(prompt)
    final_status = "approved" if "APPROVE" in response.content else "rejected"
    return {"final_status": final_status}


def support_node(state: AgentState):
    """The Support Agent: Handles complaints."""
    tid = state.get("trace_id", "N/A")
    logger.info("Drafting support apology", extra={"trace_id": tid})
    
    llm = get_llm()
    prompt = f"Write a polite apology to: {state['input_text']}. Keep tokens like [PHONE_...] intact."
    response = llm.invoke(prompt)
    
    return {"email_draft": response.content, "final_status": "escalated"}


def final_delivery_node(state: AgentState):
    """The Vault: Restores PII."""
    tid = state.get("trace_id", "N/A")
    logger.info("Restoring PII data", extra={"trace_id": tid})
    restored_draft = pii_manager.deanonymize(state['email_draft'], trace_id=tid)
    return {"email_draft": restored_draft}