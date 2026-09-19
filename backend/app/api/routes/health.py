"""
Health check endpoint — includes database and model status.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.repositories.analysis_repository import check_db_connection
from app.ml.inference import get_model_health

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness health check",
    description="Returns basic application liveness and subsystem status.",
)
async def health(session: AsyncSession = Depends(get_session)) -> dict:
    """Basic service liveness check."""
    db_ok = await check_db_connection(session)
    model_health = get_model_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "connected" if db_ok else "unavailable",
        "model": model_health,
    }


@router.get(
    "/readiness",
    summary="Readiness health check",
    description="Returns 200 OK when ready to receive traffic, or 503 Service Unavailable if database is unreachable.",
)
async def readiness(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Readiness probe for load balancers and orchestrators."""
    db_ok = await check_db_connection(session)
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "service": settings.app_name,
            "ready": False,
            "database": "disconnected",
            "message": "Database is currently unavailable",
        }

    return {
        "status": "ready",
        "service": settings.app_name,
        "ready": True,
        "database": "connected",
    }


@router.get(
    "/model-health",
    summary="Model health check",
    description="Returns status and configuration of the active ML and NLI inference models.",
)
async def model_health_endpoint() -> dict:
    """Detailed ML inference status and configuration."""
    health_info = get_model_health()
    return {
        "service": settings.app_name,
        "model_backend": settings.model_backend,
        "model_name": settings.model_name,
        "model_device": settings.model_device,
        "model_load_on_startup": settings.model_load_on_startup,
        "nli_model_name": settings.nli_model_name,
        "nli_backend": settings.nli_backend,
        "model_status": health_info,
    }

