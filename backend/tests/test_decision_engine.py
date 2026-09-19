"""
Tests for STEP 8: Decision Fusion and Uncertainty-Aware Output.

Covers:
1. Calibration: temperature scaling (softening/sharpening), ECE, Brier score, registry persistence.
2. Confidence & Uncertainty: qualitative tiers, bounds enforcement, transparent explanation generation.
3. Decision Policy Scenarios:
   - High classifier / weak evidence
   - Low classifier / strong evidence
   - Conflicting evidence
   - No evidence
   - Multiple independent supporting sources (increases evidence strength, not model probability)
   - Non-checkable input
   - Threshold boundaries (0.50, 0.75, 0.30)
4. Pipeline Integration: database persistence of decision_fusion event and response schema.
"""

from __future__ import annotations

import math
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.schemas.analysis import (
    AnalysisRequest,
    Assessment,
    ConfidenceBreakdown,
    EvidenceStrength,
    Language,
)
from app.services.calibration import (
    CalibrationParams,
    CalibrationRegistry,
    calibrate_probabilities,
    compute_brier_score,
    compute_ece,
    fit_temperature,
)
from app.services.confidence import (
    ConfidenceTier,
    calculate_confidence_breakdown,
    determine_confidence_tier,
    generate_confidence_explanation,
)
from app.services.decision_engine import (
    DecisionEngine,
    DecisionInput,
    DecisionOutput,
    fuse_decision,
)
from app.services.analysis_service import analyze_claim
from app.ml.model_registry import registry
from app.repositories import analysis_repository as repo


# ── 1. Calibration Tests ───────────────────────────────────────────────────


class TestCalibration:
    """Validates temperature scaling, ECE, Brier score, and parameter registry."""

    def test_temperature_scaling_identity_at_one(self):
        """T = 1.0 should preserve original probabilities."""
        probs = {"SUPPORTED": 0.70, "POTENTIALLY_MISLEADING": 0.20, "INSUFFICIENT_EVIDENCE": 0.10}
        calibrated = calibrate_probabilities(probs, temperature=1.0)
        assert math.isclose(calibrated["SUPPORTED"], 0.70, abs_tol=1e-4)
        assert math.isclose(calibrated["POTENTIALLY_MISLEADING"], 0.20, abs_tol=1e-4)
        assert math.isclose(calibrated["INSUFFICIENT_EVIDENCE"], 0.10, abs_tol=1e-4)
        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-4)

    def test_temperature_scaling_softening(self):
        """T > 1.0 should soften overconfident probabilities toward uniform."""
        probs = {"SUPPORTED": 0.90, "POTENTIALLY_MISLEADING": 0.08, "INSUFFICIENT_EVIDENCE": 0.02}
        calibrated = calibrate_probabilities(probs, temperature=1.5)
        # Top probability should decrease, lower probabilities should increase
        assert calibrated["SUPPORTED"] < 0.90
        assert calibrated["POTENTIALLY_MISLEADING"] > 0.08
        assert calibrated["INSUFFICIENT_EVIDENCE"] > 0.02
        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-4)

    def test_temperature_scaling_sharpening(self):
        """T < 1.0 should sharpen probabilities toward argmax."""
        probs = {"SUPPORTED": 0.60, "POTENTIALLY_MISLEADING": 0.30, "INSUFFICIENT_EVIDENCE": 0.10}
        calibrated = calibrate_probabilities(probs, temperature=0.5)
        assert calibrated["SUPPORTED"] > 0.60
        assert math.isclose(sum(calibrated.values()), 1.0, abs_tol=1e-4)

    def test_temperature_scaling_invalid_temp(self):
        """Negative or zero temperature should raise ValueError."""
        probs = {"SUPPORTED": 0.8, "REFUTED": 0.2}
        with pytest.raises(ValueError):
            calibrate_probabilities(probs, temperature=0.0)
        with pytest.raises(ValueError):
            calibrate_probabilities(probs, temperature=-1.0)

    def test_compute_ece(self):
        """Test Expected Calibration Error calculation."""
        # Perfectly calibrated: 10 samples with confidence 1.0 that are all correct
        confs_perfect = [1.0] * 10
        preds_perfect = ["A"] * 10
        truths_perfect = ["A"] * 10
        assert compute_ece(confs_perfect, preds_perfect, truths_perfect) == 0.0

        # Completely miscalibrated: confidence 1.0, but all wrong
        truths_wrong = ["B"] * 10
        ece_bad = compute_ece(confs_perfect, preds_perfect, truths_wrong)
        assert math.isclose(ece_bad, 1.0, abs_tol=1e-3)

    def test_compute_brier_score(self):
        """Test multi-class Brier score calculation."""
        # Perfect predictions: probability 1.0 for true class
        probs_perfect = [{"A": 1.0, "B": 0.0}, {"A": 0.0, "B": 1.0}]
        truths_perfect = ["A", "B"]
        brier_perfect = compute_brier_score(probs_perfect, truths_perfect, ["A", "B"])
        assert brier_perfect == 0.0

        # Complete disagreement: probability 1.0 for wrong class
        probs_wrong = [{"A": 0.0, "B": 1.0}, {"A": 1.0, "B": 0.0}]
        brier_wrong = compute_brier_score(probs_wrong, truths_perfect, ["A", "B"])
        # ( (0-1)^2 + (1-0)^2 ) = 2.0 per sample
        assert math.isclose(brier_wrong, 2.0, abs_tol=1e-3)

    def test_fit_temperature(self):
        """Fitting temperature should find optimal T and improve ECE on overconfident data."""
        # Create synthetic overconfident dataset
        classes = ["SUPPORTED", "POTENTIALLY_MISLEADING"]
        probs = []
        truths = []
        # Model is 95% confident on everything, but only 70% accurate
        for i in range(100):
            if i < 70:
                probs.append({"SUPPORTED": 0.95, "POTENTIALLY_MISLEADING": 0.05})
                truths.append("SUPPORTED")
            else:
                probs.append({"SUPPORTED": 0.95, "POTENTIALLY_MISLEADING": 0.05})
                truths.append("POTENTIALLY_MISLEADING")

        params = fit_temperature(probs, truths, classes, model_version="test-v1")
        assert params.model_version == "test-v1"
        assert params.temperature > 1.0  # Must soften to improve calibration
        assert params.ece_calibrated < params.ece_uncalibrated

    def test_calibration_registry_persistence(self, tmp_path: Path):
        """Test registry loading, saving, and version lookup."""
        file_path = tmp_path / "registry.json"
        reg = CalibrationRegistry(storage_path=file_path)

        # Register profile
        reg.register(
            CalibrationParams(
                model_version="xlmr-tuned-v1",
                temperature=1.35,
                ece_calibrated=0.045,
                brier_calibrated=0.12,
            )
        )
        assert file_path.exists()

        # Reload in new instance
        reg2 = CalibrationRegistry(storage_path=file_path)
        fetched = reg2.get("xlmr-tuned-v1")
        assert fetched.temperature == 1.35
        assert fetched.ece_calibrated == 0.045

        # Unknown model should return default configuration
        default_profile = reg2.get("unknown-model-xyz")
        assert default_profile.temperature == settings.calibration_temperature


# ── 2. Confidence & Uncertainty Tiers ──────────────────────────────────────


class TestConfidenceAndTiers:
    """Validates qualitative uncertainty tier assignments and safety bounds."""

    def test_determine_confidence_tier_no_evidence(self):
        """Zero evidence must never produce HIGH CONFIDENCE."""
        tier = determine_confidence_tier(
            confidence=0.95,
            evidence_strength=None,
            has_evidence=False,
        )
        assert tier == ConfidenceTier.LOW

    def test_determine_confidence_tier_weak_evidence_capped(self):
        """Weak evidence caps tier at MODERATE or LOW regardless of high confidence."""
        tier = determine_confidence_tier(
            confidence=0.95,
            evidence_strength=EvidenceStrength.WEAK,
            has_evidence=True,
        )
        assert tier == ConfidenceTier.MODERATE
        assert tier != ConfidenceTier.HIGH

    def test_determine_confidence_tier_conflicting_evidence_capped(self):
        """Conflicting evidence caps tier at MODERATE or LOW."""
        tier = determine_confidence_tier(
            confidence=0.88,
            evidence_strength=EvidenceStrength.STRONG,
            has_conflict=True,
            has_evidence=True,
        )
        assert tier == ConfidenceTier.MODERATE
        assert tier != ConfidenceTier.HIGH

    def test_determine_confidence_tier_high_achievable(self):
        """HIGH CONFIDENCE requires confidence >= 0.75 and MODERATE or STRONG evidence."""
        tier = determine_confidence_tier(
            confidence=0.85,
            evidence_strength=EvidenceStrength.STRONG,
            has_conflict=False,
            has_evidence=True,
        )
        assert tier == ConfidenceTier.HIGH

    def test_generate_confidence_explanation_high_classifier_weak_evidence(self):
        """High model confidence with weak evidence triggers cautionary explanation."""
        expl = generate_confidence_explanation(
            model_confidence=0.92,
            evidence_strength=EvidenceStrength.WEAK,
            evidence_count=1,
            independent_sources=1,
            has_conflict=False,
        )
        assert "High model confidence, but only limited independent evidence was retrieved." in expl

    def test_generate_confidence_explanation_conflicting(self):
        """Conflicting evidence explicitly states penalty and disagreement."""
        expl = generate_confidence_explanation(
            model_confidence=0.80,
            evidence_strength=EvidenceStrength.MODERATE,
            evidence_count=2,
            independent_sources=2,
            has_conflict=True,
        )
        assert "Conflicting evidence was retrieved" in expl
        assert "penalized" in expl

    def test_generate_confidence_explanation_no_evidence(self):
        """No evidence states inconclusive verdict."""
        expl = generate_confidence_explanation(
            model_confidence=None,
            evidence_strength=None,
            evidence_count=0,
            independent_sources=0,
            has_conflict=False,
        )
        assert "No external evidence was retrieved" in expl


# ── 3. Decision Policy Scenarios ───────────────────────────────────────────


class TestDecisionPolicyScenarios:
    """Validates the documented decision policy across critical edge cases."""

    def test_high_classifier_weak_evidence(self):
        """
        Rule: If classifier confidence is high but evidence is weak:
        do not display a strong certainty claim.
        """
        inp = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probability=0.92,
            classifier_probabilities={"SUPPORTED": 0.92, "POTENTIALLY_MISLEADING": 0.08},
            top_evidence_relevance=0.20,  # Below threshold -> weak evidence
            evidence_availability=1,
            source_diversity=1,
            has_conflict=False,
            independent_support_count=0,
            independent_contradict_count=0,
        )
        out = fuse_decision(inp)

        # Classification direction may be preserved tentatively, but certainty tier CANNOT be HIGH
        assert out.assessment == Assessment.SUPPORTED
        assert out.confidence_tier != ConfidenceTier.HIGH
        assert out.confidence_tier in (ConfidenceTier.MODERATE, ConfidenceTier.LOW)
        assert "High model confidence, but only limited independent evidence was retrieved." in out.confidence_explanation
        assert out.evidence_strength is None or out.evidence_strength == EvidenceStrength.WEAK

    def test_low_classifier_strong_evidence(self):
        """
        Rule: If classifier confidence is low or uncertain, but strong independent
        evidence contradicts: external evidence overrides classifier.
        """
        inp = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probability=0.45,  # Low classifier certainty
            classifier_probabilities={"SUPPORTED": 0.45, "POTENTIALLY_MISLEADING": 0.55},
            top_evidence_relevance=0.88,
            nli_verdict="CONTRADICTS",
            evidence_availability=2,
            source_diversity=2,
            has_strong_contradiction=True,
            independent_support_count=0,
            independent_contradict_count=2,
        )
        out = fuse_decision(inp)

        # Verified external evidence overrides classifier!
        assert out.assessment == Assessment.POTENTIALLY_MISLEADING
        assert out.evidence_strength == EvidenceStrength.STRONG
        # Standalone model probability is honestly preserved in breakdown, not falsely overwritten
        assert out.confidence_breakdown is not None
        assert out.confidence_breakdown.model_confidence == 0.45

    def test_conflicting_evidence_shows_conflicting_verdict(self):
        """
        Rule: If evidence is contradictory: show conflicting evidence.
        """
        inp = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probability=0.80,
            top_evidence_relevance=0.85,
            nli_verdict="CONFLICTING",
            source_diversity=2,
            evidence_availability=2,
            has_conflict=True,
            independent_support_count=1,
            independent_contradict_count=1,
        )
        out = fuse_decision(inp)

        assert out.assessment == Assessment.CONFLICTING_EVIDENCE
        assert "RULE_CONFLICTING_EVIDENCE" in out.decision_policy_trace["rules_triggered"]
        # Conflict penalty must be applied to confidence
        assert out.confidence < 0.80
        # Certainty tier cannot be HIGH
        assert out.confidence_tier != ConfidenceTier.HIGH

    def test_no_evidence_does_not_produce_strong_verdict(self):
        """
        Rule: If there is no sufficient evidence: do NOT produce a strong verdict.
        """
        inp = DecisionInput(
            classifier_prediction=None,
            classifier_probability=None,
            top_evidence_relevance=0.0,
            evidence_availability=0,
            source_diversity=0,
            has_conflict=False,
        )
        out = fuse_decision(inp)

        assert out.assessment == Assessment.INSUFFICIENT_EVIDENCE
        assert out.confidence is None
        assert out.confidence_tier == ConfidenceTier.LOW
        assert out.evidence_strength is None
        assert "No external evidence was retrieved" in out.confidence_explanation

    def test_multiple_independent_sources_increases_evidence_strength(self):
        """
        Rule: If multiple sources independently support a claim:
        increase evidence strength, not automatically the model probability.
        """
        inp = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probability=0.75,
            top_evidence_relevance=0.85,
            nli_verdict="SUPPORTS",
            source_diversity=3,  # 3 distinct publishers
            evidence_availability=3,
            independent_support_count=3,
            independent_contradict_count=0,
            has_conflict=False,
        )
        out = fuse_decision(inp)

        assert out.assessment == Assessment.SUPPORTED
        # Evidence strength elevated to STRONG
        assert out.evidence_strength == EvidenceStrength.STRONG
        # High confidence tier achieved
        assert out.confidence_tier == ConfidenceTier.HIGH
        # Model probability in breakdown is NOT falsely inflated beyond 0.75
        assert out.confidence_breakdown.model_confidence == 0.75

    def test_non_checkable_input(self):
        """Non-checkable input yields INSUFFICIENT_EVIDENCE with LOW confidence tier."""
        inp = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probability=0.85,
            is_non_checkable=True,
            claimability_reason="Subjective opinion detected.",
        )
        out = fuse_decision(inp)

        assert out.assessment == Assessment.INSUFFICIENT_EVIDENCE
        assert out.confidence == 0.0
        assert out.confidence_tier == ConfidenceTier.LOW
        assert out.evidence_strength is None
        assert "Subjective opinion detected" in out.explanation

    def test_threshold_boundaries(self):
        """Test edge behavior at boundary thresholds."""
        engine = DecisionEngine(
            min_relevance_threshold=0.30,
            confidence_high_threshold=0.75,
            confidence_moderate_threshold=0.50,
        )

        # Exact boundary 0.75 should yield HIGH if evidence is STRONG
        tier_exact_high = determine_confidence_tier(
            confidence=0.75,
            evidence_strength=EvidenceStrength.STRONG,
            has_conflict=False,
            has_evidence=True,
        )
        assert tier_exact_high == ConfidenceTier.HIGH

        # 0.7499 should yield MODERATE
        tier_just_below_high = determine_confidence_tier(
            confidence=0.7499,
            evidence_strength=EvidenceStrength.STRONG,
            has_conflict=False,
            has_evidence=True,
        )
        assert tier_just_below_high == ConfidenceTier.MODERATE

        # Exact boundary 0.50 should yield MODERATE
        tier_exact_mod = determine_confidence_tier(
            confidence=0.50,
            evidence_strength=EvidenceStrength.MODERATE,
            has_conflict=False,
            has_evidence=True,
        )
        assert tier_exact_mod == ConfidenceTier.MODERATE

        # 0.4999 should yield LOW
        tier_below_mod = determine_confidence_tier(
            confidence=0.4999,
            evidence_strength=EvidenceStrength.MODERATE,
            has_conflict=False,
            has_evidence=True,
        )
        assert tier_below_mod == ConfidenceTier.LOW


# ── 4. Pipeline Integration & Database Persistence ─────────────────────────


@pytest_asyncio.fixture
async def async_session():
    """In-memory SQLite async session for pipeline database testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestPipelineStep8Integration:
    """Verifies that decision fusion records pipeline events and responds correctly."""

    @pytest.mark.asyncio
    async def test_pipeline_decision_fusion_event_persisted(self, async_session):
        """Pipeline must persist the 'decision_fusion' event and return uncertainty fields."""
        registry.load_mock_model(
            model_name="FacebookAI/xlm-roberta-base",
            model_version="xlmr-v1.0",
            fixed_label="SUPPORTED",
        )

        request = AnalysisRequest(
            text="WHO recommends R21 malaria vaccine for children across endemic areas.",
            language=Language.EN,
        )
        async with async_session() as session:
            response = await analyze_claim(request, session=session)

            assert response.assessment == Assessment.SUPPORTED
            assert response.confidence is not None
            assert response.confidence_tier in ("HIGH CONFIDENCE", "MODERATE CONFIDENCE")
            assert response.confidence_explanation is not None

            # Retrieve persisted analysis and pipeline events from DB
            analysis = await repo.get_analysis_by_id(session, response.analysis_id)
            assert analysis is not None
            stage_names = [e.stage for e in analysis.pipeline_events]
            assert "decision_fusion" in stage_names

            # Check metadata of decision_fusion event
            df_event = next(e for e in analysis.pipeline_events if e.stage == "decision_fusion")
            assert df_event.status == "completed"
            assert "assessment" in df_event.metadata_
            assert "confidence_tier" in df_event.metadata_
            assert "rules_triggered" in df_event.metadata_
