"""
Production Streamlit UI — Displays full agent trace and structured results.
"""
import streamlit as st
import requests
import os
import json

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Beaver Agent | Production", page_icon="🦫", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title("🦫 Beaver Agent")
    st.caption("Multi-Agent Sales Orchestrator v1.0")
    st.divider()
    
    st.markdown("### System")
    try:
        health = requests.get(f"{API_URL}/health", timeout=2).json()
        st.success(f"● {health['status'].upper()}")
    except Exception:
        st.error("● OFFLINE")
    
    st.divider()
    st.markdown("### Architecture")
    st.markdown("""
    - 🚦 **Router**: Email Classification  
    - 🔍 **Researcher**: Company Intel  
    - ✍️ **Writer**: Draft Generation  
    - ⚖️ **Verifier**: Quality Gate  
    - 🛡️ **Support**: Complaint Handler
    """)

# --- Main ---
st.header("📨 Inbound Email Processor")

col_input, col_output = st.columns([1, 1])

with col_input:
    email_text = st.text_area(
        "Paste email content",
        height=350,
        placeholder="Subject: Enterprise License Inquiry\n\nHi team, I'm the CTO at Acme Corp..."
    )
    run_btn = st.button("🚀 Run Agent Pipeline", use_container_width=True, type="primary")

if run_btn:
    if not email_text.strip():
        st.warning("Please enter email content.")
    else:
        with st.spinner("Executing multi-agent pipeline..."):
            try:
                res = requests.post(
                    f"{API_URL}/process",
                    json={"email_text": email_text},
                    timeout=120,
                ).json()

                with col_output:
                    # Status Badge
                    cat = res["category"]
                    color = "green" if "Lead" in cat else "orange" if "Complaint" in cat else "red"
                    st.markdown(f"### Status: :{color}[{cat}]")
                    
                    # Metrics
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Company", res.get("company") or "N/A")
                    m2.metric("Revisions", res.get("revisions", 0))
                    m3.metric("Time", f"{res.get('time_ms', 0)}ms")
                    
                    st.divider()
                    
                    # Draft
                    st.subheader("📝 Final Draft")
                    st.text_area("Output", value=res["draft"], height=250, label_visibility="collapsed")
                    st.download_button("💾 Download", data=res["draft"], file_name="draft.txt")
                    
                    # Trace
                    with st.expander("🕵️ Agent Execution Trace", expanded=True):
                        for step in res.get("trace", []):
                            st.write(f"→ {step}")
                            
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to backend at `{API_URL}`.")
            except Exception as e:
                st.error(f"Error: {e}")
