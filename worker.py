# File: worker.py
import asyncio
import uuid
import random
from src.graph import graph

# Simulate a Queue (Like Redis)
EMAIL_QUEUE = [
    "Hi, I want to buy enterprise licenses. Call 9822012345.",
    "My service is down! User ID 555.",
    "Click here for free money!",
    "I need help with my account 12345.",
    "Interested in a partnership. Contact harshal@test.com"
]

async def process_email_job(email: str, worker_id: int):
    """
    Simulates a Worker picking up a job from the Queue.
    """
    thread_id = str(uuid.uuid4())
    print(f"👷 Worker-{worker_id}: Picked up job [Thread: {thread_id[:4]}]")
    
    # Config for Checkpointing (Saving state to DB)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 10
    }
    
    initial_state = {
        "input_text": email,
        "revision_count": 0,
        "messages": []
    }

    # ASYNC EXECUTION (Non-blocking)
    try:
        # async for event in graph.astream(...): allows real-time streaming
        # Here we use ainvoke for simplicity
        result = await graph.ainvoke(initial_state, config=config)
        
        category = result.get("category", "unknown")
        print(f"✅ Worker-{worker_id}: Finished. Result: {category.upper()}")
        
    except Exception as e:
        print(f"❌ Worker-{worker_id}: Failed. Error: {e}")

async def run_worker_pool():
    print("🚀 STARTING ASYNC WORKER POOL (Simulating 10,000 scale)...")
    
    tasks = []
    # Create 5 concurrent workers
    for i, email in enumerate(EMAIL_QUEUE):
        # We start all jobs AT THE SAME TIME
        task = asyncio.create_task(process_email_job(email, i+1))
        tasks.append(task)
    
    # Wait for all workers to finish
    await asyncio.gather(*tasks)
    print("🏁 ALL JOBS PROCESSED.")

if __name__ == "__main__":
    asyncio.run(run_worker_pool())