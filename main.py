"""
Production API — FastAPI application with health checks, error handling, and CORS.
"""
import time
import uvicorn
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.core.graph import graph
from src.config import settings
from src.utils.db import db
from src.utils.logger import get_logger

logger = get_logger(__name__)


# --- Lifespan (modern FastAPI pattern) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    logger.info(f"🚀 {settings.app_name} started (debug={settings.debug})")
    yield
    logger.info(f"🛑 {settings.app_name} shutting down.")


# --- App ---
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production Multi-Agent Sales Orchestrator",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response Models ---
class ProcessRequest(BaseModel):
    email_text: str
    thread_id: str | None = None

class ProcessResponse(BaseModel):
    thread_id: str
    category: str
    company: str | None
    draft: str
    revisions: int
    time_ms: int
    trace: list[str]


# --- Endpoints ---
@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.app_name}


@app.post("/process", response_model=ProcessResponse)
async def process_email(req: ProcessRequest):
    """
    Main endpoint: Runs the full multi-agent orchestrator on an inbound email.
    """
    # Multi-user support: Generate or use provided thread ID
    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info(f"📨 New email received [Thread: {thread_id}]")
    start = time.time()

    try:
        # Pass thread_id in the configurable field (Standard LangGraph pattern)
        result = graph.invoke(
            {
                "initial_email": req.email_text,
                "messages": [f"📨 Request received (Thread: {thread_id})"],
            },
            {
                "recursion_limit": settings.recursion_limit,
                "configurable": {"thread_id": thread_id}
            },
        )
    except Exception as e:
        logger.error(f"Graph execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")

    category = result.get("category", "Unknown")
    company = result.get("company_name")
    draft = result.get("draft_email", "No response generated.")
    revisions = result.get("revision_count", 0)
    trace = result.get("messages", [])
    elapsed_ms = int((time.time() - start) * 1000)

    # Persist to DB with Thread ID
    try:
        db.save_record(
            category=category, 
            company=company or "N/A", 
            draft=draft,
            thread_id=thread_id
        )
    except Exception as e:
        logger.error(f"DB save failed: {e}")

    logger.info(f"✅ Done in {elapsed_ms}ms | {category} | Thread={thread_id}")

    return ProcessResponse(
        thread_id=thread_id,
        category=category,
        company=company,
        draft=draft,
        revisions=revisions,
        time_ms=elapsed_ms,
        trace=trace,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)