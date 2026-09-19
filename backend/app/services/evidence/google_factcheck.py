"""
Google Fact Check Tools API client.

Searches published claim reviews from independent fact-checking organizations.
Note: This is specifically a fact-check search service, NOT a general web search API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.services.evidence.base import (
    EvidenceProvider,
    EvidenceRetrievalResult,
    NormalizedEvidence,
    sanitize_evidence_text,
)

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckProvider:
    """
    Client for Google Fact Check Tools API claim search endpoint.

    Queries professional fact-checking organizations (e.g., BoomLive, Vishvas News,
    FactCheck.org, PolitiFact) and returns structured claim reviews.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 2,
    ):
        self._api_key = api_key or settings.google_factcheck_api_key
        self._timeout = timeout
        self._max_retries = max_retries

    @property
    def name(self) -> str:
        return "google_factcheck"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def search(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> EvidenceRetrievalResult:
        """
        Search for fact checks matching the claim query.

        Preserves external ratings without asserting them as VeriTrace's final verdict.
        """
        if not self.is_available:
            logger.warning("Google Fact Check API key is not configured")
            return EvidenceRetrievalResult(
                items=[],
                provider=self.name,
                query=query,
                language=language,
                error="GOOGLE_FACTCHECK_API_KEY is not configured",
            )

        if not query or not query.strip():
            return EvidenceRetrievalResult(
                items=[],
                provider=self.name,
                query=query,
                language=language,
            )

        params: dict[str, Any] = {
            "query": query.strip(),
            "languageCode": language.lower(),
            "pageSize": min(page_size, 20),
            "key": self._api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        attempts = 0
        backoff = 1.0

        while attempts <= self._max_retries:
            attempts += 1
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.get(API_ENDPOINT, params=params)

                # Handle specific HTTP error status codes
                if response.status_code == 400:
                    logger.error("Google Fact Check API bad request (invalid query or params): %s", response.text)
                    return EvidenceRetrievalResult(
                        items=[],
                        provider=self.name,
                        query=query,
                        language=language,
                        error=f"Invalid request parameters: {response.text[:200]}",
                    )
                elif response.status_code in (401, 403):
                    logger.error("Google Fact Check API authentication failed (HTTP %d)", response.status_code)
                    return EvidenceRetrievalResult(
                        items=[],
                        provider=self.name,
                        query=query,
                        language=language,
                        error=f"Authentication failed (HTTP {response.status_code}): invalid or unauthorized GOOGLE_FACTCHECK_API_KEY",
                    )
                elif response.status_code == 429:
                    logger.warning("Google Fact Check API rate limit hit (429), attempt %d/%d", attempts, self._max_retries + 1)
                    if attempts <= self._max_retries:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    return EvidenceRetrievalResult(
                        items=[],
                        provider=self.name,
                        query=query,
                        language=language,
                        error="Rate limit exceeded: Google Fact Check API quota reached",
                    )
                elif response.status_code >= 500:
                    logger.warning("Google Fact Check server error %d, attempt %d/%d", response.status_code, attempts, self._max_retries + 1)
                    if attempts <= self._max_retries:
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    return EvidenceRetrievalResult(
                        items=[],
                        provider=self.name,
                        query=query,
                        language=language,
                        error=f"Google Fact Check API server error: {response.status_code}",
                    )

                try:
                    data = response.json()
                except Exception as json_err:
                    logger.error("Malformed JSON response from Google Fact Check API: %s", json_err)
                    return EvidenceRetrievalResult(
                        items=[],
                        provider=self.name,
                        query=query,
                        language=language,
                        error=f"Malformed JSON response from API: {json_err}",
                    )

                return self._parse_response(data, query, language)

            except httpx.TimeoutException:
                logger.warning("Google Fact Check request timed out, attempt %d/%d", attempts, self._max_retries + 1)
                if attempts <= self._max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return EvidenceRetrievalResult(
                    items=[],
                    provider=self.name,
                    query=query,
                    language=language,
                    error=f"Request timed out after {self._timeout}s",
                )
            except Exception as e:
                logger.exception("Unexpected error contacting Google Fact Check API: %s", e)
                return EvidenceRetrievalResult(
                    items=[],
                    provider=self.name,
                    query=query,
                    language=language,
                    error=str(e),
                )

        return EvidenceRetrievalResult(
            items=[],
            provider=self.name,
            query=query,
            language=language,
            error="Failed to retrieve evidence after retries",
        )

    def _parse_response(
        self,
        data: dict[str, Any],
        query: str,
        language: str,
    ) -> EvidenceRetrievalResult:
        """Parse raw Google Fact Check Tools API response into NormalizedEvidence list."""
        if not isinstance(data, dict):
            logger.error("Malformed API response: expected JSON object, got %s", type(data))
            return EvidenceRetrievalResult(
                items=[],
                provider=self.name,
                query=query,
                language=language,
                error="Malformed response from Google Fact Check API",
            )

        claims = data.get("claims", [])
        next_page_token = data.get("nextPageToken")
        items: list[NormalizedEvidence] = []
        seen_urls: set[str] = set()

        now_iso = datetime.now(timezone.utc).isoformat()

        for claim in claims:
            if not isinstance(claim, dict):
                continue

            claim_text = sanitize_evidence_text(claim.get("text", ""))
            claimant = sanitize_evidence_text(claim.get("claimant", ""))
            claim_date = claim.get("claimDate")

            reviews = claim.get("claimReview", [])
            for review in reviews:
                if not isinstance(review, dict):
                    continue

                raw_url = review.get("url", "")
                if not raw_url:
                    continue

                normalized_url = raw_url.strip().lower()
                if normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)

                publisher_info = review.get("publisher", {})
                source_name = (
                    publisher_info.get("name")
                    or publisher_info.get("site")
                    or "Independent Fact Checker"
                )

                raw_title = review.get("title") or claim_text or "Fact Check Review"
                title = sanitize_evidence_text(raw_title, max_length=250)

                # Snippet: combination of claim text and evaluation context
                snippet_text = claim_text
                if claimant:
                    snippet_text = f"Claim by {claimant}: {claim_text}"
                snippet = sanitize_evidence_text(snippet_text, max_length=1000)

                published_at = review.get("reviewDate") or claim_date
                external_rating = review.get("textualRating")

                evidence = NormalizedEvidence(
                    source_name=source_name,
                    title=title,
                    url=raw_url.strip(),
                    snippet=snippet,
                    published_at=published_at,
                    retrieved_at=now_iso,
                    source_type="fact_check",
                    external_rating=external_rating,
                    metadata={
                        "claimant": claimant or None,
                        "claim_date": claim_date,
                        "publisher_site": publisher_info.get("site"),
                        "review_language": review.get("languageCode", language),
                    },
                )
                items.append(evidence)

        return EvidenceRetrievalResult(
            items=items,
            provider=self.name,
            query=query,
            language=language,
            cached=False,
            next_page_token=next_page_token,
            total_results=len(items),
        )
