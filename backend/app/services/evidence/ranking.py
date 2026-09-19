"""
Evidence ranking and source-grouping module.

Ranks candidate evidence items using multiple explainable signals:
1. Semantic relevance (character + word n-gram TF-IDF cosine similarity)
2. Claim/evidence lexical similarity
3. Source metadata (domain, publisher, verified status — kept separate from relevance)
4. Recency (temporal decay where published date is available)
5. Exact entity and numerical/topic overlap

Implements source-grouping logic to ensure duplicate or syndicated articles
from the same publisher/domain are not counted as multiple independent sources.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.services.evidence.base import NormalizedEvidence

logger = logging.getLogger(__name__)

# Known verified fact-checking publishers & domains (e.g., IFCN signatories / established bodies)
KNOWN_FACT_CHECKERS: set[str] = {
    "boomlive.in",
    "vishvasnews.com",
    "factly.in",
    "altnews.in",
    "thequint.com",
    "indiatoday.in",
    "politifact.com",
    "snopes.com",
    "factcheck.org",
    "fullfact.org",
    "reuters.com",
    "afp.com",
    "apnews.com",
}


@dataclass
class SourceMetadata:
    """
    Structured metadata describing the evidence source.

    Separates publisher identity, credentials, and verification status
    from semantic relevance calculations (avoids arbitrary hardcoded trust scores).
    """

    publisher: str
    domain: str
    source_type: str  # "fact_check" | "news" | "official" | "local_fixture" | "unknown"
    is_verified_fact_checker: bool
    external_rating: Optional[str] = None
    published_at: Optional[datetime] = None
    claimant: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "publisher": self.publisher,
            "domain": self.domain,
            "source_type": self.source_type,
            "is_verified_fact_checker": self.is_verified_fact_checker,
            "external_rating": self.external_rating,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "claimant": self.claimant,
            "extra": self.extra,
        }


@dataclass
class RankedEvidence:
    """
    Candidate evidence augmented with granular ranking signals and grouping metadata.
    """

    evidence: NormalizedEvidence
    semantic_similarity: float
    entity_match_score: float
    recency_score: float
    relevance_score: float
    source_metadata: SourceMetadata
    group_id: str
    is_primary_in_group: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_dict(),
            "semantic_similarity": round(self.semantic_similarity, 4),
            "entity_match_score": round(self.entity_match_score, 4),
            "recency_score": round(self.recency_score, 4),
            "relevance_score": round(self.relevance_score, 4),
            "source_metadata": self.source_metadata.to_dict(),
            "group_id": self.group_id,
            "is_primary_in_group": self.is_primary_in_group,
        }


def extract_domain(url: str) -> str:
    """Extract clean domain from a URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]
        # Remove common www. prefix
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc or "unknown"
    except Exception:
        return "unknown"


def extract_source_metadata(evidence: NormalizedEvidence) -> SourceMetadata:
    """Extract structured source metadata without conflating with relevance."""
    domain = extract_domain(evidence.url)
    publisher = evidence.source_name.strip() or domain

    # Parse published_at date if present
    pub_dt: Optional[datetime] = None
    if evidence.published_at:
        try:
            pub_dt = datetime.fromisoformat(evidence.published_at.replace("Z", "+00:00"))
        except Exception:
            pub_dt = None

    # Check if domain or publisher is a recognized fact checker
    is_fact_checker = (
        evidence.source_type == "fact_check"
        or domain in KNOWN_FACT_CHECKERS
        or any(fc in domain for fc in KNOWN_FACT_CHECKERS)
        or "fact" in publisher.lower()
        or "check" in publisher.lower()
        or "news" in publisher.lower()
        or evidence.metadata.get("is_offline_fixture", False)
    )

    return SourceMetadata(
        publisher=publisher,
        domain=domain,
        source_type=evidence.source_type or ("fact_check" if is_fact_checker else "unknown"),
        is_verified_fact_checker=is_fact_checker,
        external_rating=evidence.external_rating,
        published_at=pub_dt,
        claimant=evidence.metadata.get("claimant"),
        extra={k: v for k, v in evidence.metadata.items() if k != "claimant"},
    )


def compute_semantic_similarity(claim: str, text: str, language: str = "en") -> float:
    """
    Compute cosine similarity between claim and evidence text using character & word n-grams.

    Handles space-delimited English as well as Hindi and Telugu scripts seamlessly.
    """
    if not claim.strip() or not text.strip():
        return 0.0

    try:
        # Multilingual TF-IDF: word 1-2 grams and char 3-5 grams to capture morphology
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=1,
            lowercase=True,
        )
        tfidf_matrix = vectorizer.fit_transform([claim, text])
        sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        return max(0.0, min(1.0, sim))
    except Exception as e:
        logger.debug("TF-IDF similarity calculation failed: %s", e)
        # Fallback to token Jaccard similarity
        c_tokens = set(re.findall(r"\w+", claim.lower()))
        t_tokens = set(re.findall(r"\w+", text.lower()))
        if not c_tokens or not t_tokens:
            return 0.0
        return len(c_tokens & t_tokens) / len(c_tokens | t_tokens)


def compute_entity_overlap(claim: str, text: str) -> float:
    """
    Compute overlap ratio of key entities, numbers, dates, and capitalized nouns.
    """
    if not claim or not text:
        return 0.0

    # Extract numbers, percentages, currency, dates, and alphanumeric tokens
    number_re = re.compile(r"\b\d+(?:[\.,]\d+)?\b|\b(?:₹|\$|€|rs\.?)\s*\d+\b", re.IGNORECASE)
    claim_nums = set(number_re.findall(claim.lower()))
    text_nums = set(number_re.findall(text.lower()))

    # Extract distinct keywords (length >= 3)
    word_re = re.compile(r"[\w\u0900-\u097F\u0C00-\u0C7F]{3,}")
    claim_words = set(word_re.findall(claim.lower()))
    text_words = set(word_re.findall(text.lower()))

    if not claim_words:
        return 0.0

    word_overlap = len(claim_words & text_words) / len(claim_words)

    # If claim contained specific numbers, verify if they are present in evidence
    num_overlap = 1.0
    if claim_nums:
        num_overlap = len(claim_nums & text_nums) / len(claim_nums)

    # 70% word overlap + 30% number overlap
    return max(0.0, min(1.0, 0.70 * word_overlap + 0.30 * num_overlap))


def compute_recency_score(published_at: Optional[datetime]) -> float:
    """
    Calculate recency score with half-life decay.

    - Recent within 6 months: 1.0
    - Within 1 year: ~0.9
    - Within 3 years: ~0.7
    - Within 5 years: ~0.5
    - If publication date is missing: neutral default of 0.60
    """
    if not published_at:
        return 0.60

    try:
        now = datetime.now(timezone.utc)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        delta_days = max(0, (now - published_at).days)
        # Half life of 730 days (~2 years)
        decay = math.exp(-0.693 * delta_days / 730.0)
        return max(0.20, min(1.0, decay))
    except Exception:
        return 0.60


def compute_composite_relevance(
    semantic_sim: float,
    entity_match: float,
    recency: float,
) -> float:
    """
    Compute composite relevance score using configurable weights.
    """
    w_sim = settings.ranking_weight_similarity
    w_ent = settings.ranking_weight_entity
    w_rec = settings.ranking_weight_recency

    total_w = w_sim + w_ent + w_rec
    if total_w <= 0:
        total_w = 1.0

    score = (w_sim * semantic_sim + w_ent * entity_match + w_rec * recency) / total_w
    return max(0.0, min(1.0, score))


def group_and_rank_evidence(
    claim: str,
    candidates: list[NormalizedEvidence],
    language: str = "en",
    top_k: Optional[int] = None,
) -> list[RankedEvidence]:
    """
    Rank candidate evidence items and group by source publisher/domain.

    - Computes similarity, entity match, recency, and composite relevance.
    - Groups items by publisher/domain key.
    - Selects the highest-scoring candidate as the primary representative for that publisher.
    - Subsequent duplicates or syndicated copies from the same publisher are flagged
      `is_primary_in_group = False` so they do not count as independent sources.
    - Returns top-K candidates ordered by relevance score.
    """
    if not candidates:
        return []

    limit = top_k if top_k is not None else settings.evidence_top_k
    ranked_list: list[RankedEvidence] = []

    for item in candidates:
        combined_text = f"{item.title} {item.snippet}"
        source_meta = extract_source_metadata(item)

        # 1. Semantic relevance
        sim_score = compute_semantic_similarity(claim, combined_text, language=language)

        # 2. Entity & topic match
        ent_score = compute_entity_overlap(claim, combined_text)

        # 3. Recency score
        rec_score = compute_recency_score(source_meta.published_at)

        # 4. Composite relevance score
        rel_score = compute_composite_relevance(sim_score, ent_score, rec_score)

        # Group ID based on normalized domain or publisher
        group_key = source_meta.domain if source_meta.domain != "unknown" else source_meta.publisher.lower()
        group_key = re.sub(r"[^\w\.]", "", group_key)

        ranked_list.append(
            RankedEvidence(
                evidence=item,
                semantic_similarity=sim_score,
                entity_match_score=ent_score,
                recency_score=rec_score,
                relevance_score=rel_score,
                source_metadata=source_meta,
                group_id=group_key,
                is_primary_in_group=True,
            )
        )

    # Sort descending by composite relevance score
    ranked_list.sort(key=lambda r: r.relevance_score, reverse=True)

    # Source-grouping pass: flag secondary articles from already-seen publisher groups
    seen_groups: set[str] = set()
    for ranked_item in ranked_list:
        gid = ranked_item.group_id
        if gid in seen_groups:
            ranked_item.is_primary_in_group = False
        else:
            seen_groups.add(gid)
            ranked_item.is_primary_in_group = True

    return ranked_list[:limit]
