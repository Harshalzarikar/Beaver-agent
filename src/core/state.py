"""
Production State Definition — The "File Folder" passed between agents.
Interview Q3: Every field is documented and typed.
"""
from typing import TypedDict, List, Annotated
import operator


class AgentState(TypedDict):
    """
    Central state object for the Sales Team Orchestrator.
    
    This TypedDict acts as the 'file folder' that every agent reads from 
    and writes to. LangGraph manages the lifecycle of this object.
    """
    # --- Input ---
    initial_email: str          # The raw inbound email content

    # --- Classification ---
    category: str               # "Lead", "Complaint", or "Spam"
    sender_name: str            # Extracted sender identity

    # --- Research ---
    company_name: str           # Extracted company name
    company_info: str           # Grounded research data from Tavily

    # --- Drafting ---
    draft_email: str            # Current version of the outbound draft

    # --- Reflection Loop (Interview Q5 & Q10) ---
    critique: str               # Verifier's feedback on the draft
    revision_count: int         # Tracks Writer↔Verifier iterations

    # --- Observability ---
    messages: Annotated[List[str], operator.add]  # Append-only audit log
