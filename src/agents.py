import os
import re
from dotenv import load_dotenv, find_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from transformers import pipeline

# 👇 Custom Modules
from src.state import AgentState
from src.security import PIIManager 

# --- 1. SETUP ---
load_dotenv(find_dotenv())

# Check for API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY is missing.")

# Tool Imports
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults

# ✅ Initialize Security Vault (Global)
print("🔒 Initializing PII Security Vault...")
pii_manager = PIIManager() 

# ✅ Load Local Classifier (CPU)
print("⏳ Loading lightweight classification model (~260MB)...")
classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-1")

# ✅ Initialize LLM with Auto-Retry (Resilience)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0,
    google_api_key=api_key,
    max_retries=3,       # <--- Retry 3 times if server disconnects
    request_timeout=60   # <--- Wait 60s before failing
)

search_tool = TavilySearchResults(max_results=3)


# --- 2. AGENT NODES ---

def router_node(state: AgentState):
    """
    The Hybrid Triage Agent.
    Step 1: Sanitize Data (PII Redaction)
    Step 2: Rule-Based Guardrails (Spam Keywords)
    Step 3: AI Classification (MapReduce Strategy)
    """
    tid = state.get("trace_id", "N/A")
    raw_text = state['input_text']
    
    # 🔒 1. PII REDACTION LAYER
    clean_text = pii_manager.anonymize(raw_text)
    state['input_text'] = clean_text 
    
    print(f"🕵️ [Trace: {tid}] Router: Analyzing Clean Text...")

    # 🛑 2. RULE-BASED SPAM FILTER (Hybrid Architecture)
    # Fast check for obvious scams before wasting compute on AI
    spam_keywords = ["click here", "free iphone", "winner", "$1000", "lottery", "prize", "casino"]
    if any(keyword in clean_text.lower() for keyword in spam_keywords):
        print("   ↳ 🚨 SPAM DETECTED via Keywords. Skipping AI model.")
        return {"category": "spam"}

    # 🤖 3. MAPREDUCE AI CLASSIFICATION
    labels = ["sales lead", "customer complaint", "spam or junk"]
    
    # Chunking Strategy for Long Emails
    words = clean_text.split()
    chunk_size = 600
    overlap = 100
    chunks = []
    
    if len(words) <= chunk_size:
        chunks.append(clean_text)
    else:
        for i in range(0, len(words), chunk_size - overlap):
            chunks.append(" ".join(words[i : i + chunk_size]))

    # Run Classifier on Chunks
    results = []
    for chunk in chunks:
        res = classifier(chunk, labels)
        results.append((res['scores'][0], res['labels'][0]))

    # Max Pooling (Best Score Wins)
    results.sort(key=lambda x: x[0], reverse=True)
    best_score, best_label = results[0]
    
    print(f"   ↳ AI Decision: {best_label.upper()} (Confidence: {best_score:.2f})")

    # Routing
    if "lead" in best_label:
        return {"category": "lead"}
    elif "complaint" in best_label:
        return {"category": "complaint"}
    else:
        return {"category": "spam"}


def researcher_node(state: AgentState):
    """
    Extracts company name and searches for news.
    """
    tid = state.get("trace_id", "N/A")
    print(f"🔎 [Trace: {tid}] Researcher: Searching Tavily...")
    
    try:
        company_name = llm.invoke(f"Extract company name from: {state['input_text']}").content.strip()
        search_results = search_tool.invoke(f"{company_name} news")
        summary = "\n".join([res['content'] for res in search_results])
    except:
        company_name = "Unknown Company"
        summary = "No specific news found."
        
    return {"company_name": company_name, "company_info": summary}


def writer_node(state: AgentState):
    """
    Drafts the email using tokens.
    Includes 'Smarter' Guardrails for 'Free' vs 'Feel Free'.
    """
    tid = state.get("trace_id", "N/A")
    print(f"✍️ [Trace: {tid}] Writer: Drafting email...")
    
    prompt = f"""
    You are a Sales AI. Write a professional email to {state['company_name']} based on:
    "{state['input_text']}"
    
    RESEARCH TO USE:
    {state['company_info']}
    
    RULES:
    1. Do NOT offer any discounts, prices, or free gifts.
    2. Use "Feel welcome to contact" instead of "Feel free".
    3. IMPORTANT: If the input has tokens like [PHONE_...] or [EMAIL_...], KEEP THEM EXACTLY. Do not invent data.
    """
    response = llm.invoke(prompt)
    email_draft = response.content

    # 🛡️ SMARTER GUARDRAIL (Regex)
    # Blocks "Free iPhone" but allows "Feel free" (if prompt failed)
    financial_risks = [
        r"\$\d+",          # Prices (e.g., $100)
        r"\d{1,2}% off",   # Discounts (e.g., 50% off)
        r"free (trial|gift|month|access|iphone)", # Risky freebies
        r"discount"        # The word discount
    ]
    
    triggered = False
    for pattern in financial_risks:
        if re.search(pattern, email_draft, re.IGNORECASE):
            triggered = True
            print(f"🚨 [Trace: {tid}] BLOCKED pattern: {pattern}")
            break
            
    if triggered:
        email_draft = "[SYSTEM BLOCK] Unsafe financial content removed."
    
    return {"email_draft": email_draft, "revision_count": state.get("revision_count", 0) + 1}


def verifier_node(state: AgentState):
    """
    Reviews the draft. 
    Instructed to accept PII Tokens as valid data.
    """
    tid = state.get("trace_id", "N/A")
    print(f"⚖️ [Trace: {tid}] Verifier: Checking Anonymized Draft...")
    
    prompt = f"""
    You are a Senior Editor. Review this sales email draft:
    
    "{state['email_draft']}"
    
    CRITERIA:
    1. Is it professional?
    2. Does it address the customer's intent?
    
    IMPORTANT RULES:
    - The email contains SECURITY TOKENS like [PHONE_...], [EMAIL_...], or [NAME_...].
    - Treat these tokens as VALID, REAL information. 
    - Do NOT reject the email because it contains these placeholders.
    
    If it is good, return "APPROVE".
    If it is bad, return "REJECT" with a reason.
    """
    
    response = llm.invoke(prompt)
    feedback = response.content.strip()
    
    if "APPROVE" in feedback:
        return {"final_status": "approved", "feedback": feedback}
    else:
        print(f"❌ [Trace: {tid}] Verifier Rejected: {feedback}")
        return {"final_status": "rejected", "feedback": feedback}


def support_node(state: AgentState):
    """
    Handles complaints. Also uses tokens.
    """
    tid = state.get("trace_id", "N/A")
    print(f"🚑 [Trace: {tid}] Support: Drafting Apology...")
    
    prompt = f"""
    Write a polite apology to this customer: "{state['input_text']}"
    Keep placeholders like [PHONE_...] or [ID_...] intact.
    """
    response = llm.invoke(prompt)
    email_draft = response.content

    # Basic Guardrail
    if re.search(r"(\$\d|\d%|free)", email_draft, re.IGNORECASE):
        email_draft = "[SYSTEM BLOCK] Unsafe content."

    return {"email_draft": email_draft, "final_status": "escalated"}


def final_delivery_node(state: AgentState):
    """
    The Exit Node: Swaps [TOKEN] back to Real Data (De-anonymization).
    """
    tid = state.get("trace_id", "N/A")
    print(f"🔓 [Trace: {tid}] Final Delivery: Restoring PII Data...")
    
    safe_draft = state['email_draft']
    
    # 1. DE-ANONYMIZE
    real_email = pii_manager.deanonymize(safe_draft)
    
    print("\n✅ --- FINAL EMAIL READY FOR SENDING ---")
    print(real_email)
    print("---------------------------------------\n")
    
    return {"email_draft": real_email}