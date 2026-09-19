"""
Evidence retrieval service — orchestrates providers, TTL caching, and security checks.

Single entry point for the analysis service to retrieve factual evidence.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Optional

from app.core.config import settings
from app.schemas.evidence import EvidenceItem, Relation
from app.services.evidence.base import (
    EvidenceProvider,
    EvidenceRetrievalResult,
    NormalizedEvidence,
    sanitize_evidence_text,
)
from app.services.evidence.google_factcheck import GoogleFactCheckProvider
from app.services.evidence.local_provider import LocalEvidenceProvider

logger = logging.getLogger(__name__)


class EvidenceCache:
    """
    Thread-safe in-memory cache with Time-To-Live (TTL) expiration.

    Reduces outbound API calls, guards against rate limits, and accelerates
    repeated claim verifications.
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self._cache: dict[str, tuple[EvidenceRetrievalResult, float]] = {}
        self._ttl = default_ttl_seconds
        self._lock = threading.Lock()

    def _make_key(self, query: str, language: str, page_token: Optional[str]) -> str:
        raw = f"{query.strip().lower()}:{language.strip().lower()}:{page_token or ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(
        self, query: str, language: str, page_token: Optional[str] = None
    ) -> Optional[EvidenceRetrievalResult]:
        key = self._make_key(query, language, page_token)
        now = time.monotonic()
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            result, timestamp = entry
            if now - timestamp > self._ttl:
                del self._cache[key]
                return None
            # Return copy with cached=True
            return EvidenceRetrievalResult(
                items=result.items,
                provider=result.provider,
                query=result.query,
                language=result.language,
                cached=True,
                next_page_token=result.next_page_token,
                total_results=result.total_results,
            )

    def set(
        self,
        query: str,
        language: str,
        result: EvidenceRetrievalResult,
        page_token: Optional[str] = None,
    ) -> None:
        if result.error or not result.items:
            # Don't cache errors or empty results indefinitely
            return
        key = self._make_key(query, language, page_token)
        with self._lock:
            self._cache[key] = (result, time.monotonic())

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Global cache instance
evidence_cache = EvidenceCache(default_ttl_seconds=settings.evidence_cache_ttl_seconds)


def map_external_rating_to_relation(rating: Optional[str]) -> Relation:
    """
    Map an external fact-checker rating to an Evidence Relation (SUPPORT/CONTRADICT/INSUFFICIENT).

    Note: This categorizes how the evidence relates to the rumor/claim;
    it does NOT set the overall VeriTrace application assessment.
    """
    if not rating:
        return Relation.INSUFFICIENT

    r = rating.lower().strip()

    # Contradicting indicators (claim was rated false/misleading)
    contradict_signals = [
        "false", "fake", "incorrect", "misleading", "pants on fire",
        "debunked", "untrue", "झूठा", "తప్పు", "गलत", "hoax",
    ]
    if any(sig in r for sig in contradict_signals):
        return Relation.CONTRADICT

    # Supporting indicators (claim was rated true/correct)
    support_signals = [
        "true", "correct", "accurate", "verified", "supported", "सही", "నిజం",
    ]
    if any(sig in r for sig in support_signals):
        return Relation.SUPPORT

    return Relation.INSUFFICIENT


def normalize_to_evidence_item(evidence: NormalizedEvidence, index: int) -> EvidenceItem:
    """Map a NormalizedEvidence dataclass to an API EvidenceItem schema."""
    relation = map_external_rating_to_relation(evidence.external_rating)

    # Base relevance score on provider type
    relevance = 0.88 if evidence.source_type == "fact_check" else 0.75
    source_quality = 0.90 if evidence.source_type == "fact_check" else 0.70

    return EvidenceItem(
        id=f"ev-{index + 1:03d}",
        title=evidence.title,
        source=evidence.source_name,
        url=evidence.url,
        snippet=evidence.snippet,
        relevance_score=relevance,
        source_quality=source_quality,
        relation=relation,
    )


def get_active_provider(force_provider: Optional[str] = None) -> EvidenceProvider:
    """Resolve the active evidence provider based on settings and environment."""
    provider_type = force_provider or settings.evidence_provider

    if provider_type == "local":
        return LocalEvidenceProvider(allow_in_production=False)

    # Default: Google Fact Check
    google_provider = GoogleFactCheckProvider(
        api_key=settings.google_factcheck_api_key,
        timeout=settings.evidence_timeout_seconds,
        max_retries=settings.evidence_max_retries,
    )

    if google_provider.is_available:
        return google_provider

    # If Google API key is missing:
    if settings.evidence_enable_offline_fallback or settings.is_development:
        logger.warning(
            "GOOGLE_FACTCHECK_API_KEY missing — falling back to LocalEvidenceProvider (DEMO / OFFLINE MODE)"
        )
        return LocalEvidenceProvider(allow_in_production=settings.evidence_enable_offline_fallback)

    # In strict production without key, return unconfigured google provider to fail honestly
    return google_provider


async def retrieve_evidence(
    query: str,
    language: str = "en",
    page_size: int = 10,
    page_token: Optional[str] = None,
    force_provider: Optional[str] = None,
    skip_cache: bool = False,
) -> EvidenceRetrievalResult:
    """
    Retrieve external evidence for a claim.

    Checks cache, selects provider, queries provider, and sanitizes output.
    """
    cleaned_query = sanitize_evidence_text(query, max_length=300)
    if not cleaned_query:
        return EvidenceRetrievalResult(
            items=[],
            provider="none",
            query=query,
            language=language,
        )

    # Check cache
    if not skip_cache:
        cached = evidence_cache.get(cleaned_query, language, page_token)
        if cached is not None:
            logger.info("Evidence cache HIT for query '%s' (lang=%s)", cleaned_query[:40], language)
            return cached

    # Run retrieval
    provider = get_active_provider(force_provider=force_provider)
    logger.info(
        "Retrieving evidence for query '%s' via provider '%s' (lang=%s)",
        cleaned_query[:40], provider.name, language,
    )

    result = provider.search(
        query=cleaned_query,
        language=language,
        page_size=page_size,
        page_token=page_token,
    )

    # Cache successful results
    if not skip_cache and not result.error and result.items:
        evidence_cache.set(cleaned_query, language, result, page_token)

    return result
