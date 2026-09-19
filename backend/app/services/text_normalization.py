"""
Text normalization service.

Cleans and normalizes input text for downstream NLP processing.
Handles: whitespace, repeated punctuation, Unicode normalization,
URLs, mentions, hashtags, forwarded-message prefixes, excessive formatting.

Does NOT destroy: numbers, dates, named entities, meaningful punctuation.

No external ML dependencies — pure regex + unicodedata.
"""

from __future__ import annotations

import re
import unicodedata


# ── Patterns ─────────────────────────────────────────────────────────────

# URLs (http, https, ftp, www)
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

# Social media mentions (@username)
_MENTION_PATTERN = re.compile(r"@[\w]+")

# Hashtags (#topic) — split camelCase
_HASHTAG_PATTERN = re.compile(r"#([\w]+)")

# Forwarded message prefixes (multilingual)
_FORWARDED_PATTERNS = [
    re.compile(r"^(?:Forwarded|Fwd|FWD|Fw)\s*[:>]\s*", re.MULTILINE),
    re.compile(r"^-{2,}\s*Forwarded\s+message\s*-{2,}\s*", re.MULTILINE),
    re.compile(r"^>{1,3}\s*", re.MULTILINE),  # Quoted text markers
]

# Repeated punctuation (3+ → collapse to 1)
_REPEATED_PUNCT = re.compile(r"([!?.])\1{2,}")

# Excessive whitespace
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")

# Repeated characters (e.g., "soooo gooood" → leave 2 max)
_REPEATED_CHARS = re.compile(r"(.)\1{3,}")

# Zero-width and invisible Unicode characters
_INVISIBLE_CHARS = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad\u2060]"
)

# Emoji variation selectors
_VARIATION_SELECTORS = re.compile(r"[\ufe00-\ufe0f]")


def _split_camel_case(text: str) -> str:
    """Split camelCase and PascalCase: 'FakeNewsBusted' → 'Fake News Busted'."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", text)


def _normalize_hashtag(match: re.Match) -> str:
    """Convert hashtag to readable text: #FakeNewsBusted → Fake News Busted."""
    tag_text = match.group(1)
    return _split_camel_case(tag_text)


def normalize_text(text: str) -> str:
    """
    Normalize input text for NLP processing.

    Preserves: numbers, dates, named entities, sentence structure.
    Removes/normalizes: URLs, mentions, excess formatting, invisible chars.
    """
    if not text:
        return ""

    result = text

    # Unicode NFC normalization (compose diacritics)
    result = unicodedata.normalize("NFC", result)

    # Remove invisible/zero-width characters
    result = _INVISIBLE_CHARS.sub("", result)
    result = _VARIATION_SELECTORS.sub("", result)

    # Remove forwarded-message prefixes
    for pattern in _FORWARDED_PATTERNS:
        result = pattern.sub("", result)

    # Replace URLs with placeholder (preserve meaning, remove noise)
    result = _URL_PATTERN.sub("[URL]", result)

    # Replace mentions with placeholder
    result = _MENTION_PATTERN.sub("[MENTION]", result)

    # Normalize hashtags: #FakeNewsBusted → Fake News Busted
    result = _HASHTAG_PATTERN.sub(_normalize_hashtag, result)

    # Collapse repeated punctuation (!!!!! → !)
    result = _REPEATED_PUNCT.sub(r"\1", result)

    # Collapse repeated characters (soooo → soo)
    result = _REPEATED_CHARS.sub(r"\1\1", result)

    # Normalize whitespace
    result = _MULTI_SPACE.sub(" ", result)
    result = _MULTI_NEWLINE.sub("\n\n", result)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in result.split("\n")]
    result = "\n".join(lines)

    return result.strip()
