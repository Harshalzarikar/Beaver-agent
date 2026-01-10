import os
import uuid
from dotenv import load_dotenv, find_dotenv
from src.graph import graph
from src.db import init_db, save_lead

# Load Keys (LangSmith + Google)
load_dotenv(find_dotenv())

def run_scenario(input_message: str, scenario_name: str):
    print(f"\n\n🚀 STARTING SCENARIO: {scenario_name}")
    print("=" * 60)
    print(f"📩 Input: {input_message.strip()}")
    
    # 1. Trace ID (Used in LangSmith to find this specific run)
    current_trace_id = str(uuid.uuid4())
    print(f"🕵️ TRACE ID: {current_trace_id}")
    
    # 2. RUN GRAPH
    try:
        initial_state = {
            "input_text": input_message,
            "trace_id": current_trace_id,
            "messages": [],  
            "revision_count": 0
        }

        # 🛡️ THE SAFETY NET (Hard Stop)
        # recursion_limit=15 prevents infinite billing loops
        result = graph.invoke(
            initial_state, 
            {"recursion_limit": 15}  
        )
        
        # 3. OUTPUT
        final_email = result.get("email_draft", "No draft created")
        category = result.get("category", "unknown")
        
        # Save to DB
        if category in ["lead", "complaint"]:
            init_db()
            save_lead(
                company_name=result.get("company_name", "Unknown"),
                category=category,
                email_draft=final_email
            )

        print("\n#################################################")
        print(f"✅ FINAL OUTPUT ({scenario_name})")
        print("#################################################")
        print(f"📝 Final Email (Restored Data):\n{final_email}")
        print("#################################################\n")
            
    except Exception as e:
        print(f"🚨 SYSTEM ALERT: {e}")

if __name__ == "__main__":
    
    # Test 1: Sales Lead (Will generate Traces in LangSmith)
    lead_msg = """
    Hi, I am Harshal from Cogninest AI. 
    We want to buy your enterprise license. 
    Call me at 9822012345 or email harshal@cogninest.com.
    """
    run_scenario(lead_msg, "Sales Lead + PII + LangSmith Trace")

    # Test 2: Spam
    run_scenario("Click here for free iPhone $1000", "Spam Filter")