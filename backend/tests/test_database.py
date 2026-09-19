"""
Database model and repository tests.

Tests CRUD operations, foreign-key integrity, cascade deletes,
invalid relationships, duplicate handling, and rollback behavior.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.model_run import ModelRun
from app.models.pipeline_event import PipelineEvent
from app.repositories import analysis_repository as repo


# ── Migration / Schema ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tables_exist(async_session) -> None:
    """All 5 tables should be created by the fixture."""
    async with async_session() as session:
        # Query sqlite_master for table names
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic%'")
        )
        tables = {row[0] for row in result.fetchall()}
        assert "analyses" in tables
        assert "claims" in tables
        assert "evidence" in tables
        assert "model_runs" in tables
        assert "pipeline_events" in tables


# ── CRUD: Analysis ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_analysis(async_session) -> None:
    """Should create an analysis record with auto-generated id and timestamps."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Test claim",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test explanation",
        )
        await session.commit()

        assert analysis.id is not None
        assert len(analysis.id) == 12
        assert analysis.input_text == "Test claim"
        assert analysis.language == "en"
        assert analysis.created_at is not None
        assert analysis.completed_at is not None


@pytest.mark.asyncio
async def test_get_analysis_by_id(async_session) -> None:
    """Should retrieve an analysis by its ID with relationships."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Retrievable claim",
            language="hi",
            assessment="SUPPORTED",
            confidence=0.9,
            evidence_strength="STRONG",
            explanation="Well-supported",
        )
        await session.commit()
        aid = analysis.id

    async with async_session() as session:
        fetched = await repo.get_analysis_by_id(session, aid)
        assert fetched is not None
        assert fetched.id == aid
        assert fetched.language == "hi"
        assert fetched.confidence == 0.9


@pytest.mark.asyncio
async def test_get_analysis_not_found(async_session) -> None:
    """Should return None for non-existent ID."""
    async with async_session() as session:
        result = await repo.get_analysis_by_id(session, "doesnotexist")
        assert result is None


@pytest.mark.asyncio
async def test_list_analyses(async_session) -> None:
    """Should list analyses ordered by creation time."""
    async with async_session() as session:
        for i in range(3):
            await repo.create_analysis(
                session,
                input_text=f"Claim {i}",
                language="en",
                assessment="INSUFFICIENT_EVIDENCE",
                confidence=None,
                evidence_strength=None,
                explanation=f"Explanation {i}",
            )
        await session.commit()

    async with async_session() as session:
        results = await repo.list_analyses(session, limit=10)
        assert len(results) == 3


# ── CRUD: Claim ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_claim_with_analysis(async_session) -> None:
    """Should create a claim linked to an analysis."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Parent analysis",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        claim = await repo.create_claim(
            session,
            analysis_id=analysis.id,
            claim_text="Extracted claim",
            normalized_claim="extracted claim",
            claim_type="factual",
            entities={"org": ["RBI"]},
        )
        await session.commit()

        assert claim.id is not None
        assert claim.analysis_id == analysis.id
        assert claim.claim_type == "factual"
        assert claim.entities == {"org": ["RBI"]}


# ── CRUD: Evidence ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_evidence_with_claim(async_session) -> None:
    """Should create evidence linked to a claim."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Evidence test",
            language="en",
            assessment="SUPPORTED",
            confidence=0.8,
            evidence_strength="MODERATE",
            explanation="Has evidence",
        )
        claim = await repo.create_claim(
            session,
            analysis_id=analysis.id,
            claim_text="Some claim",
        )
        evidence = await repo.create_evidence(
            session,
            claim_id=claim.id,
            source_name="Reuters",
            source_url="https://reuters.com/article",
            title="Article Title",
            snippet="Relevant excerpt...",
            relevance_score=0.85,
            relation="SUPPORT",
            source_type="news",
        )
        await session.commit()

        assert evidence.id is not None
        assert evidence.claim_id == claim.id
        assert evidence.source_name == "Reuters"
        assert evidence.relevance_score == 0.85


# ── CRUD: ModelRun ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_model_run(async_session) -> None:
    """Should create a model run record."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Model run test",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        run = await repo.create_model_run(
            session,
            analysis_id=analysis.id,
            model_name="gemini-2.0-flash",
            model_version="2.0",
            prediction="SUPPORTED",
            probabilities={"SUPPORTED": 0.7, "MISLEADING": 0.3},
        )
        await session.commit()

        assert run.id is not None
        assert run.model_name == "gemini-2.0-flash"
        assert run.probabilities["SUPPORTED"] == 0.7


# ── CRUD: PipelineEvent ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_pipeline_event(async_session) -> None:
    """Should create a pipeline event record."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Pipeline test",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        event = await repo.create_pipeline_event(
            session,
            analysis_id=analysis.id,
            stage="language_detection",
            status="completed",
            metadata={"detected": "en", "confidence": 0.99},
        )
        await session.commit()

        assert event.id is not None
        assert event.stage == "language_detection"
        assert event.metadata_["detected"] == "en"


# ── Foreign Key Integrity ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_claim_requires_valid_analysis_id(async_session) -> None:
    """Creating a claim with a non-existent analysis_id should fail."""
    async with async_session() as session:
        claim = Claim(
            analysis_id="nonexistent1",
            claim_text="Orphan claim",
        )
        session.add(claim)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.asyncio
async def test_evidence_requires_valid_claim_id(async_session) -> None:
    """Creating evidence with a non-existent claim_id should fail."""
    async with async_session() as session:
        evidence = Evidence(
            claim_id="nonexistent1",
            source_name="Test",
            source_url="https://test.com",
            title="Test",
            snippet="Test snippet",
            relation="SUPPORT",
        )
        session.add(evidence)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.asyncio
async def test_model_run_requires_valid_analysis_id(async_session) -> None:
    """Creating a model run with a non-existent analysis_id should fail."""
    async with async_session() as session:
        run = ModelRun(
            analysis_id="nonexistent1",
            model_name="test-model",
            model_version="1.0",
        )
        session.add(run)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


@pytest.mark.asyncio
async def test_pipeline_event_requires_valid_analysis_id(async_session) -> None:
    """Creating a pipeline event with a non-existent analysis_id should fail."""
    async with async_session() as session:
        event = PipelineEvent(
            analysis_id="nonexistent1",
            stage="test_stage",
            status="completed",
        )
        session.add(event)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


# ── Cascade Deletes ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cascade_delete_analysis(async_session) -> None:
    """Deleting an analysis should cascade to claims, evidence, model_runs, events."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Cascade test",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        claim = await repo.create_claim(
            session, analysis_id=analysis.id, claim_text="Claim"
        )
        await repo.create_evidence(
            session,
            claim_id=claim.id,
            source_name="Test",
            source_url="https://test.com",
            title="T",
            snippet="S",
            relation="SUPPORT",
        )
        await repo.create_model_run(
            session,
            analysis_id=analysis.id,
            model_name="test",
            model_version="1.0",
        )
        await repo.create_pipeline_event(
            session, analysis_id=analysis.id, stage="test"
        )
        await session.commit()
        aid = analysis.id

    # Delete the analysis
    async with async_session() as session:
        analysis = await session.get(Analysis, aid)
        assert analysis is not None
        await session.delete(analysis)
        await session.commit()

    # Verify cascade
    async with async_session() as session:
        assert await session.get(Analysis, aid) is None
        claims = (await session.execute(select(Claim).where(Claim.analysis_id == aid))).scalars().all()
        assert len(claims) == 0
        runs = (await session.execute(select(ModelRun).where(ModelRun.analysis_id == aid))).scalars().all()
        assert len(runs) == 0
        events = (await session.execute(select(PipelineEvent).where(PipelineEvent.analysis_id == aid))).scalars().all()
        assert len(events) == 0


# ── Duplicate Handling ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_analysis_ids_are_unique(async_session) -> None:
    """Two analyses created separately should have different IDs."""
    async with async_session() as session:
        a1 = await repo.create_analysis(
            session,
            input_text="First",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        a2 = await repo.create_analysis(
            session,
            input_text="Second",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        await session.commit()
        assert a1.id != a2.id


@pytest.mark.asyncio
async def test_same_text_creates_separate_analyses(async_session) -> None:
    """Submitting the same text twice should create two separate records."""
    async with async_session() as session:
        a1 = await repo.create_analysis(
            session,
            input_text="Duplicate text",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        a2 = await repo.create_analysis(
            session,
            input_text="Duplicate text",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        await session.commit()
        assert a1.id != a2.id

    async with async_session() as session:
        results = await repo.list_analyses(session, limit=10)
        assert len(results) == 2


# ── Rollback Behavior ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rollback_on_error(async_session) -> None:
    """Failed operations should not persist partial data."""
    async with async_session() as session:
        analysis = await repo.create_analysis(
            session,
            input_text="Rollback test",
            language="en",
            assessment="INSUFFICIENT_EVIDENCE",
            confidence=None,
            evidence_strength=None,
            explanation="Test",
        )
        aid = analysis.id

        # Attempt to create a claim with invalid FK (should fail)
        bad_claim = Claim(
            analysis_id="nonexistent1",
            claim_text="Bad claim",
        )
        session.add(bad_claim)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()

    # Verify the analysis was rolled back too
    async with async_session() as session:
        result = await session.get(Analysis, aid)
        # After rollback, the analysis should not be persisted
        assert result is None


# ── DB Health Check ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_db_health_check(async_session) -> None:
    """Repository health check should return True for a working database."""
    async with async_session() as session:
        assert await repo.check_db_connection(session) is True
