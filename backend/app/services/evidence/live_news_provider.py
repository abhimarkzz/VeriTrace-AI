"""
Live real-world news and encyclopedic evidence provider for VeriTrace AI.

Retrieves verified real-time news articles from Google News RSS and encyclopedic
context from Wikipedia API across English, Hindi, and Telugu without requiring
external API keys.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

from app.services.evidence.base import (
    EvidenceProvider,
    EvidenceRetrievalResult,
    NormalizedEvidence,
    sanitize_evidence_text,
    sanitize_evidence_url,
)

logger = logging.getLogger("veritrace.evidence.live_news")

# Language to Google News region and edition mapping
GOOGLE_NEWS_PARAMS = {
    "en": {"hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
    "hi": {"hl": "hi", "gl": "IN", "ceid": "IN:hi"},
    "te": {"hl": "te", "gl": "IN", "ceid": "IN:te"},
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class LiveNewsEvidenceProvider:
    """
    Retrieves live real-world news evidence and encyclopedic knowledge.

    Combines Google News RSS and Wikipedia OpenSearch for real-time claim corroboration.
    """

    def __init__(self, timeout: float = 8.0):
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "live_news"

    @property
    def is_available(self) -> bool:
        return True

    def search(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> EvidenceRetrievalResult:
        """
        Execute live news and encyclopedia search for a claim.
        """
        cleaned_query = sanitize_evidence_text(query, max_length=200)
        if not cleaned_query:
            return EvidenceRetrievalResult(
                items=[],
                provider=self.name,
                query=query,
                language=language,
            )

        lang = language.lower() if language else "en"
        items: list[NormalizedEvidence] = []
        seen_urls: set[str] = set()

        # 1. Retrieve from Google News RSS
        try:
            news_items = self._fetch_google_news(cleaned_query, lang, max_results=page_size)
            for item in news_items:
                if item.url not in seen_urls:
                    seen_urls.add(item.url)
                    items.append(item)
        except Exception as e:
            logger.warning("Google News RSS retrieval error for query '%s': %s", cleaned_query[:40], e)

        # 2. If fewer than 3 items found, augment with Wikipedia search
        if len(items) < 3:
            try:
                wiki_items = self._fetch_wikipedia(cleaned_query, lang, max_results=3)
                for item in wiki_items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        items.append(item)
            except Exception as e:
                logger.warning("Wikipedia retrieval error for query '%s': %s", cleaned_query[:40], e)

        return EvidenceRetrievalResult(
            items=items[:page_size],
            provider=self.name,
            query=cleaned_query,
            language=lang,
            total_results=len(items),
        )

    def _fetch_google_news(
        self, query: str, language: str, max_results: int = 10
    ) -> list[NormalizedEvidence]:
        """Fetch news articles from Google News RSS."""
        params = GOOGLE_NEWS_PARAMS.get(language, GOOGLE_NEWS_PARAMS["en"])
        encoded_q = urllib.parse.quote(query)
        url = (
            f"https://news.google.com/rss/search?q={encoded_q}"
            f"&hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
        )

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            xml_content = resp.read()

        root = ET.fromstring(xml_content)
        articles: list[NormalizedEvidence] = []

        for item_node in root.findall(".//item")[:max_results]:
            title_node = item_node.find("title")
            link_node = item_node.find("link")
            source_node = item_node.find("source")
            pub_node = item_node.find("pubDate")
            desc_node = item_node.find("description")

            raw_title = title_node.text.strip() if title_node is not None and title_node.text else ""
            raw_link = link_node.text.strip() if link_node is not None and link_node.text else ""
            raw_source = source_node.text.strip() if source_node is not None and source_node.text else ""
            raw_pub = pub_node.text.strip() if pub_node is not None and pub_node.text else ""
            raw_desc = desc_node.text.strip() if desc_node is not None and desc_node.text else ""

            if not raw_title or not raw_link:
                continue

            # Parse publisher name from title if source node is empty
            publisher = raw_source
            clean_title = raw_title
            if not publisher and " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                clean_title = parts[0].strip()
                publisher = parts[1].strip()
            elif publisher and clean_title.endswith(f" - {publisher}"):
                clean_title = clean_title[: -(len(publisher) + 3)].strip()

            if not publisher:
                publisher = "News Report"

            # Parse publication timestamp
            pub_iso = None
            if raw_pub:
                try:
                    dt = parsedate_to_datetime(raw_pub)
                    pub_iso = dt.isoformat()
                except Exception:
                    pub_iso = None

            # Clean snippet: remove html tags and truncate
            snippet = sanitize_evidence_text(raw_desc or clean_title, max_length=600)

            articles.append(
                NormalizedEvidence(
                    source_name=publisher,
                    title=sanitize_evidence_text(clean_title, max_length=250),
                    url=sanitize_evidence_url(raw_link),
                    snippet=snippet,
                    published_at=pub_iso,
                    source_type="news",
                    metadata={
                        "publisher": publisher,
                        "feed": "google_news_rss",
                        "raw_pub_date": raw_pub,
                    },
                )
            )

        return articles

    def _fetch_wikipedia(
        self, query: str, language: str, max_results: int = 3
    ) -> list[NormalizedEvidence]:
        """Fetch relevant encyclopedic articles from Wikipedia API."""
        wiki_lang = language if language in ("en", "hi", "te") else "en"
        encoded_q = urllib.parse.quote(query)
        url = (
            f"https://{wiki_lang}.wikipedia.org/w/api.php?"
            f"action=query&list=search&srsearch={encoded_q}&format=json&utf8=1"
        )

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "VeriTraceAI/1.0 (https://github.com/abhimarkzz/VeriTrace-AI)"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        search_results = data.get("query", {}).get("search", [])
        articles: list[NormalizedEvidence] = []

        for r in search_results[:max_results]:
            title = r.get("title", "").strip()
            snippet_html = r.get("snippet", "").strip()
            timestamp = r.get("timestamp")

            if not title:
                continue

            clean_snippet = sanitize_evidence_text(snippet_html, max_length=600)
            article_url = f"https://{wiki_lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

            articles.append(
                NormalizedEvidence(
                    source_name="Wikipedia",
                    title=title,
                    url=sanitize_evidence_url(article_url),
                    snippet=clean_snippet,
                    published_at=timestamp,
                    source_type="encyclopedia",
                    metadata={
                        "publisher": "Wikipedia",
                        "wiki_lang": wiki_lang,
                        "page_id": r.get("pageid"),
                    },
                )
            )

        return articles
