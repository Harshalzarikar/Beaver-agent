from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.agents import (
    router_node, 
    researcher_node, 
    writer_node, 
    verifier_node, 
    support_node, 
    final_delivery_node
)

# --- 1. DEFINE ROUTING LOGIC ---

def route_after_router(state: AgentState):
    """Decides path based on the Router's classification."""
    category = state["category"]
    if category == "lead":
        return "researcher"
    elif category == "complaint":
        return "support"
    else:
        return END # Spam -> Stop

def route_after_verifier(state: AgentState):
    """
    Decides if we need to rewrite the email.
    Includes LOOP DETECTION logic.
    """
    status = state.get("final_status")
    revision_count = state.get("revision_count", 0)
    
    # ✅ APPROVED: Go to delivery
    if status == "approved":
        return "final_delivery"
    
    # 🛑 LOOP DETECTOR (The "Soft Stop")
    # If we have tried 3 times and failed, STOP looping.
    # It is better to send an imperfect email than to crash.
    if revision_count > 3:
        print("⚠️ [Graph] Loop Detector triggered: Max revisions reached. Proceeding to delivery.")
        return "final_delivery" 
    
    # 🔄 REJECTED: Try again (Loop back)
    return "writer"

# --- 2. BUILD THE GRAPH ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", router_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)
workflow.add_node("verifier", verifier_node)
workflow.add_node("support", support_node)
workflow.add_node("final_delivery", final_delivery_node)

# Set Entry Point
workflow.set_entry_point("router")

# --- 3. WIRE EDGES ---

# Router Split
workflow.add_conditional_edges(
    "router", 
    route_after_router,
    {
        "researcher": "researcher",
        "support": "support",
        END: END
    }
)

# Sales Pipeline (Cyclic)
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "verifier")

workflow.add_conditional_edges(
    "verifier",
    route_after_verifier,
    {
        "writer": "writer",                 # Retry
        "final_delivery": "final_delivery"  # Done (or Force Done)
    }
)

# Support Pipeline
workflow.add_edge("support", "final_delivery")

# Exit
workflow.add_edge("final_delivery", END)

# Compile
graph = workflow.compile()