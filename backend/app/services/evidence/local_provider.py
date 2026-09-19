"""
Local evidence provider containing verified test fixtures for offline development.

All fixtures are explicitly marked as:
DEMO / OFFLINE EVIDENCE

This provider is disabled in production mode to prevent silent fallback to mock data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.evidence.base import (
    EvidenceProvider,
    EvidenceRetrievalResult,
    NormalizedEvidence,
)

logger = logging.getLogger(__name__)

# Verified test fixtures for offline development & testing
OFFLINE_FIXTURES: list[dict] = [
    # ── UPI Ban Rumor (English) ──────────────────────────────────────────
    {
        "keywords": ["upi", "banned", "shut down", "charge", "transactions", "npci"],
        "languages": ["en", "auto"],
        "source_name": "NPCI Press Bureau",
        "title": "Clarification on UPI Transactions: No Ban or General Charges Announced",
        "url": "https://www.npci.org.in/what-we-do/upi/press-releases/clarification-upi-charges",
        "snippet": "NPCI clarifies that Unified Payments Interface (UPI) services continue uninterrupted. Reports of bans or universal transactional fees for end users are unfounded.",
        "published_at": "2024-01-05T10:00:00Z",
        "external_rating": "False",
        "claimant": "Viral WhatsApp Forward",
    },
    {
        "keywords": ["upi", "banned", "shut down", "charge", "fees"],
        "languages": ["en", "auto"],
        "source_name": "Boom Live Fact Check",
        "title": "Viral Post Falsely Claims UPI Payments To Be Shut Down Nationwide",
        "url": "https://www.boomlive.in/fact-check/upi-payments-ban-viral-claim-fact-check-24156",
        "snippet": "Our verification found no government or banking circular ordering a shutdown of the UPI network. NPCI confirmed standard user payments remain free and operational.",
        "published_at": "2024-01-06T14:30:00Z",
        "external_rating": "False",
        "claimant": "Social Media Posts",
    },

    # ── UPI Ban Rumor (Hindi) ────────────────────────────────────────────
    {
        "keywords": ["upi", "बंद", "शुल्क", "एनपीसीआई", "लेनदेन"],
        "languages": ["hi", "auto"],
        "source_name": "विश्वास न्यूज (Vishvas News)",
        "title": "पड़ताल: क्या सरकार ने यूपीआई लेनदेन पर रोक लगा दी है? जानें वायरल दावे का सच",
        "url": "https://www.vishvasnews.com/hindi/fact-check/fact-check-upi-transaction-ban-claim-is-false/",
        "snippet": "विश्वास न्यूज की पड़ताल में यूपीआई बंद होने का दावा पूरी तरह भ्रामक निकला। एनपीसीआई ने स्पष्ट किया है कि सामान्य ग्राहकों के लिए यूपीआई सेवाएं सामान्य रूप से जारी हैं।",
        "published_at": "2024-01-07T11:00:00Z",
        "external_rating": "झूठा (False)",
        "claimant": "सोशल मीडिया फॉरवर्ड",
    },

    # ── UPI Ban Rumor (Telugu) ───────────────────────────────────────────
    {
        "keywords": ["upi", "నిలిపివేత", "రుసుము", "లావాదేవీలు", "రద్దు"],
        "languages": ["te", "auto"],
        "source_name": "ఫ్యాక్ట్ లీ (Factly Telugu)",
        "title": "యూపీఐ లావాదేవీలు నిలిపివేస్తున్నట్లు వస్తున్న వార్తల్లో నిజం ఎంత?",
        "url": "https://telugu.factly.in/fact-check-upi-services-ban-claims-debunked/",
        "snippet": "దేశవ్యాప్తంగా యూపీఐ చెల్లింపులు నిలిపివేస్తున్నట్లు జరుగుతున్న ప్రచారంలో నిజం లేదు. ఎన్‌పీసీఐ అధికారులు ఈ ప్రచారాన్ని ఖండించారు.",
        "published_at": "2024-01-08T09:15:00Z",
        "external_rating": "తప్పు (False)",
        "claimant": "వాట్సాప్ సందేశాలు",
    },

    # ── Malaria Vaccine (English) ────────────────────────────────────────
    {
        "keywords": ["malaria", "vaccine", "who", "r21", "matrix-m", "approved"],
        "languages": ["en", "auto"],
        "source_name": "World Health Organization",
        "title": "WHO recommends R21/Matrix-M vaccine for malaria prevention in children",
        "url": "https://www.who.int/news/item/02-10-2023-who-recommends-r21-matrix-m-vaccine-for-malaria-prevention",
        "snippet": "The World Health Organization (WHO) has recommended a new vaccine, R21/Matrix-M, for the prevention of malaria in children following advice from strategic advisory groups.",
        "published_at": "2023-10-02T12:00:00Z",
        "external_rating": "Correct / True",
        "claimant": "Public Health Reports",
    },

    # ── Chandrayaan / Lunar Mission (English) ────────────────────────────
    {
        "keywords": ["chandrayaan", "moon", "isro", "landing", "lunar", "south pole"],
        "languages": ["en", "auto"],
        "source_name": "Indian Space Research Organisation (ISRO)",
        "title": "Chandrayaan-3 Successfully Lands on the Lunar Surface",
        "url": "https://www.isro.gov.in/Chandrayaan3_Details.html",
        "snippet": "India's Chandrayaan-3 spacecraft successfully executed a soft landing near the lunar south pole region, confirming all telemetry and instrument deployments.",
        "published_at": "2023-08-23T12:34:00Z",
        "external_rating": "Supported",
        "claimant": "Scientific Telemetry",
    },
]


class LocalEvidenceProvider:
    """
    Offline test fixture provider for local development.

    Never silently serves data in production mode. Every record returned
    is explicitly marked with metadata: {"mode": "DEMO / OFFLINE EVIDENCE"}.
    """

    def __init__(self, allow_in_production: bool = False):
        self._allow_in_production = allow_in_production

    @property
    def name(self) -> str:
        return "local_evidence_fixtures"

    @property
    def is_available(self) -> bool:
        # Strictly disabled in production unless explicitly overridden
        if not self._allow_in_production and getattr(settings, "app_env", "") == "production":
            return False
        return True

    def search(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> EvidenceRetrievalResult:
        """Search local fixtures matching query keywords and language."""
        if not self.is_available:
            logger.error("LocalEvidenceProvider invoked in production mode without explicit authorization")
            return EvidenceRetrievalResult(
                items=[],
                provider=self.name,
                query=query,
                language=language,
                error="Local evidence provider is disabled in production mode. Configure GOOGLE_FACTCHECK_API_KEY.",
            )

        q_lower = query.lower()
        lang_lower = language.lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        matched_fixtures = []
        for fixture in OFFLINE_FIXTURES:
            # Language match check
            if lang_lower not in fixture.get("languages", ["en", "auto"]) and "auto" not in fixture.get("languages", []):
                continue

            # Keyword match check
            keywords = fixture.get("keywords", [])
            matches = any(kw.lower() in q_lower for kw in keywords)
            if matches:
                matched_fixtures.append(fixture)

        items: list[NormalizedEvidence] = []
        for f in matched_fixtures[:page_size]:
            evidence = NormalizedEvidence(
                source_name=f["source_name"],
                title=f["title"],
                url=f["url"],
                snippet=f["snippet"],
                published_at=f.get("published_at"),
                retrieved_at=now_iso,
                source_type="local_fixture",
                external_rating=f.get("external_rating"),
                metadata={
                    "mode": "DEMO / OFFLINE EVIDENCE",
                    "is_offline_fixture": True,
                    "claimant": f.get("claimant"),
                },
            )
            items.append(evidence)

        logger.info(
            "LocalEvidenceProvider returned %d fixtures for query '%s' (lang=%s)",
            len(items), query[:40], language,
        )

        return EvidenceRetrievalResult(
            items=items,
            provider=self.name,
            query=query,
            language=language,
            cached=False,
            next_page_token=None,
            total_results=len(items),
        )
