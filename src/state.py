import operator
from typing import TypedDict, Annotated, List, Union

class AgentState(TypedDict):
    # --- 1. The Input & Trace ---
    input_text: str
    trace_id: str
    
    # --- 2. The Logic Flags ---
    category: str               # "lead", "complaint", "spam"
    confidence_score: float     # Classification confidence
    revision_count: int         # To stop infinite loops
    final_status: str           # "approved", "rejected"
    
    # --- 3. Agent Data ---
    company_name: str           
    company_info: str           
    email_draft: str            
    feedback: str               
    
    # --- 4. THE INTERVIEW WINNER (Reducer) ---
    # This allows agents to add logs/messages without deleting old ones
    messages: Annotated[List[str], operator.add]
