from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from src.graph import graph
from src.db import init_db, save_lead

# 1. Initialize App & DB
app = FastAPI(title="Beaver Agent API", version="1.0")
init_db()

# 2. Define Request Schema (The Input)
class EmailRequest(BaseModel):
    email_text: str

# 3. Define Response Schema (The Output)
class AgentResponse(BaseModel):
    category: str
    company: str
    draft: str
    trace_id: str

@app.post("/process-email", response_model=AgentResponse)
async def process_email(request: EmailRequest):
    """
    Endpoint that triggers the Autonomous Agent.
    """
    trace_id = str(uuid.uuid4())
    print(f"🌍 API Request received. Trace ID: {trace_id}")

    try:
        # Prepare State
        initial_state = {
            "input_text": request.email_text,
            "trace_id": trace_id,
            "messages": [],
            "revision_count": 0
        }

        # Run Graph (Blocking for simplicity in MVP)
        # In prod, we would use a background task
        result = graph.invoke(initial_state, {"recursion_limit": 10})

        # Extract Data
        category = result.get("category", "unknown")
        company = result.get("company_name", "Unknown")
        draft = result.get("email_draft", "No draft created")

        # Save to DB
        if category in ["lead", "complaint"]:
            save_lead(company, category, draft)

        return AgentResponse(
            category=category,
            company=company,
            draft=draft,
            trace_id=trace_id
        )

    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# To run: uvicorn src.api:app --reload