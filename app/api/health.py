from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from app.database.session import get_primary_session, get_replica_session
from sqlalchemy import text

router = APIRouter()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

DB_OPERATION_LATENCY = Histogram(
    'db_operation_duration_seconds',
    'Database operation latency',
    ['operation', 'node']
)

@router.get("/health")
async def health_check(
    primary_db: Session = Depends(get_primary_session),
    replica_db: Session = Depends(get_replica_session)
):
    """Health check endpoint that verifies database connectivity"""
    health_status = {
        "status": "healthy",
        "primary_db": "up",
        "replica_db": "up"
    }
    
    try:
        # Check primary connection
        primary_db.execute(text("SELECT 1"))
    except Exception as e:
        health_status["primary_db"] = "down"
        health_status["status"] = "unhealthy"
    
    try:
        # Check replica connection
        replica_db.execute(text("SELECT 1"))
    except Exception as e:
        health_status["replica_db"] = "down"
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    ) 