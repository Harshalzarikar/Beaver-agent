# File: src/persistence.py
from langgraph.checkpoint.memory import MemorySaver

def get_checkpointer():
    """
    Uses RAM for checkpointing.
    Perfect for Async demos to avoid SQLite file-lock issues.
    """
    return MemorySaver()