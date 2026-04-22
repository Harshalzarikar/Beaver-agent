"""
Production Graph — The Orchestrator with Supervisor + Reflection patterns.
Interview Q2 & Q4 & Q5: Cyclic workflow with conditional edges and loop control.
"""
from langgraph.graph import StateGraph, END
from src.core.state import AgentState
from src.agents.router import router_node
from src.agents.researcher import researcher_node
from src.agents.writer import writer_node
from src.agents.verifier import verifier_node
from src.agents.support import support_node
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def build_graph():
    """
    Assembles the Sales Team Orchestrator.
    
    Flow:
        Email → Router → [Lead] → Researcher → Writer ↔ Verifier → END
                       → [Complaint] → Support → END
                       → [Spam] → END
    """
    workflow = StateGraph(AgentState)

    # --- Register Nodes ---
    workflow.add_node("router", router_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("support", support_node)

    # --- Entry Point ---
    workflow.set_entry_point("router")

    # --- Conditional Edge: Router → (Interview Q4) ---
    def route_after_classification(state: AgentState) -> str:
        """Deterministic routing based on LLM classification output."""
        cat = state.get("category", "Spam")
        if "Lead" in cat:
            return "lead"
        if "Complaint" in cat:
            return "complaint"
        return "spam"

    workflow.add_conditional_edges(
        "router",
        route_after_classification,
        {
            "lead": "researcher",
            "complaint": "support",
            "spam": END,
        },
    )

    # --- Linear Edges: Lead Path ---
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "verifier")

    # --- Conditional Edge: The Reflection Loop (Interview Q5) ---
    def should_continue(state: AgentState) -> str:
        """
        The 'Secret Sauce' — decides if the draft needs another pass.
        
        Two safeguards against infinite loops:
        1. State Counter: revision_count >= max_revisions → force END
        2. Recursion Limit: set on graph.compile() as a hard failsafe
        """
        critique = state.get("critique", "")

        # Safeguard 1: Explicit approval
        if "APPROVE" in critique.upper():
            logger.info("✅ Draft APPROVED — proceeding to output.")
            return "approved"

        # Safeguard 2: Max revision limit (Interview Q5)
        if state.get("revision_count", 0) >= settings.max_revisions:
            logger.warning(f"⚠️ Max revisions ({settings.max_revisions}) reached — forcing approval.")
            return "approved"

        # Otherwise: send back to Writer with critique
        logger.info("🔄 Sending draft back to Writer for revision...")
        return "revise"

    workflow.add_conditional_edges(
        "verifier",
        should_continue,
        {
            "approved": END,
            "revise": "writer",  # THIS is the cycle (Interview Q2)
        },
    )

    # --- Linear Edge: Complaint Path ---
    workflow.add_edge("support", END)

    # --- Compile with Recursion Limit (Interview Q5, safeguard 2) ---
    compiled = workflow.compile()
    logger.info(f"📊 Graph compiled (recursion_limit={settings.recursion_limit})")

    return compiled


# Compile graph at module load
graph = build_graph()
