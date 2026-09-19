"""
Claim/evidence verifier and verdict synthesis engine.

Determines for each ranked evidence item:
- relation: SUPPORTS | CONTRADICTS | NOT_ENOUGH_INFORMATION
- nli_score: model confidence of the predicted entailment relation
- relevance_score: composite ranking relevance score
- source_metadata: publisher, domain, verification credentials

Synthesizes claim-level verdict using independent publisher groups to handle:
- no evidence
- conflicting evidence
- weak evidence
- one strong contradiction
- multiple supporting sources
- duplicate/syndicated sources from the same publisher
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.core.config import settings
from app.schemas.analysis import Assessment
from app.schemas.evidence import Relation
from app.services.evidence.base import NormalizedEvidence
from app.services.evidence.nli import NLIModel, NLIOutput, get_nli_model
from app.services.evidence.ranking import RankedEvidence, SourceMetadata, group_and_rank_evidence

logger = logging.getLogger(__name__)


class ClaimEvidenceRelation(str, Enum):
    """Internal relation between a claim and an evidence item."""

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"

    def to_api_relation(self) -> Relation:
        """Map to public API Relation enum for frontend and schema compatibility."""
        if self == ClaimEvidenceRelation.SUPPORTS:
            return Relation.SUPPORT
        elif self == ClaimEvidenceRelation.CONTRADICTS:
            return Relation.CONTRADICT
        return Relation.INSUFFICIENT


@dataclass
class VerifiedEvidenceItem:
    """
    Standard contract for an evaluated evidence item.
    """

    relation: ClaimEvidenceRelation
    nli_score: float
    relevance_score: float
    source_metadata: SourceMetadata
    evidence: NormalizedEvidence
    group_id: str
    is_independent: bool
    nli_output: NLIOutput

    def to_dict(self) -> dict[str, Any]:
        """Contract specified by Step 7 requirements."""
        return {
            "relation": self.relation.value,
            "nli_score": round(self.nli_score, 4),
            "relevance_score": round(self.relevance_score, 4),
            "source_metadata": self.source_metadata.to_dict(),
        }


@dataclass
class VerificationSynthesisResult:
    """
    Synthesized verdict across all candidate evidence.
    """

    assessment: Assessment
    confidence: float
    verified_items: list[VerifiedEvidenceItem]
    independent_support_count: int
    independent_contradict_count: int
    independent_insufficient_count: int
    has_strong_contradiction: bool
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment": self.assessment.value,
            "confidence": round(self.confidence, 4),
            "verified_items": [item.to_dict() for item in self.verified_items],
            "independent_support_count": self.independent_support_count,
            "independent_contradict_count": self.independent_contradict_count,
            "independent_insufficient_count": self.independent_insufficient_count,
            "has_strong_contradiction": self.has_strong_contradiction,
            "explanation": self.explanation,
        }


def classify_relation(
    relevance_score: float,
    nli_out: NLIOutput,
    min_relevance_threshold: Optional[float] = None,
    contradiction_threshold: Optional[float] = None,
    entailment_threshold: Optional[float] = None,
) -> tuple[ClaimEvidenceRelation, float]:
    """
    Determine relationship between claim and evidence based on explicit configuration thresholds.

    - If relevance is below min_relevance_threshold, evidence is deemed irrelevant/weak
      and returns NOT_ENOUGH_INFORMATION.
    - Otherwise checks NLI probabilities against configured thresholds.
    """
    min_rel = (
        min_relevance_threshold
        if min_relevance_threshold is not None
        else settings.evidence_min_relevance_threshold
    )
    contra_thresh = (
        contradiction_threshold
        if contradiction_threshold is not None
        else settings.nli_contradiction_threshold
    )
    entail_thresh = (
        entailment_threshold
        if entailment_threshold is not None
        else settings.nli_entailment_threshold
    )

    # 1. Relevance gate: irrelevant text cannot confirm or refute a claim
    if relevance_score < min_rel:
        return ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION, nli_out.probabilities.get("neutral", 0.70)

    contra_prob = nli_out.probabilities.get("contradiction", 0.0)
    entail_prob = nli_out.probabilities.get("entailment", 0.0)

    # 2. Check contradiction first (claims of misinformation require strong debunking signal)
    if contra_prob >= contra_thresh:
        return ClaimEvidenceRelation.CONTRADICTS, contra_prob

    # 3. Check entailment
    if entail_prob >= entail_thresh:
        return ClaimEvidenceRelation.SUPPORTS, entail_prob

    # 4. Inconclusive / neutral
    return ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION, nli_out.probabilities.get("neutral", 0.60)


def verify_evidence(
    claim: str,
    ranked_candidates: list[RankedEvidence],
    language: str = "en",
    nli_model: Optional[NLIModel] = None,
) -> list[VerifiedEvidenceItem]:
    """
    Run NLI inference and relation classification over ranked evidence items.
    """
    if not ranked_candidates:
        return []

    model = nli_model or get_nli_model()
    verified_list: list[VerifiedEvidenceItem] = []

    for ranked in ranked_candidates:
        # Premise = Evidence title + snippet; Hypothesis = Claim
        premise = f"{ranked.evidence.title}. {ranked.evidence.snippet}"
        hypothesis = claim

        # Run NLI
        nli_out = model.predict(premise=premise, hypothesis=hypothesis, language=language)

        # Classify relation using configured thresholds
        rel, score = classify_relation(
            relevance_score=ranked.relevance_score,
            nli_out=nli_out,
        )

        verified_list.append(
            VerifiedEvidenceItem(
                relation=rel,
                nli_score=score,
                relevance_score=ranked.relevance_score,
                source_metadata=ranked.source_metadata,
                evidence=ranked.evidence,
                group_id=ranked.group_id,
                is_independent=ranked.is_primary_in_group,
                nli_output=nli_out,
            )
        )

    return verified_list


def synthesize_evidence_verdict(
    verified_items: list[VerifiedEvidenceItem],
) -> VerificationSynthesisResult:
    """
    Synthesize claim-level assessment from verified evidence items.

    Enforces source-grouping: duplicate articles from the same publisher group
    (`is_independent=False`) do NOT count as multiple independent sources.
    """
    # ── Case 1: No evidence ──────────────────────────────────────────────
    if not verified_items:
        return VerificationSynthesisResult(
            assessment=Assessment.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            verified_items=[],
            independent_support_count=0,
            independent_contradict_count=0,
            independent_insufficient_count=0,
            has_strong_contradiction=False,
            explanation="No relevant external fact-checks or verifiable citations were found.",
        )

    # Count only independent source groups
    support_items = [v for v in verified_items if v.is_independent and v.relation == ClaimEvidenceRelation.SUPPORTS]
    contradict_items = [v for v in verified_items if v.is_independent and v.relation == ClaimEvidenceRelation.CONTRADICTS]
    insufficient_items = [v for v in verified_items if v.is_independent and v.relation == ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION]

    num_support = len(support_items)
    num_contradict = len(contradict_items)
    num_insufficient = len(insufficient_items)

    # Check for strong contradiction:
    # A verified fact-checker or official source contradicting with high NLI confidence
    has_strong_contradiction = any(
        c.source_metadata.is_verified_fact_checker and c.nli_score >= settings.nli_contradiction_threshold
        for c in contradict_items
    )

    # ── Case 2: Conflicting evidence ─────────────────────────────────────
    if num_support >= 1 and num_contradict >= 1:
        avg_conf = (
            sum(c.nli_score for c in support_items + contradict_items)
            / (num_support + num_contradict)
        )
        return VerificationSynthesisResult(
            assessment=Assessment.CONFLICTING_EVIDENCE,
            confidence=avg_conf,
            verified_items=verified_items,
            independent_support_count=num_support,
            independent_contradict_count=num_contradict,
            independent_insufficient_count=num_insufficient,
            has_strong_contradiction=has_strong_contradiction,
            explanation=(
                f"Conflicting evidence found: {num_support} independent source(s) support "
                f"while {num_contradict} source(s) contradict this claim."
            ),
        )

    # ── Case 3: Contradiction (One strong or multiple contradictions) ─────
    if num_contradict >= 1:
        # Confidence weighted by fact-checker status and top NLI score
        top_contra_score = max(c.nli_score for c in contradict_items)
        confidence = min(0.96, top_contra_score + (0.05 if has_strong_contradiction else 0.0))
        sources_str = ", ".join(c.source_metadata.publisher for c in contradict_items[:2])
        return VerificationSynthesisResult(
            assessment=Assessment.POTENTIALLY_MISLEADING,
            confidence=confidence,
            verified_items=verified_items,
            independent_support_count=num_support,
            independent_contradict_count=num_contradict,
            independent_insufficient_count=num_insufficient,
            has_strong_contradiction=has_strong_contradiction,
            explanation=(
                f"Contradicted by {num_contradict} independent source(s) ({sources_str}). "
                "The claim has been refuted or identified as misleading."
            ),
        )

    # ── Case 4: Multiple or single supporting sources ─────────────────────
    if num_support >= 1:
        top_support_score = max(s.nli_score for s in support_items)
        # Higher confidence when confirmed by multiple independent publishers
        conf_boost = 0.08 if num_support >= 2 else 0.0
        confidence = min(0.95, top_support_score + conf_boost)
        sources_str = ", ".join(s.source_metadata.publisher for s in support_items[:2])
        return VerificationSynthesisResult(
            assessment=Assessment.SUPPORTED,
            confidence=confidence,
            verified_items=verified_items,
            independent_support_count=num_support,
            independent_contradict_count=num_contradict,
            independent_insufficient_count=num_insufficient,
            has_strong_contradiction=False,
            explanation=(
                f"Verified by {num_support} independent source(s) ({sources_str}). "
                "Available factual evidence supports this claim."
            ),
        )

    # ── Case 5: All evidence is neutral / weak / inconclusive ─────────────
    return VerificationSynthesisResult(
        assessment=Assessment.INSUFFICIENT_EVIDENCE,
        confidence=0.0,
        verified_items=verified_items,
        independent_support_count=0,
        independent_contradict_count=0,
        independent_insufficient_count=num_insufficient,
        has_strong_contradiction=False,
        explanation=(
            f"Found {len(verified_items)} candidate source(s), but none provided conclusive "
            "factual confirmation or refutation."
        ),
    )


def rank_and_verify_evidence(
    claim: str,
    candidates: list[NormalizedEvidence],
    language: str = "en",
    top_k: Optional[int] = None,
    nli_model: Optional[NLIModel] = None,
) -> tuple[list[VerifiedEvidenceItem], VerificationSynthesisResult]:
    """
    End-to-end evidence processing:
    1. Group and rank candidates.
    2. Run NLI entailment classification.
    3. Synthesize claim verification assessment.
    """
    ranked = group_and_rank_evidence(
        claim=claim,
        candidates=candidates,
        language=language,
        top_k=top_k,
    )

    verified_items = verify_evidence(
        claim=claim,
        ranked_candidates=ranked,
        language=language,
        nli_model=nli_model,
    )

    synthesis = synthesize_evidence_verdict(verified_items)

    return verified_items, synthesis
