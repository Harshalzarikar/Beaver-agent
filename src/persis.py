from langgraph.checkpoint.memory import MemorySaver

def get_checkpointer():
    # Using In-Memory for Demo speed.
    # In PROD: Switch to AsyncPostgresSaver
    return MemorySaver()