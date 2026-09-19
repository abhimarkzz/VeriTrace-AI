"""
VeriTrace AI — FastAPI application entry point.

Assembles middleware, CORS, routes, and lifecycle hooks.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.routes import analysis, health
from app.core.config import settings
from app.core.logging import generate_request_id, request_id_ctx, setup_logging
from app.core.security import RateLimitMiddleware

# ── Bootstrap logging before anything else ──────────────────────────────
setup_logging(
    level="DEBUG" if settings.app_debug else "INFO",
    log_format=settings.log_format,
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown lifecycle."""
    from app.db.base import Base
    from app.db.session import engine
    import app.models  # noqa: F401 — register all models with Base.metadata

    logger.info(
        "%s v%s starting (env=%s, db=%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
    )

    # Auto-create tables in development (production uses Alembic migrations)
    if settings.is_development:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")

    # Optionally load ML model on startup
    if settings.model_load_on_startup:
        try:
            from app.ml.model_registry import registry
            if settings.model_backend == "mock":
                info = registry.load_mock_model(model_name=settings.model_name)
            elif settings.model_backend == "hosted" and settings.model_endpoint_url:
                info = registry.load_hosted_model(
                    endpoint_url=settings.model_endpoint_url,
                    api_key=settings.model_api_key,
                    model_name=settings.model_name,
                )
            else:
                info = registry.load_model(
                    model_name=settings.model_name,
                    device=settings.model_device,
                    max_length=settings.model_max_length,
                )
            logger.info("ML model status: %s", info.status.value)
        except Exception as e:
            logger.warning("ML model load failed (non-fatal): %s", e)
    else:
        logger.info("ML model loading skipped (MODEL_LOAD_ON_STARTUP=false)")


    yield

    await engine.dispose()
    logger.info("Shutting down")


# ── Application factory ─────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multilingual, evidence-grounded misinformation verification API. "
        "Accepts claims in English, Hindi, and Telugu, retrieves evidence, "
        "and returns a structured assessment with a full evidence trail."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

@app.get("/api/docs", include_in_schema=False)
async def api_docs_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


# ── CORS ─────────────────────────────────────────────────────────────────

cors_origins = settings.cors_origin_list
has_wildcard = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if has_wildcard else cors_origins,
    allow_origin_regex=r"^https?://.*" if has_wildcard else r"^https?://([a-zA-Z0-9.-]+\.)?(trycloudflare\.com|localhost|127\.0\.0\.1|lhr\.life)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

# ── Rate Limiting ────────────────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)


# ── Request-ID & Timing Middleware ───────────────────────────────────────

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach a unique request ID and measure response time."""
    rid = generate_request_id()
    request_id_ctx.set(rid)
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start
    response.headers["X-Request-ID"] = rid
    logger.info(
        "%s %s → %d (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed * 1000,
    )
    return response


# ── Global exception handlers ────────────────────────────────────────────

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Return structured JSON instead of the default 422 body."""
    rid = request_id_ctx.get("-")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request body failed validation",
            "details": exc.errors(),
            "request_id": rid,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler to prevent leaking connection strings,
    file paths, passwords, or system internals in HTTP responses.
    """
    from sqlalchemy.exc import SQLAlchemyError

    rid = request_id_ctx.get("-")
    logger.exception("Unhandled error processing request: %s", exc)

    if isinstance(exc, SQLAlchemyError):
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "message": "Database service is temporarily unavailable.",
                "request_id": rid,
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": rid,
        },
    )


# ── Routes ───────────────────────────────────────────────────────────────

# Cloud standard root health checks (/health, /readiness, /model-health)
app.include_router(health.router)

# Versioned API routes (/api/v1/...)
app.include_router(health.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")

