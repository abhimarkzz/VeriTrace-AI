"""
Decision Fusion Engine for VeriTrace AI.

Encodes the core safety and correctness layer:
    MODEL CONFIDENCE ≠ EVIDENCE STRENGTH ≠ TRUTH PROBABILITY

Input Signals:
1. classifier prediction (label)
2. classifier probability (calibrated softmax confidence)
3. top evidence relevance (from ranking)
4. NLI relationship (SUPPORTS, CONTRADICTS, NOT_ENOUGH_INFORMATION, CONFLICTING)
5. source diversity (number of distinct publisher domains)
6. evidence availability (number of primary verified items above relevance threshold)
7. conflict indicator (internal evidence conflict or classifier vs evidence contradiction)

Output States:
- SUPPORTED
- POTENTIALLY_MISLEADING
- INSUFFICIENT_EVIDENCE
- CONFLICTING_EVIDENCE

Decision Policy Rules:
- If there is no sufficient evidence: do NOT produce a strong verdict (tier capped at LOW/MODERATE).
- If evidence is contradictory: show CONFLICTING_EVIDENCE with conflict penalty applied.
- If classifier confidence is high but evidence is weak: do not display a strong certainty claim.
- If multiple sources independently support a claim: increase evidence strength (STRONG), not automatically the model probability.
- If external evidence contradicts the classifier: verified external evidence overrides standalone model predictions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import settings
from app.schemas.analysis import (
    Assessment,
    ConfidenceBreakdown,
    EvidenceStrength,
)
from app.services.confidence import (
    ConfidenceTier,
    calculate_confidence_breakdown,
    determine_confidence_tier,
    generate_confidence_explanation,
)

logger = logging.getLogger("veritrace.decision_engine")


@dataclass
class DecisionInput:
    """Input signals presented to the decision fusion engine."""

    classifier_prediction: Optional[str] = None
    classifier_probability: Optional[float] = None
    classifier_probabilities: Optional[dict[str, float]] = None
    top_evidence_relevance: float = 0.0
    nli_verdict: Optional[str] = None  # "SUPPORTS", "CONTRADICTS", "INSUFFICIENT", "CONFLICTING"
    source_diversity: int = 0
    evidence_availability: int = 0
    has_conflict: bool = False
    has_strong_contradiction: bool = False
    independent_support_count: int = 0
    independent_contradict_count: int = 0
    mean_source_quality: float = 0.70
    is_non_checkable: bool = False
    claimability_reason: Optional[str] = None


@dataclass
class DecisionOutput:
    """Fused, uncertainty-aware decision result."""

    assessment: Assessment
    confidence: Optional[float]
    confidence_tier: ConfidenceTier
    evidence_strength: Optional[EvidenceStrength]
    confidence_breakdown: Optional[ConfidenceBreakdown]
    confidence_explanation: str
    explanation: str
    decision_policy_trace: dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    """
    Evaluates multi-source verification signals according to a documented decision policy.
    """

    def __init__(
        self,
        min_relevance_threshold: float = settings.evidence_min_relevance_threshold,
        confidence_high_threshold: float = settings.confidence_threshold_high,
        confidence_moderate_threshold: float = settings.confidence_threshold_moderate,
        conflict_penalty_weight: float = settings.conflict_penalty_weight,
        min_sources_for_strong: int = settings.decision_min_independent_sources_for_strong,
    ):
        self.min_relevance_threshold = min_relevance_threshold
        self.confidence_high_threshold = confidence_high_threshold
        self.confidence_moderate_threshold = confidence_moderate_threshold
        self.conflict_penalty_weight = conflict_penalty_weight
        self.min_sources_for_strong = min_sources_for_strong

    def fuse(self, inp: DecisionInput) -> DecisionOutput:
        """
        Execute the decision policy and fuse all input signals into an uncertainty-aware verdict.
        """
        trace: dict[str, Any] = {
            "signals": {
                "classifier_prediction": inp.classifier_prediction,
                "classifier_probability": inp.classifier_probability,
                "top_evidence_relevance": inp.top_evidence_relevance,
                "nli_verdict": inp.nli_verdict,
                "source_diversity": inp.source_diversity,
                "evidence_availability": inp.evidence_availability,
                "has_conflict": inp.has_conflict,
                "has_strong_contradiction": inp.has_strong_contradiction,
                "independent_support_count": inp.independent_support_count,
                "independent_contradict_count": inp.independent_contradict_count,
            },
            "rules_triggered": [],
        }

        # ── 1. Non-Checkable / Subjective Claims ──────────────────────────────
        if inp.is_non_checkable:
            trace["rules_triggered"].append("RULE_NON_CHECKABLE")
            explanation = (
                inp.claimability_reason
                or "The input was identified as a non-checkable statement "
                   "(opinion, subjective expression, or question). "
                   "Verification requires empirical factual assertions."
            )
            confidence_explanation = generate_confidence_explanation(
                model_confidence=inp.classifier_probability,
                evidence_strength=None,
                evidence_count=inp.evidence_availability,
                independent_sources=inp.source_diversity,
                has_conflict=False,
                is_non_checkable=True,
            )
            return DecisionOutput(
                assessment=Assessment.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                confidence_tier=ConfidenceTier.LOW,
                evidence_strength=None,
                confidence_breakdown=calculate_confidence_breakdown(
                    evidence_agreement=0.0,
                    evidence_relevance=0.0,
                    source_quality=0.0,
                    model_confidence=inp.classifier_probability,
                    probabilities=inp.classifier_probabilities,
                ) if inp.classifier_probability is not None else None,
                confidence_explanation=confidence_explanation,
                explanation=explanation,
                decision_policy_trace=trace,
            )

        # ── 2. Determine Evidence Strength ───────────────────────────────────
        evidence_strength: Optional[EvidenceStrength] = None
        has_sufficient_evidence = (
            inp.evidence_availability > 0
            and inp.top_evidence_relevance >= self.min_relevance_threshold
        )

        if has_sufficient_evidence:
            total_verified = (
                inp.independent_support_count + inp.independent_contradict_count
            )
            # Multiple sources independently supporting/corroborating elevates strength to STRONG
            if (
                inp.source_diversity >= self.min_sources_for_strong
                or total_verified >= self.min_sources_for_strong
            ):
                evidence_strength = EvidenceStrength.STRONG
                trace["rules_triggered"].append("RULE_STRONG_EVIDENCE_ELEVATED")
            elif total_verified >= 1 or inp.evidence_availability >= 1:
                evidence_strength = EvidenceStrength.MODERATE
            else:
                evidence_strength = EvidenceStrength.WEAK
        elif inp.evidence_availability > 0:
            evidence_strength = EvidenceStrength.WEAK
            trace["rules_triggered"].append("RULE_WEAK_EVIDENCE_BELOW_RELEVANCE")
        else:
            evidence_strength = None
            trace["rules_triggered"].append("RULE_NO_EVIDENCE")

        # ── 3. Calculate Evidence Agreement and Relevance Signals ─────────────
        total_directional = (
            inp.independent_support_count + inp.independent_contradict_count
        )
        if total_directional > 0:
            evidence_agreement = max(
                inp.independent_support_count, inp.independent_contradict_count
            ) / total_directional
        else:
            evidence_agreement = 0.0

        evidence_relevance = inp.top_evidence_relevance
        source_quality = inp.mean_source_quality
        model_conf = inp.classifier_probability

        # ── 4. Apply Decision Policy to Determine Assessment ─────────────────
        assessment: Assessment
        explanation_parts: list[str] = []

        # Rule A: Conflicting evidence -> CONFLICTING_EVIDENCE
        if inp.has_conflict or (
            inp.independent_support_count > 0 and inp.independent_contradict_count > 0
        ):
            trace["rules_triggered"].append("RULE_CONFLICTING_EVIDENCE")
            assessment = Assessment.CONFLICTING_EVIDENCE
            explanation_parts.append(
                f"Conflicting evidence was found across {inp.source_diversity} independent sources. "
                f"{inp.independent_support_count} source(s) support while "
                f"{inp.independent_contradict_count} source(s) contradict the claim."
            )

        # Rule B: One strong contradiction or dominating contradiction -> POTENTIALLY_MISLEADING
        elif (
            inp.has_strong_contradiction
            or inp.nli_verdict == "CONTRADICTS"
            or (inp.independent_contradict_count > 0 and inp.independent_support_count == 0)
        ):
            trace["rules_triggered"].append("RULE_EVIDENCE_CONTRADICTS")
            assessment = Assessment.POTENTIALLY_MISLEADING
            explanation_parts.append(
                f"Retrieved evidence from {inp.source_diversity} independent source(s) contradicts this claim."
            )
            if inp.classifier_prediction == "SUPPORTED":
                trace["rules_triggered"].append("RULE_EVIDENCE_OVERRIDES_CLASSIFIER")
                explanation_parts.append(
                    "Verified external evidence overrides conflicting standalone model predictions."
                )

        # Rule C: Multiple/Dominating supporting sources -> SUPPORTED
        elif (
            inp.nli_verdict == "SUPPORTS"
            or (inp.independent_support_count > 0 and inp.independent_contradict_count == 0)
        ):
            trace["rules_triggered"].append("RULE_EVIDENCE_SUPPORTS")
            assessment = Assessment.SUPPORTED
            explanation_parts.append(
                f"Retrieved evidence from {inp.source_diversity} independent source(s) corroborates this claim."
            )
            if inp.classifier_prediction == "POTENTIALLY_MISLEADING":
                trace["rules_triggered"].append("RULE_EVIDENCE_OVERRIDES_CLASSIFIER")
                explanation_parts.append(
                    "Verified external evidence overrides conflicting standalone model predictions."
                )

        # Rule D: Standalone classifier prediction when evidence is weak or inconclusive
        elif inp.classifier_prediction in ("SUPPORTED", "POTENTIALLY_MISLEADING"):
            trace["rules_triggered"].append("RULE_CLASSIFIER_DIRECTION_TENTATIVE")
            assessment = (
                Assessment.SUPPORTED
                if inp.classifier_prediction == "SUPPORTED"
                else Assessment.POTENTIALLY_MISLEADING
            )
            explanation_parts.append(
                f"Classified as {inp.classifier_prediction.lower().replace('_', ' ')} based on model inference."
            )
            if not has_sufficient_evidence:
                explanation_parts.append("External evidence corroboration is limited.")

        # Rule E: Fallback to Insufficient Evidence
        else:
            trace["rules_triggered"].append("RULE_NO_SUFFICIENT_EVIDENCE_NO_STRONG_VERDICT")
            assessment = Assessment.INSUFFICIENT_EVIDENCE
            explanation_parts.append(
                "No conclusive external evidence was retrieved to substantiate this claim."
            )

        # ── 5. Compute Fused Confidence ──────────────────────────────────────
        fused_confidence: Optional[float] = None

        if model_conf is not None:
            base_conf = model_conf
            # Conflict penalty
            if inp.has_conflict or assessment == Assessment.CONFLICTING_EVIDENCE:
                base_conf *= (1.0 - self.conflict_penalty_weight)
                trace["rules_triggered"].append("RULE_PENALIZE_CONFLICT_CONFIDENCE")
            elif has_sufficient_evidence and inp.source_diversity >= self.min_sources_for_strong:
                trace["rules_triggered"].append("RULE_STRONG_CORROBORATION")

            fused_confidence = round(max(0.0, min(1.0, base_conf)), 4)

        elif has_sufficient_evidence:
            # Evidence available without ML classifier
            diversity_signal = min(1.0, inp.source_diversity / 2.0)
            base_conf = (
                0.50 * evidence_agreement
                + 0.35 * evidence_relevance
                + 0.15 * diversity_signal
            )
            if inp.has_conflict or assessment == Assessment.CONFLICTING_EVIDENCE:
                base_conf *= (1.0 - self.conflict_penalty_weight)
            fused_confidence = round(max(0.0, min(1.0, base_conf)), 4)

        else:
            # No ML model was executed and no sufficient evidence
            fused_confidence = None
            trace["rules_triggered"].append("RULE_NO_CLASSIFIER_EXECUTED")

        # ── 6. Determine Qualitative Confidence Tier ─────────────────────────
        confidence_tier = determine_confidence_tier(
            confidence=fused_confidence,
            evidence_strength=evidence_strength,
            has_conflict=(inp.has_conflict or assessment == Assessment.CONFLICTING_EVIDENCE),
            has_evidence=has_sufficient_evidence,
        )

        # ── 7. Generate Confidence Explanation ───────────────────────────────
        confidence_explanation = generate_confidence_explanation(
            model_confidence=model_conf,
            evidence_strength=evidence_strength,
            evidence_count=inp.evidence_availability,
            independent_sources=inp.source_diversity,
            has_conflict=(inp.has_conflict or assessment == Assessment.CONFLICTING_EVIDENCE),
            nli_verdict=inp.nli_verdict,
            is_non_checkable=inp.is_non_checkable,
        )

        # ── 8. Assemble Full Explanation ─────────────────────────────────────
        full_explanation = " ".join(explanation_parts) + " " + confidence_explanation

        # ── 9. Assemble Granular Confidence Breakdown ─────────────────────────
        confidence_breakdown = (
            calculate_confidence_breakdown(
                evidence_agreement=evidence_agreement if has_sufficient_evidence else None,
                evidence_relevance=evidence_relevance if has_sufficient_evidence else None,
                source_quality=source_quality if has_sufficient_evidence else None,
                model_confidence=model_conf,
                probabilities=inp.classifier_probabilities,
            )
            if model_conf is not None
            else None
        )

        trace["decision"] = {
            "assessment": assessment.value,
            "confidence": fused_confidence,
            "confidence_tier": confidence_tier.value,
            "evidence_strength": evidence_strength.value if evidence_strength else None,
        }

        return DecisionOutput(
            assessment=assessment,
            confidence=fused_confidence,
            confidence_tier=confidence_tier,
            evidence_strength=evidence_strength,
            confidence_breakdown=confidence_breakdown,
            confidence_explanation=confidence_explanation,
            explanation=full_explanation.strip(),
            decision_policy_trace=trace,
        )


# Global singleton engine
decision_engine = DecisionEngine()


def fuse_decision(inp: DecisionInput) -> DecisionOutput:
    """Convenience function calling the singleton decision engine."""
    return decision_engine.fuse(inp)
