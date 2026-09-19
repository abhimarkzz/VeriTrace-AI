"""
Base models, interfaces, and security utilities for evidence retrieval.

Defines the normalized evidence contract, provider protocol, and untrusted
content sanitization to defend against prompt injection and context poisoning.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Protocol, runtime_checkable

# Pattern for stripping HTML tags
HTML_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)

# Pattern for zero-width and invisible characters used in steganographic prompt injection
ZERO_WIDTH_CHARS_RE = re.compile(r"[\u200B-\u200D\uFEFF\u2060\u00A0]")

# Dangerous script and pseudo-protocol patterns
DANGEROUS_PROTOCOLS_RE = re.compile(r"(?i)\b(javascript|vbscript|data|file):")

# Markdown image exfiltration pattern
MARKDOWN_EXFIL_RE = re.compile(r"!\[.*?\]\(https?://[^\)]+\)")

# Prompt injection signature patterns to neutralize
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directives|guidelines)\b"),
    re.compile(r"(?i)\b(disregard|forget|override|bypass)\s+(all\s+)?(previous|prior|above|existing)\s+(rules|instructions|prompts|directives|context|guidelines)\b"),
    re.compile(r"(?i)\b(system\s*prompt|system\s*directive|developer\s*mode|god\s*mode)\s*:\b"),
    re.compile(r"(?i)\bnew\s+(instructions?|system\s*prompt|directive)\s*:\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+(a|an|in)\b"),
    re.compile(r"(?i)\bact\s+as\s+(an?\s+)?(unrestricted|jailbroken|unfiltered|evil|dan)\b"),
    re.compile(r"(?i)\byou\s+must\s+(now\s+)?(always\s+)?(say|output|respond\s+with|confirm)\b"),
    re.compile(r"(?i)\[/?(system|instructions?|developer|assistant|human)\]"),
    re.compile(r"(?i)<(system|instructions?|developer|assistant|human)>"),
    re.compile(r"<\|im_(start|end)\|>", re.IGNORECASE),
]


def sanitize_evidence_text(text: str, max_length: int = 1500) -> str:
    """
    Sanitize untrusted external web text.

    - Strips raw HTML and script tags.
    - Neutralizes dangerous pseudo-protocols.
    - Decodes HTML entities cleanly.
    - Removes zero-width steganographic characters.
    - Defangs known prompt injection and system directive attempts.
    - Neutralizes markdown image exfiltration tokens.
    - Truncates to safe length bounds to prevent context flooding.
    """
    if not text:
        return ""

    # Strip zero-width characters
    cleaned = ZERO_WIDTH_CHARS_RE.sub("", text)

    # Strip HTML tags
    cleaned = HTML_TAG_RE.sub(" ", cleaned)

    # Decode HTML entities (e.g. &amp; -> &)
    cleaned = html.unescape(cleaned)

    # Neutralize dangerous pseudo-protocols in text
    cleaned = DANGEROUS_PROTOCOLS_RE.sub("[filtered_protocol]:", cleaned)

    # Defang markdown image exfiltration attempts
    cleaned = MARKDOWN_EXFIL_RE.sub("[filtered_image]", cleaned)

    # Neutralize prompt injection phrases by defanging them
    for pattern in PROMPT_INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered_directive]", cleaned)

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    # Bound maximum length
    if len(cleaned) > max_length:
        cleaned = cleaned[: max(0, max_length - 3)].rstrip() + "..."

    return cleaned


def sanitize_evidence_url(url: Optional[str]) -> str:
    """
    Sanitize and validate an external evidence URL.
    Ensures scheme is http/https and blocks javascript:, data:, or malformed links.
    """
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
        return ""
    # Disallow internal control characters or newlines
    if any(c in cleaned for c in ("\r", "\n", "\t", " ", "<", ">", '"', "'")):
        return ""
    return cleaned



@dataclass
class NormalizedEvidence:
    """
    Standardized evidence contract.

    Preserves publisher and external rating without conflating with internal verdict.
    """
    source_name: str
    title: str
    url: str
    snippet: str
    published_at: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_type: str = "fact_check"  # "fact_check" | "web_search" | "local_fixture"
    external_rating: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to standard JSON-compatible dictionary."""
        return {
            "source_name": self.source_name,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "source_type": self.source_type,
            "external_rating": self.external_rating,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceRetrievalResult:
    """Result of an evidence retrieval search operation."""
    items: list[NormalizedEvidence]
    provider: str
    query: str
    language: str
    cached: bool = False
    next_page_token: Optional[str] = None
    total_results: int = 0
    error: Optional[str] = None


@runtime_checkable
class EvidenceProvider(Protocol):
    """Protocol interface for all evidence providers."""

    @property
    def name(self) -> str:
        """Provider identifier."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the provider is configured and available."""
        ...

    def search(
        self,
        query: str,
        language: str = "en",
        page_size: int = 10,
        page_token: Optional[str] = None,
    ) -> EvidenceRetrievalResult:
        """Execute a claim verification search query."""
        ...
