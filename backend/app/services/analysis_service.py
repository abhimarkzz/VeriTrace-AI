"""
Analysis service — business logic for claim verification.

Orchestrates: language detection → text normalization → claim extraction
→ evidence retrieval → assessment. Uses real NLP services for Steps 1-3.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories import analysis_repository as repo
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    Assessment,
    ConfidenceBreakdown,
    EvidenceStrength,
    PipelineStatus,
)
from app.schemas.evidence import EvidenceItem
from app.services.evidence import (
    NormalizedEvidence,
    normalize_to_evidence_item,
    rank_and_verify_evidence,
    retrieve_evidence,
    VerifiedEvidenceItem,
    VerificationSynthesisResult,
)
from app.services.language_detection import (
    detect_language,
    DetectionStatus,
)
from app.services.text_normalization import normalize_text
from app.services.claim_extraction import extract_claims, Claimability
from app.ml.inference import classify_claim, is_ml_available
from app.services.calibration import (
    calibrate_probabilities,
    calibration_registry,
)
from app.services.confidence import (
    ConfidenceTier,
    determine_confidence_tier,
)
from app.services.decision_engine import (
    DecisionInput,
    fuse_decision,
)

logger = logging.getLogger(__name__)


class AnalysisServiceError(Exception):
    """Raised when analysis processing fails."""

    def __init__(self, message: str, *, code: str = "analysis_error") -> None:
        super().__init__(message)
        self.code = code


async def analyze_claim(
    request: AnalysisRequest,
    session: Optional[AsyncSession] = None,
) -> AnalysisResponse:
    """
    Run the full analysis pipeline on user-submitted text.

    Pipeline stages:
      1. Text normalization
      2. Language detection
      3. Claim extraction + checkability assessment
      4. Evidence retrieval
      5. Evidence ranking and NLI verification
      6. Decision fusion and uncertainty calibration
    """
    t0 = time.perf_counter()

    # ── Step 0: Reject obviously oversized input before normalization ────
    if len(request.text) > settings.max_input_length:
        raise AnalysisServiceError(
            f"Input text exceeds maximum length of {settings.max_input_length} characters",
            code="input_too_long",
        )

    # ── Step 1: Text normalization ───────────────────────────────────────
    normalized = normalize_text(request.text)

    if len(normalized) > settings.max_input_length:
        raise AnalysisServiceError(
            f"Input text exceeds maximum length of {settings.max_input_length} characters",
            code="input_too_long",
        )

    if not normalized:
        raise AnalysisServiceError(
            "Input text is empty after normalization",
            code="empty_input",
        )

    # ── Step 2: Language detection ───────────────────────────────────────
    lang_result = detect_language(normalized, request.language.value)
    language = lang_result.language_code or "en"

    if lang_result.status == DetectionStatus.UNSUPPORTED_LANGUAGE:
        raise AnalysisServiceError(
            f"Language '{lang_result.language_code or 'unknown'}' is unsupported. "
            "VeriTrace AI currently verifies claims in English, Hindi, and Telugu.",
            code="unsupported_language",
        )

    lang_status = "completed"
    lang_metadata: dict = {
        "detected_code": lang_result.language_code,
        "detected_name": lang_result.language_name,
        "confidence": lang_result.confidence,
        "status": lang_result.status.value,
    }

    # ── Step 3: Claim extraction ─────────────────────────────────────────
    claims = extract_claims(normalized, language)

    # Use the first checkable claim, or fall back to the full text
    primary_claim = normalized
    primary_claim_type = None
    primary_claimability = Claimability.CHECKABLE
    primary_entities: list[str] = []

    if claims:
        # Prefer the first CHECKABLE claim
        checkable = [c for c in claims if c.claimability == Claimability.CHECKABLE]
        best = checkable[0] if checkable else claims[0]
        primary_claim = best.claim_text
        primary_claim_type = best.claim_type
        primary_claimability = best.claimability
        primary_entities = best.entities

    # ── Step 4: Evidence retrieval ───────────────────────────────────────
    evidence_items: list[EvidenceItem] = []
    raw_evidence_items: list[NormalizedEvidence] = []
    verified_evidence_items: list[VerifiedEvidenceItem] = []
    evidence_synthesis: Optional[VerificationSynthesisResult] = None
    evidence_metadata: dict = {"status": "skipped", "reason": "non_checkable"}
    evidence_status = "skipped"
    retrieval_latency_ms = 0.0
    nli_latency_ms = 0.0

    if primary_claimability != Claimability.NON_CHECKABLE:
        t_retrieval = time.perf_counter()
        try:
            retrieval_res = await retrieve_evidence(
                query=primary_claim,
                language=language,
            )
        except Exception as exc:
            logger.warning("Evidence retrieval failed unexpectedly: %s", exc)
            from app.services.evidence.base import EvidenceRetrievalResult
            retrieval_res = EvidenceRetrievalResult(
                items=[],
                provider="error_fallback",
                query=primary_claim,
                language=language,
                error=f"Retrieval error: {exc}",
            )
        retrieval_latency_ms = round((time.perf_counter() - t_retrieval) * 1000, 2)
        raw_evidence_items = retrieval_res.items
        evidence_status = "completed" if raw_evidence_items else ("failed" if retrieval_res.error else "no_results")
        evidence_metadata = {
            "provider": retrieval_res.provider,
            "evidence_count": len(raw_evidence_items),
            "cached": retrieval_res.cached,
            "error": retrieval_res.error,
        }

        # ── Step 7: Evidence Ranking & Verification ──────────────────────────
        t_nli = time.perf_counter()
        verified_evidence_items, evidence_synthesis = rank_and_verify_evidence(
            claim=primary_claim,
            candidates=raw_evidence_items,
            language=language,
        )
        nli_latency_ms = round((time.perf_counter() - t_nli) * 1000, 2)
        for idx, v_item in enumerate(verified_evidence_items):
            evidence_items.append(EvidenceItem(
                id=f"ev-{idx + 1:03d}",
                title=v_item.evidence.title,
                source=v_item.source_metadata.publisher,
                url=v_item.evidence.url,
                snippet=v_item.evidence.snippet,
                relevance_score=round(v_item.relevance_score, 4),
                source_quality=0.90 if v_item.source_metadata.is_verified_fact_checker else 0.70,
                relation=v_item.relation.to_api_relation(),
                publisher=v_item.source_metadata.publisher,
                published_at=v_item.evidence.published_at,
            ))


    # ── Step 5: ML Inference & Calibration ──────────────────────────────
    ml_result = None
    calibrated_probabilities: Optional[dict[str, float]] = None
    calibrated_confidence: Optional[float] = None

    if is_ml_available():
        ml_result = classify_claim(primary_claim)
        if ml_result.label != "ML_UNAVAILABLE" and ml_result.probabilities:
            # Look up calibration profile for model_version
            cal_params = calibration_registry.get(ml_result.model_version or "default")
            calibrated_probabilities = calibrate_probabilities(
                ml_result.probabilities, temperature=cal_params.temperature
            )
            calibrated_confidence = max(calibrated_probabilities.values()) if calibrated_probabilities else None

    # ── Step 8: Decision Fusion & Uncertainty-Aware Assessment ─────────
    top_ev_relevance = (
        verified_evidence_items[0].relevance_score if verified_evidence_items else 0.0
    )
    source_diversity = (
        len(set(v.group_id for v in verified_evidence_items if v.is_independent))
        if verified_evidence_items
        else 0
    )
    evidence_avail = len([
        v for v in verified_evidence_items
        if v.is_independent and v.relevance_score >= settings.evidence_min_relevance_threshold
    ]) if verified_evidence_items else 0
    has_conflict = (
        (evidence_synthesis.independent_support_count > 0 and evidence_synthesis.independent_contradict_count > 0)
        if evidence_synthesis
        else False
    )

    decision_inp = DecisionInput(
        classifier_prediction=ml_result.label if ml_result and ml_result.label != "ML_UNAVAILABLE" else None,
        classifier_probability=calibrated_confidence,
        classifier_probabilities=calibrated_probabilities or (ml_result.probabilities if ml_result else None),
        top_evidence_relevance=top_ev_relevance,
        nli_verdict=evidence_synthesis.assessment.value if evidence_synthesis else None,
        source_diversity=source_diversity,
        evidence_availability=evidence_avail,
        has_conflict=has_conflict,
        has_strong_contradiction=evidence_synthesis.has_strong_contradiction if evidence_synthesis else False,
        independent_support_count=evidence_synthesis.independent_support_count if evidence_synthesis else 0,
        independent_contradict_count=evidence_synthesis.independent_contradict_count if evidence_synthesis else 0,
        mean_source_quality=0.90 if any(v.source_metadata.is_verified_fact_checker for v in verified_evidence_items) else 0.70,
        is_non_checkable=(primary_claimability == Claimability.NON_CHECKABLE),
        claimability_reason=(
            "The input was identified as a non-checkable statement "
            "(opinion, question, or subjective content). "
            "Fact verification requires verifiable factual claims."
            if primary_claimability == Claimability.NON_CHECKABLE
            else (
                "The input contains ambiguous or conditional language "
                "(predictions, hedged statements). Verification confidence is limited."
                if primary_claimability == Claimability.AMBIGUOUS
                else None
            )
        ),
    )

    decision_out = fuse_decision(decision_inp)

    if not is_ml_available() or (ml_result and ml_result.label == "ML_UNAVAILABLE"):
        # Honest baseline without active ML sequence classification
        assessment = Assessment.INSUFFICIENT_EVIDENCE
        confidence = None
        confidence_breakdown = None
        confidence_tier = ConfidenceTier.LOW
        evidence_strength = decision_out.evidence_strength
        evidence_note = (
            f"Found {len(evidence_items)} independent fact-check evidence sources."
            if evidence_items
            else "No external fact-check reviews found."
        )
        if ml_result and ml_result.label == "ML_UNAVAILABLE":
            explanation = (
                "ML model returned unavailable status. "
                f"Retrieved {len(evidence_items)} independent evidence sources."
                if evidence_items
                else "ML model returned unavailable status. Classification could not be performed."
            )
        else:
            explanation = (
                f"The claim was successfully extracted and analyzed. {evidence_note} "
                "No ML model is loaded. Set MODEL_LOAD_ON_STARTUP=true to enable ML inference."
            )
        confidence_explanation = (
            "No ML model is loaded. Assessment is limited to insufficient evidence with low confidence."
        )
    else:
        assessment = decision_out.assessment
        confidence = decision_out.confidence
        confidence_tier = decision_out.confidence_tier
        evidence_strength = decision_out.evidence_strength
        confidence_breakdown = decision_out.confidence_breakdown
        confidence_explanation = decision_out.confidence_explanation
        explanation = decision_out.explanation

    # ── Persist to database if session available ─────────────────────────
    analysis_id: str
    if session is not None:
        persisted_input_text = (
            normalized
            if settings.persist_user_input_text
            else f"[REDACTED_PRIVACY_PROTECTED] (SHA256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]})"
        )
        analysis_record = await repo.create_analysis(
            session,
            input_text=persisted_input_text,
            language=language,
            assessment=assessment.value,
            confidence=confidence,
            evidence_strength=evidence_strength.value if evidence_strength else None,
            explanation=explanation,
            model_version=ml_result.model_version if ml_result and ml_result.label != "ML_UNAVAILABLE" else None,
        )
        analysis_id = analysis_record.id

        # Create claim record with real extraction data
        claim_record = await repo.create_claim(
            session,
            analysis_id=analysis_id,
            claim_text=primary_claim,
            normalized_claim=primary_claim,
            claim_type=primary_claim_type,
            entities={"names": primary_entities} if primary_entities else None,
        )

        # Persist each evidence item linked to this claim
        for v_item, ev_schema in zip(verified_evidence_items, evidence_items):
            pub_date = None
            if v_item.evidence.published_at:
                try:
                    from datetime import datetime as dt
                    pub_date = dt.fromisoformat(v_item.evidence.published_at.replace("Z", "+00:00"))
                except Exception:
                    pub_date = None

            await repo.create_evidence(
                session,
                claim_id=claim_record.id,
                source_name=v_item.source_metadata.publisher,
                source_url=v_item.evidence.url,
                title=v_item.evidence.title,
                snippet=v_item.evidence.snippet,
                published_at=pub_date,
                relevance_score=ev_schema.relevance_score,
                relation=ev_schema.relation.value,
                source_type=v_item.evidence.source_type,
            )

        # Record pipeline events with real metadata
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="language_detection",
            status=lang_status,
            metadata=lang_metadata,
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="text_normalization",
            status="completed",
            metadata={"input_length": len(request.text), "output_length": len(normalized)},
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="claim_extraction",
            status="completed",
            metadata={
                "claims_found": len(claims),
                "primary_claimability": primary_claimability.value,
                "claim_type": primary_claim_type,
            },
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="evidence_retrieval",
            status=evidence_status,
            metadata=evidence_metadata,
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="evidence_ranking",
            status="completed" if verified_evidence_items else "skipped",
            metadata={
                "ranked_count": len(verified_evidence_items),
                "top_k": settings.evidence_top_k,
                "independent_groups": (
                    len(set(v.group_id for v in verified_evidence_items))
                    if verified_evidence_items
                    else 0
                ),
            },
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="evidence_verification",
            status="completed" if verified_evidence_items else "skipped",
            metadata={
                "independent_supports": evidence_synthesis.independent_support_count if evidence_synthesis else 0,
                "independent_contradicts": evidence_synthesis.independent_contradict_count if evidence_synthesis else 0,
                "has_strong_contradiction": evidence_synthesis.has_strong_contradiction if evidence_synthesis else False,
                "evidence_verdict": evidence_synthesis.assessment.value if evidence_synthesis else "INSUFFICIENT_EVIDENCE",
            },
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="decision_fusion",
            status="completed",
            metadata={
                "assessment": assessment.value,
                "confidence": confidence,
                "confidence_tier": confidence_tier.value,
                "evidence_strength": evidence_strength.value if evidence_strength else None,
                "rules_triggered": decision_out.decision_policy_trace.get("rules_triggered", []),
                "signals": decision_out.decision_policy_trace.get("signals", {}),
            },
        )
        await repo.create_pipeline_event(
            session,
            analysis_id=analysis_id,
            stage="assessment_generation",
            status="completed",
            metadata={
                "method": "decision_engine_fused",
                "model_name": ml_result.model_name if ml_result else None,
                "inference_time_ms": ml_result.inference_time_ms if ml_result else None,
                "evidence_count": len(evidence_items),
                "confidence_tier": confidence_tier.value,
            },
        )

        # Record model run if ML was used
        if ml_result and ml_result.label != "ML_UNAVAILABLE":
            await repo.create_model_run(
                session,
                analysis_id=analysis_id,
                model_name=ml_result.model_name,
                model_version=ml_result.model_version,
                prediction=ml_result.label,
                probabilities=calibrated_probabilities or ml_result.probabilities,
            )

        logger.info("Analysis %s persisted to database", analysis_id)
    else:
        import uuid
        analysis_id = uuid.uuid4().hex[:12]

    total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "Analysis %s completed — lang=%s claim_type=%s assessment=%s tier=%s retrieval_ms=%.1f nli_ms=%.1f total_ms=%.1f",
        analysis_id, language, primary_claim_type,
        assessment.value, confidence_tier.value,
        retrieval_latency_ms, nli_latency_ms, total_latency_ms,
        extra={
            "analysis_id": analysis_id,
            "language": language,
            "stage": "completed",
            "model_version": ml_result.model_version if ml_result and ml_result.label != "ML_UNAVAILABLE" else "baseline",
            "retrieval_latency_ms": retrieval_latency_ms,
            "nli_latency_ms": nli_latency_ms,
            "total_latency_ms": total_latency_ms,
        },
    )

    return AnalysisResponse(
        analysis_id=analysis_id,
        language=language,
        claim=primary_claim,
        claim_type=primary_claim_type,
        assessment=assessment,
        confidence=confidence,
        confidence_breakdown=confidence_breakdown,
        confidence_tier=confidence_tier.value,
        confidence_explanation=confidence_explanation,
        evidence_strength=evidence_strength,
        evidence=evidence_items,
        explanation=explanation,
        pipeline_status=PipelineStatus.COMPLETED,
    )


async def get_analysis(
    session: AsyncSession,
    analysis_id: str,
) -> Optional[AnalysisResponse]:
    """
    Retrieve a stored analysis by ID and map to the API response schema.
    Returns None if not found.
    """
    record = await repo.get_analysis_by_id(session, analysis_id)
    if record is None:
        return None

    # Map claim data
    claim_text = record.claims[0].claim_text if record.claims else record.input_text
    claim_type = record.claims[0].claim_type if record.claims else None

    # Map evidence from all claims
    evidence_items = []
    for c in record.claims:
        for e in c.evidence_items:
            from app.schemas.evidence import EvidenceItem as EvidenceSchema
            evidence_items.append(EvidenceSchema(
                id=e.id,
                title=e.title,
                source=e.source_name,
                url=e.source_url,
                snippet=e.snippet,
                relevance_score=e.relevance_score or 0.0,
                source_quality=0.0,
                relation=e.relation,
                publisher=e.source_name,
                published_at=e.published_at.isoformat() if e.published_at else None,
            ))

    conf_tier = determine_confidence_tier(
        confidence=record.confidence,
        evidence_strength=EvidenceStrength(record.evidence_strength) if record.evidence_strength else None,
        has_conflict=(record.assessment == Assessment.CONFLICTING_EVIDENCE.value),
        has_evidence=bool(evidence_items),
    )

    return AnalysisResponse(
        analysis_id=record.id,
        language=record.language,
        claim=claim_text,
        claim_type=claim_type,
        assessment=Assessment(record.assessment),
        confidence=record.confidence,
        confidence_breakdown=None,
        confidence_tier=conf_tier.value,
        confidence_explanation=None,
        evidence_strength=EvidenceStrength(record.evidence_strength) if record.evidence_strength else None,
        evidence=evidence_items,
        explanation=record.explanation,
        pipeline_status=PipelineStatus.COMPLETED,
    )

