"""
Analysis repository — database CRUD operations.

All database access goes through this module.
Routes and services never construct SQL directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.model_run import ModelRun
from app.models.pipeline_event import PipelineEvent

logger = logging.getLogger(__name__)


# ── Health ───────────────────────────────────────────────────────────────


async def check_db_connection(session: AsyncSession) -> bool:
    """Run a trivial query to verify database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


# ── Create ───────────────────────────────────────────────────────────────


async def create_analysis(
    session: AsyncSession,
    *,
    input_text: str,
    language: str,
    assessment: str,
    confidence: Optional[float],
    evidence_strength: Optional[str],
    explanation: str,
    model_version: Optional[str] = None,
) -> Analysis:
    """Persist a new analysis and return the ORM instance."""
    analysis = Analysis(
        input_text=input_text,
        language=language,
        assessment=assessment,
        confidence=confidence,
        evidence_strength=evidence_strength,
        explanation=explanation,
        model_version=model_version,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(analysis)
    await session.flush()  # Populate id before return
    logger.info("Created analysis %s", analysis.id)
    return analysis


async def create_claim(
    session: AsyncSession,
    *,
    analysis_id: str,
    claim_text: str,
    normalized_claim: Optional[str] = None,
    claim_type: Optional[str] = None,
    entities: Optional[dict] = None,
) -> Claim:
    """Persist a claim linked to an analysis."""
    claim = Claim(
        analysis_id=analysis_id,
        claim_text=claim_text,
        normalized_claim=normalized_claim,
        claim_type=claim_type,
        entities=entities,
    )
    session.add(claim)
    await session.flush()
    return claim


async def create_evidence(
    session: AsyncSession,
    *,
    claim_id: str,
    source_name: str,
    source_url: str,
    title: str,
    snippet: str,
    relevance_score: Optional[float] = None,
    relation: str = "INSUFFICIENT",
    source_type: Optional[str] = None,
    published_at: Optional[datetime] = None,
) -> Evidence:
    """Persist an evidence item linked to a claim."""
    evidence = Evidence(
        claim_id=claim_id,
        source_name=source_name,
        source_url=source_url,
        title=title,
        snippet=snippet,
        relevance_score=relevance_score,
        relation=relation,
        source_type=source_type,
        published_at=published_at,
    )
    session.add(evidence)
    await session.flush()
    return evidence


async def create_pipeline_event(
    session: AsyncSession,
    *,
    analysis_id: str,
    stage: str,
    status: str = "completed",
    metadata: Optional[dict] = None,
) -> PipelineEvent:
    """Record a pipeline stage event."""
    event = PipelineEvent(
        analysis_id=analysis_id,
        stage=stage,
        status=status,
        metadata_=metadata,
    )
    session.add(event)
    await session.flush()
    return event


async def create_model_run(
    session: AsyncSession,
    *,
    analysis_id: str,
    model_name: str,
    model_version: str,
    prediction: Optional[str] = None,
    probabilities: Optional[dict] = None,
) -> ModelRun:
    """Record a model invocation."""
    run = ModelRun(
        analysis_id=analysis_id,
        model_name=model_name,
        model_version=model_version,
        prediction=prediction,
        probabilities=probabilities,
    )
    session.add(run)
    await session.flush()
    return run


# ── Read ─────────────────────────────────────────────────────────────────


async def get_analysis_by_id(
    session: AsyncSession, analysis_id: str
) -> Optional[Analysis]:
    """
    Fetch a single analysis with all related entities eagerly loaded.
    Returns None if not found.
    """
    stmt = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(
            selectinload(Analysis.claims).selectinload(Claim.evidence_items),
            selectinload(Analysis.model_runs),
            selectinload(Analysis.pipeline_events),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_analyses(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Analysis]:
    """List analyses ordered by creation time (newest first)."""
    stmt = (
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .options(
            selectinload(Analysis.claims).selectinload(Claim.evidence_items)
        )
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def purge_expired_analyses(
    session: AsyncSession,
    retention_days: int,
) -> int:
    """
    Purge analysis records older than retention_days.
    Cascades to related claims, evidence, model runs, and pipeline events via foreign keys.
    Returns the count of purged analyses.
    """
    from datetime import timedelta
    from sqlalchemy import delete

    if retention_days <= 0:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    stmt = delete(Analysis).where(Analysis.created_at < cutoff)
    result = await session.execute(stmt)
    await session.commit()
    count = result.rowcount or 0
    if count > 0:
        logger.info("Purged %d expired analyses older than %d days", count, retention_days)
    return count

