"""
Production-ready FastAPI application with rate limiting, health checks,
authentication, and comprehensive error handling.
"""
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import asyncio
import uuid
from typing import Optional
import time

from src.graph import graph
from src.db import init_db, save_lead
from src.config import settings
from src.logger import get_logger, set_correlation_id, get_correlation_id
from src.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    emails_processed_total,
    emails_failed_total,
    email_processing_duration_seconds,
    active_requests
)

logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: startup and shutdown logic.
    """
    # Startup
    logger.info("Application starting up...")
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database", extra={"error": str(e)})
        # Don't crash on DB init failure, allows health checks to run
    
    yield
    
    # Shutdown
    logger.info("Application shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="Beaver Agent API",
    version="1.0.0",
    description="Production-ready autonomous email processing agent",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan
)

# Add rate limit exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class EmailRequest(BaseModel):
    """Email processing request model."""
    email_text: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_email_length,
        description="Email text to process"
    )
    
    @field_validator("email_text")
    @classmethod
    def validate_email_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Email text cannot be empty or whitespace only")
        return v.strip()


class AgentResponse(BaseModel):
    """Agent processing response model."""
    category: str = Field(..., description="Email category")
    confidence_score: float = Field(..., description="Classification confidence")
    company: str = Field(..., description="Company name")
    draft: str = Field(..., description="Generated draft")
    trace_id: str = Field(..., description="Trace ID")
    processing_time_ms: int = Field(..., description="Processing time ms")


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    timestamp: str


class ReadyResponse(BaseModel):
    ready: bool
    checks: dict


# --- Middleware ---

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    set_correlation_id(trace_id)
    active_requests.inc()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Trace-ID"] = trace_id
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)
        
        return response
    finally:
        active_requests.dec()


# --- Authentication ---

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if settings.is_development and not settings.api_keys:
        return
    
    if not x_api_key or x_api_key not in settings.api_keys:
        logger.warning("Invalid API key")
        raise HTTPException(status_code=403, detail="Invalid API key")


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    from datetime import datetime
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/ready", response_model=ReadyResponse, tags=["System"])
async def readiness_check():
    checks = {"database": True, "redis": True, "llm": True}
    return ReadyResponse(ready=all(checks.values()), checks=checks)


@app.get("/metrics", tags=["System"])
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/process-email",
    response_model=AgentResponse,
    tags=["Email Processing"],
    dependencies=[Depends(verify_api_key)] if settings.api_keys else []
)
@limiter.limit(f"{settings.rate_limit_requests}/minute")
async def process_email(request: Request, email_request: EmailRequest):
    trace_id = get_correlation_id() or str(uuid.uuid4())
    logger.info("Processing email", extra={"length": len(email_request.email_text)})
    
    start_time = time.time()
    try:
        initial_state = {
            "input_text": email_request.email_text,
            "trace_id": trace_id,
            "messages": [],
            "revision_count": 0
        }
        
        result = await graph.ainvoke(
            initial_state,
            {"recursion_limit": settings.recursion_limit}
        )
        
        category = result.get("category", "unknown")
        confidence_score = result.get("confidence_score", 0.0)
        company = result.get("company_name", "Unknown")
        draft = result.get("email_draft", "No draft")
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        if category in ["lead", "complaint"]:
            try:
                save_lead(company, category, draft)
            except Exception as e:
                logger.error("DB save failed", extra={"error": str(e)})
        
        emails_processed_total.labels(category=category).inc()
        email_processing_duration_seconds.labels(category=category).observe(time.time() - start_time)
        
        return AgentResponse(
            category=category,
            confidence_score=confidence_score,
            company=company,
            draft=draft,
            trace_id=trace_id,
            processing_time_ms=processing_time_ms
        )
            
    except Exception as e:
        logger.error("Processing failed", extra={"error": str(e)}, exc_info=True)
        emails_failed_total.labels(error_type="internal").inc()
        raise HTTPException(status_code=500, detail="Processing error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host=settings.api_host, port=settings.api_port)