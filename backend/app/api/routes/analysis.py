"""
Analysis endpoints:
  POST /api/v1/analyze  — submit a claim for verification
  GET  /api/v1/analysis/{analysis_id} — retrieve a stored result
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import mask_sensitive_input, request_id_ctx
from app.db.session import get_session
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, AnalysisSummary, ErrorResponse
from app.services.analysis_service import (
    AnalysisServiceError,
    analyze_claim,
    get_analysis,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze a claim",
    description=(
        "Submit text for verification. The service extracts the claim, "
        "retrieves evidence, and returns a structured assessment."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input or unsupported language"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal error"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def analyze(
    body: AnalysisRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisResponse:
    """Run the verification pipeline on the submitted text."""
    rid = request_id_ctx.get("-")
    logger.info(
        "Received analysis request — %s, language: %s",
        mask_sensitive_input(body.text),
        body.language.value,
    )

    try:
        result = await analyze_claim(body, session=session)
    except AnalysisServiceError as exc:
        logger.warning("Analysis failed: %s (code=%s)", exc, exc.code)
        raise HTTPException(
            status_code=400,
            detail={
                "error": exc.code,
                "message": str(exc),
                "request_id": rid,
            },
        )
    except SQLAlchemyError as db_exc:
        logger.error("Database unavailable during analysis: %s", db_exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "message": "Database is temporarily unavailable. The verification request could not be persisted.",
                "request_id": rid,
            },
        )
    except Exception:
        logger.exception("Unexpected error during analysis")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred during analysis",
                "request_id": rid,
            },
        )

    return result


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Retrieve a stored analysis",
    description="Fetch a previously completed analysis by its ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def get_analysis_by_id(
    analysis_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisResponse:
    """Look up a stored analysis result."""
    try:
        result = await get_analysis(session, analysis_id)
    except SQLAlchemyError as db_exc:
        logger.error("Database unavailable during lookup of %s: %s", analysis_id, db_exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "message": "Database is temporarily unavailable.",
                "request_id": request_id_ctx.get("-"),
            },
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Analysis '{analysis_id}' not found",
                "request_id": request_id_ctx.get("-"),
            },
        )

    return result
 
 
@router.get(
    "/analyses",
    response_model=list[AnalysisSummary],
    summary="List recent analyses",
    description="Fetch previously completed analyses from the database for the investigation history.",
    responses={
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def list_recent_analyses(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> list[AnalysisSummary]:
    """Retrieve stored analyses for history display."""
    try:
        from app.repositories import analysis_repository as repo
        from app.services.confidence import determine_confidence_tier
        from app.schemas.analysis import Assessment, EvidenceStrength

        records = await repo.list_analyses(session, limit=limit, offset=offset)
        summaries: list[AnalysisSummary] = []
        for r in records:
            claim_text = r.claims[0].claim_text if r.claims else r.input_text
            claim_type = r.claims[0].claim_type if r.claims else None
            ev_count = sum(len(c.evidence_items) for c in r.claims) if r.claims else 0

            tier = determine_confidence_tier(
                confidence=r.confidence,
                evidence_strength=EvidenceStrength(r.evidence_strength) if r.evidence_strength else None,
                has_conflict=(r.assessment == Assessment.CONFLICTING_EVIDENCE.value),
                has_evidence=(ev_count > 0),
            )

            summaries.append(
                AnalysisSummary(
                    analysis_id=r.id,
                    language=r.language,
                    claim=claim_text,
                    claim_type=claim_type,
                    assessment=Assessment(r.assessment),
                    confidence=r.confidence,
                    confidence_tier=tier.value,
                    evidence_strength=EvidenceStrength(r.evidence_strength) if r.evidence_strength else None,
                    evidence_count=ev_count,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                )
            )
        return summaries
    except SQLAlchemyError as db_exc:
        logger.error("Database unavailable during list_analyses: %s", db_exc)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "service_unavailable",
                "message": "Database is temporarily unavailable.",
                "request_id": request_id_ctx.get("-"),
            },
        )

