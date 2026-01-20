"""
Prometheus metrics for monitoring application performance.
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time
from typing import Callable, Any

from src.config import settings


# --- Application Info ---
app_info = Info("beaver_agent", "Beaver Agent application information")
app_info.info({
    "version": "1.0.0",
    "environment": settings.environment,
    "model_provider": settings.model_provider
})

# --- Request Metrics ---
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

# --- Email Processing Metrics ---
emails_processed_total = Counter(
    "emails_processed_total",
    "Total emails processed",
    ["category"]  # lead, complaint, spam
)

emails_failed_total = Counter(
    "emails_failed_total",
    "Total emails that failed processing",
    ["error_type"]
)

email_processing_duration_seconds = Histogram(
    "email_processing_duration_seconds",
    "Email processing duration in seconds",
    ["category"]
)

# --- Agent Node Metrics ---
agent_node_duration_seconds = Histogram(
    "agent_node_duration_seconds",
    "Agent node execution duration in seconds",
    ["node_name"]
)

agent_node_executions_total = Counter(
    "agent_node_executions_total",
    "Total agent node executions",
    ["node_name"]
)

# --- PII Detection Metrics ---
pii_entities_detected_total = Counter(
    "pii_entities_detected_total",
    "Total PII entities detected",
    ["entity_type"]
)

pii_anonymization_duration_seconds = Histogram(
    "pii_anonymization_duration_seconds",
    "PII anonymization duration in seconds"
)

# --- LLM Metrics ---
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["provider", "model"]
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["provider"]
)

llm_tokens_used_total = Counter(
    "llm_tokens_used_total",
    "Total tokens used",
    ["provider", "type"]  # type: prompt, completion
)

# --- Database Metrics ---
db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation"]  # select, insert, update, delete
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"]
)

# --- Graph Workflow Metrics ---
graph_revisions_total = Counter(
    "graph_revisions_total",
    "Total graph revisions (writer retries)",
    ["final_status"]  # approved, rejected, max_retries
)

graph_loop_detections_total = Counter(
    "graph_loop_detections_total",
    "Total loop detections triggered"
)

# --- System Metrics ---
active_requests = Gauge(
    "active_requests",
    "Number of active requests being processed"
)

redis_connections_active = Gauge(
    "redis_connections_active",
    "Number of active Redis connections"
)


# --- Decorator for timing functions ---
def track_time(metric: Histogram, labels: dict[str, str] | None = None):
    """
    Decorator to track function execution time.
    
    Args:
        metric: Prometheus Histogram metric
        labels: Optional labels to add to the metric
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
