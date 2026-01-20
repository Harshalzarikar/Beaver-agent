import streamlit as st
import requests
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
# Get API URL from environment variable (Render support)
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
st.markdown("## 📨 Incoming Message Processor")
st.markdown("Paste email content below to trigger the autonomous workflow.")

col1, col2 = st.columns([2, 1])

with col1:
    email_input = st.text_area(
        "Email Content",
        height=300,
        placeholder="Subject: Enterprise License Inquiry\n\nHi team, I am interested in purchasing...",
        label_visibility="collapsed"
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
    process_btn = st.button("🚀 Process Email", use_container_width=True)
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

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
        
        # Simulate steps (since API is one call)
        for percent, label in steps:
            time.sleep(0.15) 
            my_bar.progress(percent, text=label)

        try:
            # API CALL
            # Use environment API key or fallback to the first dev key
            request_api_key = os.environ.get("FRONTEND_API_KEY", "your-secret-api-key-1")
            headers = {"X-API-Key": request_api_key}
            
            payload = {"email_text": email_input}
            response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=120)
            
            my_bar.progress(100, text="✅ Done!")
            time.sleep(0.5)
            my_bar.empty()
            
            if response.status_code == 200:
                data = response.json()
                duration = round(time.time() - start_time, 2)
                
                # --- RESULTS DISPLAY ---
                st.balloons()
                
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
                    st.text_area("Draft Re-write", value=data.get('draft', 'No draft created'), height=400)
                    st.download_button("💾 Download Draft", data=data.get('draft', ''), file_name=f"draft_{int(time.time())}.txt")
                    
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

            else:
                st.error(f"Server Error ({response.status_code}): {response.text}")

        except requests.exceptions.ConnectionError:
            st.error(f"❌ Could not connect to Backend at `{API_BASE}`. Is it running?")
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")