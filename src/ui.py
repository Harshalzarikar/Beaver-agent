import streamlit as st
import requests

# Set API URL (Where FastAPI is running)
API_URL = "http://127.0.0.1:8000/process-email"

st.set_page_config(page_title="Beaver AI", page_icon="🦫", layout="centered")

st.title("🦫 Autonomous Email Agent")
st.markdown("### Powered by LangGraph & Hybrid AI")

# Input Area
email_input = st.text_area("Paste Incoming Email:", height=150, placeholder="Hi, I want to buy...")

if st.button("🚀 Process Email", type="primary"):
    if not email_input:
        st.warning("Please enter an email text.")
    else:
        # Show a cool loading spinner
        with st.status("🤖 AI Agents working...", expanded=True) as status:
            st.write("1️⃣  Scanning for PII & Spam...")
            st.write("2️⃣  Routing to correct Agent...")
            st.write("3️⃣  Drafting & Verifying response...")
            
            try:
                # CALL THE FASTAPI BACKEND
                payload = {"email_text": email_input}
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    status.update(label="✅ Processing Complete!", state="complete", expanded=False)
                    
                    # Display Results
                    st.divider()
                    
                    # Metrics Row
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Category", data['category'].upper())
                    col2.metric("Company", data['company'])
                    col3.metric("Trace ID", data['trace_id'][:8])
                    
                    # Final Email
                    st.subheader("📝 Generated Draft")
                    st.code(data['draft'], language="text")
                    
                    st.success("Draft saved to Database.")
                    
                else:
                    status.update(label="❌ Error", state="error")
                    st.error(f"API Error: {response.text}")
                    
            except Exception as e:
                st.error(f"Connection Error: Is FastAPI running? \n{e}")

# Footer
st.markdown("---")
st.caption("Architecture: Streamlit → FastAPI → LangGraph → Gemini/Local LLM")