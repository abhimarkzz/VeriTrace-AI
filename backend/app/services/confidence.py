"""
Uncertainty-aware confidence engine for VeriTrace AI.

Encodes the core safety principle:
    MODEL CONFIDENCE ≠ EVIDENCE STRENGTH ≠ TRUTH PROBABILITY

Responsibilities:
1. Assign qualitative confidence tiers: HIGH CONFIDENCE, MODERATE CONFIDENCE, LOW CONFIDENCE.
2. Ensure high model confidence without evidence NEVER produces a high certainty tier.
3. Penalize confidence when evidence conflicts or when sources are sparse.
4. Generate transparent confidence explanations communicating epistemic uncertainty.
5. Compute granular confidence sub-scores for breakdown inspection.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from app.core.config import settings
from app.schemas.analysis import ConfidenceBreakdown, EvidenceStrength


class ConfidenceTier(str, Enum):
    """Qualitative uncertainty tiers communicating evidence and model backing."""

    HIGH = "HIGH CONFIDENCE"
    MODERATE = "MODERATE CONFIDENCE"
    LOW = "LOW CONFIDENCE"


def determine_confidence_tier(
    confidence: Optional[float],
    evidence_strength: Optional[EvidenceStrength],
    has_conflict: bool = False,
    has_evidence: bool = True,
) -> ConfidenceTier:
    """
    Determine the qualitative confidence tier based on fused score, evidence strength,
    and conflict status.

    Safety Bounds:
    - If there is no evidence, the tier CANNOT be HIGH.
    - If evidence is conflicting, the tier CANNOT be HIGH.
    - If evidence is WEAK, the tier CANNOT be HIGH (caps at MODERATE or LOW).
    - HIGH CONFIDENCE requires confidence >= confidence_threshold_high AND
      evidence_strength in (MODERATE, STRONG) AND no conflict.
    """
    if confidence is None:
        return ConfidenceTier.LOW

    if not has_evidence:
        return ConfidenceTier.LOW

    if has_conflict:
        # Conflicting evidence must never be presented with high confidence
        return (
            ConfidenceTier.MODERATE
            if confidence >= settings.confidence_threshold_moderate
            else ConfidenceTier.LOW
        )

    if evidence_strength == EvidenceStrength.WEAK:
        # Weak evidence caps confidence tier at MODERATE
        return (
            ConfidenceTier.MODERATE
            if confidence >= settings.confidence_threshold_moderate
            else ConfidenceTier.LOW
        )

    # For MODERATE or STRONG evidence without conflicts:
    if (
        confidence >= settings.confidence_threshold_high
        and evidence_strength in (EvidenceStrength.MODERATE, EvidenceStrength.STRONG)
    ):
        return ConfidenceTier.HIGH
    elif confidence >= settings.confidence_threshold_moderate:
        return ConfidenceTier.MODERATE
    else:
        return ConfidenceTier.LOW


def generate_confidence_explanation(
    model_confidence: Optional[float],
    evidence_strength: Optional[EvidenceStrength],
    evidence_count: int,
    independent_sources: int,
    has_conflict: bool,
    nli_verdict: Optional[str] = None,
    is_non_checkable: bool = False,
) -> str:
    """
    Generate an honest, uncertainty-aware explanation of the confidence level.

    Never claims "95% chance this statement is true". Clearly details the interplay
    between model confidence and retrieved independent evidence.
    """
    if is_non_checkable:
        return (
            "Low confidence: Statement contains subjective opinion, prediction, or "
            "non-verifiable assertions rather than an empirical claim."
        )

    if evidence_count == 0:
        if model_confidence is not None and model_confidence >= settings.confidence_threshold_high:
            return (
                "High model confidence, but no independent evidence was retrieved. "
                "Verification requires verifiable external sources; certainty is restricted."
            )
        return (
            "No external evidence was retrieved to substantiate this claim. "
            "The assessment is inconclusive with low confidence."
        )

    if has_conflict:
        return (
            f"Conflicting evidence was retrieved across {independent_sources} independent sources. "
            "Confidence is penalized due to contradictory verification signals."
        )

    if evidence_strength == EvidenceStrength.WEAK:
        if model_confidence is not None and model_confidence >= settings.confidence_threshold_high:
            return (
                "High model confidence, but only limited independent evidence was retrieved. "
                "External backing is weak, so overall certainty is moderated."
            )
        return (
            "Evidence retrieved has limited relevance or low source corroboration; "
            "assessment confidence remains moderate to low."
        )

    if evidence_strength == EvidenceStrength.STRONG:
        if independent_sources >= 2:
            return (
                f"High confidence supported by {independent_sources} independent sources "
                "with strong semantic agreement and verified corroboration."
            )
        return (
            "Strong verification signal from an authoritative fact-checking source "
            "with high semantic relevance."
        )

    # Moderate evidence case
    if model_confidence is not None and model_confidence < settings.confidence_threshold_moderate:
        return (
            "External fact-check evidence provides moderate independent corroboration "
            "despite lower standalone model certainty."
        )

    return (
        f"Assessment is supported by {independent_sources} independent source(s) "
        "with moderate semantic agreement."
    )


def calculate_confidence_breakdown(
    evidence_agreement: Optional[float] = None,
    evidence_relevance: Optional[float] = None,
    source_quality: Optional[float] = None,
    model_confidence: Optional[float] = None,
    probabilities: Optional[dict[str, float]] = None,
) -> ConfidenceBreakdown:
    """
    Construct a ConfidenceBreakdown instance, rounding all scores to 4 decimal places.
    """
    return ConfidenceBreakdown(
        evidence_agreement=round(evidence_agreement, 4) if evidence_agreement is not None else None,
        evidence_relevance=round(evidence_relevance, 4) if evidence_relevance is not None else None,
        source_quality=round(source_quality, 4) if source_quality is not None else None,
        model_confidence=round(model_confidence, 4) if model_confidence is not None else None,
        probabilities=probabilities,
    )
