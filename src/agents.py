import os
import re
import sys
from functools import lru_cache
from dotenv import load_dotenv, find_dotenv

# LLM Providers
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

# Tools & Pipelines
# from transformers import pipeline # Removed unused dependency
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

    # 3. DIRECT LLM CLASSIFICATION (Robust for Cloud)
    # Skipped local zero-shot classifier to prevent OOM/Timeouts
    
    # Tier 2: LLM Classification with Few-Shot Examples + Chain-of-Thought
    llm = get_llm()
    classify_prompt = f"""You are an expert email classifier. Classify the email into exactly ONE category.

CATEGORIES:
- 'lead': Customer wants to buy, inquire about product/service, request demo, or explore partnership.
- 'complaint': Customer is unhappy, reporting issue, requesting refund, or wants to unsubscribe.
- 'spam': Irrelevant message, phishing attempt, advertisement, or nonsensical content.

EXAMPLES:

Example 1:
Email: "Hi, I saw your product on LinkedIn. We're a 50-person startup looking for enterprise solutions. Can we schedule a demo next week? - Sarah, CTO at TechFlow"
Reasoning: The sender identifies themselves, mentions their company size, and explicitly requests a demo. This is a clear sales inquiry.
Category: lead

Example 2:
Email: "I've been waiting 2 weeks for my order #12345 and it still hasn't arrived. This is unacceptable. I want a refund immediately."
Reasoning: The sender is frustrated, mentions a specific order issue, and demands a refund. This is clearly a complaint.
Category: complaint

Example 3:
Email: "Congratulations! You've been selected to receive a FREE iPhone 15! Click here to claim your prize: bit.ly/free-prize"
Reasoning: This uses urgency tactics, offers something "free", and has a suspicious link. Classic spam/phishing.
Category: spam

Example 4:
Email: "Please remove me from your mailing list. I no longer wish to receive these emails."
Reasoning: The sender wants to unsubscribe, which indicates dissatisfaction with current communication.
Category: complaint

NOW CLASSIFY THIS EMAIL:
Email: "{clean_text[:3000]}"

Think step-by-step:
1. What is the sender's intent?
2. Are they asking about products/services (lead), expressing dissatisfaction (complaint), or is this irrelevant/suspicious (spam)?
3. What specific words or phrases indicate the category?

Reasoning: [Your analysis]
Category: [lead/complaint/spam]"""
    
    try:
        response = llm.invoke(classify_prompt)
        content = response.content.strip().lower()
        
        # Extract category from response
        if "category: lead" in content or content.endswith("lead"):
            category = "lead"
        elif "category: complaint" in content or content.endswith("complaint"):
            category = "complaint"
        elif "category: spam" in content or content.endswith("spam"):
            category = "spam"
        else:
            # Fallback extraction
            if "lead" in content.split()[-5:]:
                category = "lead"
            elif "complaint" in content.split()[-5:]:
                category = "complaint"
            else:
                category = "spam"
        
        logger.info("LLM Classification result", extra={
            "trace_id": tid, 
            "category": category,
            "model": settings.model_provider
        })
        
        return {"category": category, "confidence_score": 0.95}  # High confidence for LLM with CoT
        
    except Exception as e:
        logger.error("Classification failed", extra={"error": str(e)})
        return {"category": "spam", "confidence_score": 0.0}  # Fail safe


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
    """The Detective: Finds company info with enhanced extraction."""
    tid = state.get("trace_id", "N/A")
    
    if TEST_MODE:
        return {"company_name": "Test Corp", "company_info": "Simulated Research Data"}

    logger.info("Researching sender", extra={"trace_id": tid})
    
    llm = get_llm()
    search_tool = get_search_tool()
    
    company_name = "Unknown"
    summary = "No public information found."
    
    # Common email providers to ignore
    COMMON_PROVIDERS = {
        "gmail", "yahoo", "hotmail", "outlook", "aol", "icloud", 
        "protonmail", "mail", "live", "msn", "ymail", "googlemail"
    }

    try:
        input_text = state['input_text']
        
        # 1. Multi-Pattern Extraction (Prioritized)
        extraction_methods = []
        
        # Method A: Email domain extraction
        email_match = re.search(r"@([\w.-]+)\.(com|org|net|io|co|ai|tech|biz)", input_text, re.IGNORECASE)
        if email_match:
            domain = email_match.group(1).lower()
            if domain not in COMMON_PROVIDERS:
                extraction_methods.append(("email_domain", domain.capitalize()))
        
        # Method B: Signature block patterns (e.g., "- John, CEO at TechCorp")
        sig_patterns = [
            r"(?:at|from|@)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?(?:\s+(?:Inc|LLC|Corp|Ltd|Co))?)",
            r"([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s+(?:Inc|LLC|Corp|Ltd|Co\.?)\b",
            r"(?:Best|Regards|Sincerely),?\s*\n.*?\n([A-Z][A-Za-z0-9\s]+?)(?:\n|$)"
        ]
        for pattern in sig_patterns:
            match = re.search(pattern, input_text)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 2 and extracted.lower() not in COMMON_PROVIDERS:
                    extraction_methods.append(("signature", extracted))
                    break
        
        # 2. Use best extraction or fallback to LLM
        if extraction_methods:
            # Prefer signature over email domain
            for method, name in extraction_methods:
                if method == "signature":
                    company_name = name
                    break
            if company_name == "Unknown":
                company_name = extraction_methods[0][1]
            logger.info(f"Extracted company via regex: {company_name}", extra={"trace_id": tid})
        else:
            # LLM Extraction with better prompt
            try:
                extract_prompt = f"""Extract the company or organization name from this email.

RULES:
1. Look for company names in signatures, email domains, or explicit mentions.
2. Ignore common email providers (Gmail, Yahoo, etc.).
3. Return ONLY the company name, nothing else.
4. If no company found, return exactly: Unknown

Email:
{input_text[:2000]}

Company Name:"""
                response = llm.invoke(extract_prompt)
                extracted = response.content.strip()
                
                # Validate extraction
                if extracted and len(extracted) < 50 and extracted.lower() != "unknown":
                    if extracted.lower() not in COMMON_PROVIDERS:
                        company_name = extracted
                        logger.info(f"Extracted company via LLM: {company_name}", extra={"trace_id": tid})
                        
            except Exception as e:
                logger.warning("Company extraction LLM failed", extra={"error": str(e)})
            
        # 3. Web Search for company info
        if company_name and company_name != "Unknown":
            logger.info(f"Searching for company: {company_name}", extra={"trace_id": tid})
            try:
                search_results = search_tool.invoke(f"{company_name} company business")
                if search_results:
                    summary = "\n".join([res.get('content', '')[:500] for res in search_results[:2]])
            except Exception as e:
                logger.warning("Search failed", extra={"error": str(e)})
        
    except Exception as e:
        logger.error("Research failed", extra={"trace_id": tid, "error": str(e)})

    return {"company_name": company_name, "company_info": summary}


def writer_node(state: AgentState):
    """The Author: Writes professional, tailored email responses."""
    tid = state.get("trace_id", "N/A")
    
    if TEST_MODE:
        return {"email_draft": "Simulated Draft.", "revision_count": 1}

    logger.info("Drafting email response", extra={"trace_id": tid})
    
    llm = get_llm()
    sender = settings.get_sender_config()
    
    prompt = f"""You are a professional sales representative at {sender['company_name']}.
Write a tailored email response to the inquiry from {state.get('company_name', 'the customer')}.

INCOMING EMAIL:
{state['input_text'][:2000]}

RESEARCH ON SENDER:
{state.get('company_info', 'No information available.')[:1000]}

EXAMPLES OF GOOD RESPONSES:

Example 1 (Product Inquiry):
"Dear Sarah,

Thank you for reaching out about our enterprise solutions! Given TechFlow's growth trajectory, I'd recommend our Pro tier which scales seamlessly from 50 to 500 users.

I'd love to schedule a 20-minute demo to show you how companies similar to yours have reduced onboarding time by 40%. Would Thursday at 2 PM work for your team?

Best regards,
[Signature]"

Example 2 (Partnership Request):
"Dear Michael,

I appreciate your interest in exploring a partnership with us. After reviewing DataSync Inc's impressive work in data integration, I believe there's strong potential for collaboration.

Let's set up a call to discuss synergies. Please let me know your availability next week.

Best regards,
[Signature]"

YOUR TASK:
1. DIRECTLY address the sender's specific question or request
2. Reference their company or situation specifically (use the research)
3. Propose a clear next step (meeting, demo, call, etc.)
4. Keep the response between 100-200 words
5. Maintain a professional but warm tone
6. Preserve any [PLACEHOLDER] tokens exactly as they appear

IMPORTANT: Do NOT offer discounts, free trials, or make promises you can't keep.

Sign off with:
Best regards,
{sender['name']}
{sender['title']}
{sender['company_name']}

Write the email now:"""
    
    response = llm.invoke(prompt)
    email_draft = response.content
    
    # Guardrails - Block risky content
    risky_patterns = [r"\$\d+", r"free (iphone|money|trial)", r"click here", r"guaranteed"]
    for pattern in risky_patterns:
        if re.search(pattern, email_draft, re.IGNORECASE):
            logger.warning("Blocked risky content", extra={"trace_id": tid, "pattern": pattern})
            email_draft = "[SYSTEM BLOCK] Unsafe content removed. Please review manually."
            break

    return {
        "email_draft": email_draft,
        "revision_count": state.get("revision_count", 0) + 1
    }


def verifier_node(state: AgentState):
    """The Manager: Quality verification with structured criteria."""
    tid = state.get("trace_id", "N/A")
    logger.info("Verifying draft quality", extra={"trace_id": tid})
    
    llm = get_llm()
    prompt = f"""You are a quality assurance manager reviewing an email draft before sending.

DRAFT TO REVIEW:
{state.get('email_draft', '')[:2000]}

ORIGINAL INQUIRY:
{state.get('input_text', '')[:500]}

EVALUATION CRITERIA:
1. PROFESSIONAL TONE: Is the language appropriate and courteous?
2. ADDRESSES REQUEST: Does it directly answer the sender's question/need?
3. CLEAR NEXT STEP: Is there a concrete call-to-action?
4. NO RISKY CONTENT: No unauthorized discounts, suspicious links, or false promises?
5. PROPER FORMATTING: Has greeting, body, and signature?

Score each criterion 1-5 (1=poor, 5=excellent).

DECISION RULES:
- APPROVE if average score >= 3.5 AND no score below 2
- REJECT if any score is 1 OR average score < 3

Your response format:
SCORES:
- Professional Tone: X/5
- Addresses Request: X/5
- Clear Next Step: X/5
- No Risky Content: X/5
- Proper Formatting: X/5

VERDICT: [APPROVE/REJECT]
REASON: [Brief explanation]"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content.upper()
        
        if "APPROVE" in content:
            final_status = "approved"
        else:
            final_status = "rejected"
            
        logger.info(f"Verification result: {final_status}", extra={"trace_id": tid})
        
    except Exception as e:
        logger.error("Verification failed", extra={"error": str(e)})
        final_status = "rejected"  # Default to reject on error
        
    return {"final_status": final_status}


def support_node(state: AgentState):
    """The Support Agent: Professional complaint handling."""
    tid = state.get("trace_id", "N/A")
    logger.info("Drafting support response", extra={"trace_id": tid})
    
    llm = get_llm()
    sender = settings.get_sender_config()
    
    prompt = f"""You are a customer support specialist at {sender['company_name']}.
Write a professional and empathetic response to this customer complaint:

COMPLAINT:
{state.get('input_text', '')[:2000]}

GUIDELINES:
1. Acknowledge their frustration with empathy
2. Apologize sincerely without being defensive
3. If applicable, explain what went wrong (briefly)
4. Propose a concrete solution or next step
5. Preserve any [PLACEHOLDER] tokens exactly as they appear
6. Keep response between 100-150 words

EXAMPLE RESPONSE:
"Dear [Customer],

I sincerely apologize for the frustration you've experienced with your order. This is not the level of service we strive to provide.

I've escalated your case to our fulfillment team for immediate attention. You can expect an update within 24 hours, and we'll do everything possible to resolve this quickly.

Thank you for bringing this to our attention.

Best regards,
[Support Rep]"

Sign off with:
Best regards,
{sender['name']}
Customer Support Team
{sender['company_name']}

Write the response now:"""
    
    response = llm.invoke(prompt)
    
    return {"email_draft": response.content, "final_status": "escalated"}


def final_delivery_node(state: AgentState):
    """The Vault: Restores PII."""
    tid = state.get("trace_id", "N/A")
    logger.info("Restoring PII data", extra={"trace_id": tid})
    restored_draft = pii_manager.deanonymize(state['email_draft'], trace_id=tid)
    return {"email_draft": restored_draft}