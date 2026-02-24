"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Application info
app_info = Info("centro_control", "Application information")

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    buckets=[100, 1000, 10000, 100000, 1000000]
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# Business metrics
leads_ingested_total = Counter(
    "leads_ingested_total",
    "Total leads ingested",
    ["cuenta_id", "source"]
)

leads_created_total = Counter(
    "leads_created_total",
    "Total leads created",
    ["cuenta_id"]
)

campaign_calls_total = Counter(
    "campaign_calls_total",
    "Total campaign calls made",
    ["campaign_id", "result"]
)

automation_executions_total = Counter(
    "automation_executions_total",
    "Total automation executions",
    ["automation_id", "status"]
)

webhook_dispatches_total = Counter(
    "webhook_dispatches_total",
    "Total webhook dispatches",
    ["webhook_id", "status"]
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request body size
        request_size = 0
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            request_size = len(body)
            # Need to put it back for the next middleware
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        
        http_request_size_bytes.observe(request_size)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Get endpoint path (sanitize to avoid high cardinality)
        endpoint = request.url.path
        # Replace IDs with placeholders to reduce cardinality
        import re
        endpoint = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/<id>', endpoint)
        endpoint = re.sub(r'/\d+', '/<id>', endpoint)
        
        # Record metrics
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()
        
        # Response size
        response_body = b""
        if hasattr(response, 'body'):
            response_body = response.body
        elif hasattr(response, 'body_iterator'):
            # For streaming responses, we can't get size easily
            pass
        http_response_size_bytes.observe(len(response_body))
        
        return response


def get_metrics_response():
    """Get Prometheus metrics as HTTP response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def record_lead_ingested(cuenta_id: str, source: str = "webhook"):
    """Record a lead ingestion."""
    leads_ingested_total.labels(
        cuenta_id=cuenta_id,
        source=source
    ).inc()


def record_lead_created(cuenta_id: str):
    """Record a lead creation."""
    leads_created_total.labels(cuenta_id=cuenta_id).inc()


def record_automation_execution(automation_id: str, status: str):
    """Record an automation execution."""
    automation_executions_total.labels(
        automation_id=automation_id,
        status=status
    ).inc()


def record_webhook_dispatch(webhook_id: str, success: bool):
    """Record a webhook dispatch."""
    webhook_dispatches_total.labels(
        webhook_id=webhook_id,
        status="success" if success else "failed"
    ).inc()
