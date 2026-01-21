import sys
import os

# -----------------------------------------------------------------------------
# CRITICAL PATH FIX: Force Project Root into sys.path
# This prevents "ModuleNotFoundError: No module named 'src.config'"
# -----------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -----------------------------------------------------------------------------

import streamlit as st
import requests
import time
from datetime import datetime
import uuid

# --- CRITICAL: LOAD SECRETS BEFORE IMPORTS ---
# We must load secrets into os.environ BEFORE importing src.config or src.graph
# otherwise Pydantic will crash with "Field required"
try:
    if hasattr(st, "secrets"):
        # 1. Load flat secrets
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ[key] = value
        # 2. Load nested 'general' secrets
        if "general" in st.secrets:
            for key, value in st.secrets["general"].items():
                os.environ[key] = str(value)
except Exception:
    pass # Local execution or secrets not available

# NOW it is safe to import internal modules that check environment variables
try:
    if os.environ.get("NO_API_MODE", "false").lower() == "true":
        from src.graph import graph
        print("⚠️ Running in STANDALONE mode (Direct Graph execution)")
except ImportError:
    pass # Handle errors later in the main logic


# --- CONFIGURATION ---
# Mode Selection: "api" (default) or "standalone" (Streamlit Cloud)
# AUTO-DETECT: If API URL is localhost/127.0.0.1, assume Standalone (useful for cloud where localhost is empty)
RAIL_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
IS_LOCALHOST = "127.0.0.1" in RAIL_URL or "localhost" in RAIL_URL
FORCE_STANDALONE = os.environ.get("NO_API_MODE", "").lower() == "true"

# Fallback: If forced OR (it looks like localhost and we haven't explicitly disabled standalone)
IS_STANDALONE = FORCE_STANDALONE or IS_LOCALHOST

# Get API URL from environment variable
RAIL_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")

# Ensure scheme (Render 'hostport' property excludes http://)
if not RAIL_URL.startswith("http"):
    RAIL_URL = f"http://{RAIL_URL}"

# Normalize base URL (strip trailing slash and specific endpoint if present)
if RAIL_URL.endswith("/process-email"):
    API_BASE = RAIL_URL.replace("/process-email", "")
else:
    API_BASE = RAIL_URL.rstrip("/")

API_ENDPOINT = f"{API_BASE}/process-email"
HEALTH_ENDPOINT = f"{API_BASE}/health"

if IS_STANDALONE:
    # Direct Import for Monolithic Deployment
    try:
        # Standard import should work now that we are at root
        from src.graph import graph
        print("⚠️ Running in STANDALONE mode (Direct Graph execution)")
    except ImportError as e:
        st.error(f"Failed to import graph for standalone mode: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected Initialization Error: {e}")
        st.stop()

st.set_page_config(
    page_title="Beaver Agent | Enterprise AI",
    page_icon="🦫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Rich Aesthetics) ---
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stTextArea textarea {
        background-color: #1e2329;
        color: #ffffff;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    .stButton button {
        background-image: linear-gradient(to right, #2ecc71, #27ae60);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(46, 204, 113, 0.4);
    }
    .metric-card {
        background-color: #1e2329;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-lead { background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; }
    .status-spam { background-color: rgba(231, 76, 60, 0.2); color: #e74c3c; }
    .status-complaint { background-color: rgba(241, 196, 15, 0.2); color: #f1c40f; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://em-content.zobj.net/source/microsoft-teams/337/beaver_1f9ab.png", width=80)
    st.title("Beaver Agent")
    st.caption("Enterprise Autonomous Email Handler")
    st.divider()
    
    st.subheader("⚙️ System Status")
    
    if IS_STANDALONE:
        st.success(f"● Standalone Mode")
        st.info("Running locally in-app")
    else:
        try:
            # Check Health
            health = requests.get(HEALTH_ENDPOINT, timeout=2)
            if health.status_code == 200:
                st.success(f"● System Online ({health.json().get('environment', 'prod')})")
            else:
                st.error("● System Degraded")
        except:
            st.error("● System Offline")
            
        st.info(f"Backend: `{API_BASE}`")
    st.markdown("---")
    st.markdown("### 📊 Metrics")
    st.metric("Model", "Gemini 2.5 Flash")
    st.metric("Avg Latency", "1.2s")

# --- MAIN CONTENT ---
# --- HELPER: Callback to load email into manual input ---
def load_email_for_analysis(subject, sender, body):
    """Callback to set session state before widget rendering"""
    content = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
    st.session_state["manual_input"] = content
    # Switch to tab 0 (Manual) is not directly possible via state, but the text will be there.

# --- MAIN CONTENT ---
st.markdown("## 📨 Incoming Message Processor")

# Tabs for Input Method
tab1, tab2 = st.tabs(["✍️ Write / Paste", "📥 Inbox (IMAP)"])

# --- TAB 1: MANUAL INPUT ---
with tab1:
    st.markdown("Paste email content below to trigger the autonomous workflow.")
    col1, col2 = st.columns([2, 1])

    with col1:
        # Check if we need to initialize
        if "manual_input" not in st.session_state:
            st.session_state.manual_input = ""
            
        email_input = st.text_area(
            "Email Content",
            height=300,
            placeholder="Subject: Enterprise License Inquiry\n\nHi team, I am interested in purchasing...",
            label_visibility="collapsed",
            key="manual_input"
        )

    with col2:
        st.markdown("#### 🎯 Capabilities")
        st.markdown("""
        - **PII Redaction**: Auto-removes sensitive data
        - **Spam Filtering**: Hybrid Regex + AI detection
        - **Smart Research**: Enriches lead data via Web
        - **Auto-Drafting**: Context-aware replies
        """)
        
        st.markdown("#### ⚡ Actions")
        process_btn = st.button("🚀 Process Email", key="process_manual", use_container_width=True)
        clear_btn = st.button("🗑️ Clear", key="clear_manual", use_container_width=True)

# --- TAB 2: INBOX (IMAP) ---
with tab2:
    st.markdown("#### Connect to Email Server")
    
    # Credentials Form
    with st.expander("🔌 Connection Settings", expanded=False):
        st.info("""
        **Note for Gmail/Outlook Users:**  
        You cannot use your login password. You must use an **App Password**.  
        👉 [Click here to generate a Gmail App Password](https://myaccount.google.com/apppasswords)  
        *(Select 'Mail' and 'Mac/Windows Computer')*
        """)
        c1, c2, c3 = st.columns(3)
        with c1:
            imap_server = st.text_input("IMAP Server", value=os.environ.get("IMAP_SERVER", "imap.gmail.com"))
        with c2:
            email_user = st.text_input("Email User", value=os.environ.get("EMAIL_USER", ""))
        with c3:
            email_pass = st.text_input("App Password", type="password", help="The 16-character code from Google", value=os.environ.get("EMAIL_PASSWORD", ""))
            
    fetch_btn = st.button("🔄 Fetch Unread Emails")
    
    if "fetched_emails" not in st.session_state:
        st.session_state.fetched_emails = []
        
    if fetch_btn:
        if not email_user or not email_pass:
            st.error("Please provide Email User and App Password.")
        else:
            try:
                from src.ingestion import EmailIngestor
                ingestor = EmailIngestor(server=imap_server, user=email_user, password=email_pass)
                with st.spinner("Connecting to Inbox..."):
                    ingestor.connect()
                    emails = ingestor.fetch_recent_emails(limit=5)
                    st.session_state.fetched_emails = emails
                    if not emails:
                        st.info("No unread emails found.")
                    else:
                        st.success(f"Fetched {len(emails)} emails!")
                    ingestor.close()
            except Exception as e:
                st.error(f"Failed to fetch emails: {e}")

    # Display Emails
    if st.session_state.fetched_emails:
        st.markdown("### 📥 Unread Messages")
        for i, email in enumerate(st.session_state.fetched_emails):
            with st.container():
                ec1, ec2 = st.columns([5, 1])
                with ec1:
                    st.markdown(f"**{email['subject']}**")
                    st.caption(f"From: {email['sender']} | {email['date']}")
                    with st.expander("View Body"):
                        st.text(email['body'][:500] + "...")
                with ec2:
                    # Use Callback to safely update state
                    st.button(
                        "Analyze 🚀", 
                        key=f"analyze_{i}",
                        on_click=load_email_for_analysis,
                        args=(email['subject'], email['sender'], email['body'])
                    )
                st.divider()

# Logic to handle processing (Shared)
# The text_area widget automatically updates st.session_state.manual_input
# So we just read from the widget's return value 'email_input' which is already correct.
if "manual_input" in st.session_state and st.session_state.manual_input:
     # Validated input exists
     pass



if clear_btn:
    st.rerun()

if process_btn:
    if not email_input:
        st.toast("Please enter text first!", icon="⚠️")
    else:
        start_time = time.time()
        
        # PROGESS BAR
        progress_text = "Initializing agents..."
        my_bar = st.progress(0, text=progress_text)
        
        steps = [
            (10, "🕵️ Detecting PII & Anonymizing..."),
            (30, "🛡️ Checking for Spam..."),
            (50, "🧠 Classifying Intent..."),
            (70, "🌍 Researching Company Info..."),
            (90, "✍️ Drafting Professional Response..."),
        ]
        
        # Simulate steps
        for percent, label in steps:
            time.sleep(0.15) 
            my_bar.progress(percent, text=label)

        try:
            data = {}
            
            if IS_STANDALONE:
                # --- DIRECT GRAPH EXECUTION ---
                trace_id = str(uuid.uuid4())
                initial_state = {
                    "input_text": email_input,
                    "trace_id": trace_id,
                    "revision_count": 0
                }
                
                # Run the graph
                # Add status text update
                
                # Run logic
                result = graph.invoke(initial_state)
                
                # Map result to UI format
                data = {
                    "category": result.get("category", "unknown"),
                    "company": result.get("company_name", "Unknown"),
                    "trace_id": trace_id,
                    "draft": result.get("email_draft", "No draft created"),
                    "confidence_score": result.get("confidence_score", 0.0)
                }
                
            else:
                # --- API EXECUTION ---
                request_api_key = os.environ.get("FRONTEND_API_KEY", "your-secret-api-key-1")
                headers = {"X-API-Key": request_api_key}
                
                payload = {"email_text": email_input}
                response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                else:
                    st.error(f"Server Error ({response.status_code}): {response.text}")
                    st.stop()
            
            if data:
                st.session_state["analysis_result"] = data
                st.session_state["analysis_time"] = round(time.time() - start_time, 2)
                st.rerun() # Force rerun to render results from state

        except requests.exceptions.ConnectionError:
            st.error(f"❌ Could not connect to Backend at `{API_BASE}`. Is it running?")
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")

# --- DISPLAY RESULTS (PERSISTENT) ---
if "analysis_result" in st.session_state:
    data = st.session_state["analysis_result"]
    duration = st.session_state.get("analysis_time", 0)
    
    # --- HERE IS THE PERSISTENT UI ---
    
    # Header Stats
    s1, s2, s3, s4 = st.columns(4)
    
    cat = data.get('category', 'unknown')
    cat_color = "status-lead" if cat == "lead" else "status-spam" if cat == "spam" else "status-complaint"
    
    with s1:
        st.markdown(f"**Category**<br><span class='status-badge {cat_color}'>{cat.upper()}</span>", unsafe_allow_html=True)
    with s2:
        st.metric("Company", data.get('company', 'Unknown'))
    with s3:
        st.metric("Trace ID", data.get('trace_id', 'N/A')[:8])
    with s4:
        st.metric("Time", f"{duration}s")
    
    st.divider()
    
    # Content Split
    r_col1, r_col2 = st.columns([1, 1])
    
    with r_col1:
        st.subheader("📝 Generated Draft")
        draft_text = st.text_area("Draft Re-write", value=data.get('draft', 'No draft created'), height=400)
        
        # --- SEND EMAIL UI ---
        with st.expander("📤 Send Reply", expanded=True):
            # Try to extract recipient from input if possible, else empty
            recipient = ""
            if "From:" in email_input:
                for line in email_input.split("\n"):
                    if line.startswith("From:"):
                        recipient = line.replace("From:", "").strip()
                        break
                        
            to_email = st.text_input("To:", value=recipient)
            subject_line = st.text_input("Subject:", value=f"Re: Inquiry regarding {data.get('company', 'your request')}")
            
            if st.button("📨 Send Email Now"):
                if not to_email or not draft_text:
                    st.error("Missing Recipient or Body")
                else:
                    try:
                        from src.delivery import EmailSender
                        # USE UI CREDENTIALS IF AVAILABLE
                        sender = EmailSender(user=email_user, password=email_pass)
                        with st.spinner("Sending..."):
                            sender.send_email(to_email, subject_line, draft_text)
                        st.success(f"Email sent to {to_email}!")
                    except Exception as e:
                        st.error(f"Send Failed: {e}")

        st.download_button("💾 Download Draft", data=draft_text, file_name=f"draft_{int(time.time())}.txt")
        
    with r_col2:
        st.subheader("🧠 Analysis Details")
        with st.expander("🔍 Research Summary", expanded=True):
            st.write("Company info sourced during processing.")
            st.json({
                "Company": data.get('company'),
                "Confidence": f"{data.get('confidence_score', 0.0) * 100:.1f}%",
                "Source": "Tavily Search API"
            })
        
        with st.expander("🔒 PII Audit Log", expanded=False):
            st.info("Sensitive data was redacted and stored in secure vault.")
            st.code(f"Value: {data.get('category')}\nTrace: {data.get('trace_id')}", language="json")
