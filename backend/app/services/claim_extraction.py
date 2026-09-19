"""
Claim extraction service.

Extracts factual/checkable statements from normalized text.
- English: spaCy NER + sentence segmentation
- Hindi/Telugu: regex-based sentence splitting + rule-based extraction

Each sentence is scored for "checkability":
  CHECKABLE     — contains verifiable factual assertions
  NON_CHECKABLE — opinions, questions, satire, greetings
  AMBIGUOUS     — predictions, conditional statements, vague assertions
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Claimability(str, Enum):
    CHECKABLE = "CHECKABLE"
    NON_CHECKABLE = "NON_CHECKABLE"
    AMBIGUOUS = "AMBIGUOUS"


@dataclass
class ExtractedClaim:
    """A single extracted claim with metadata."""
    claim_text: str
    claim_type: Optional[str] = None
    claimability: Claimability = Claimability.CHECKABLE
    entities: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["claimability"] = self.claimability.value
        return d


# ── Patterns for non-factual content ────────────────────────────────────

_QUESTION_PATTERN = re.compile(r"\?\s*$")

_OPINION_MARKERS_EN = [
    "i think", "i believe", "i feel", "in my opinion", "imo",
    "i guess", "it seems to me", "personally", "i reckon",
]
_OPINION_MARKERS_HI = [
    "मुझे लगता है", "मेरे विचार में", "मेरी राय में", "शायद",
    "मैं सोचता हूँ", "मैं मानता हूँ",
]
_OPINION_MARKERS_TE = [
    "నా అభిప్రాయం", "నాకు అనిపిస్తుంది", "బహుశా",
]
_ALL_OPINION_MARKERS = _OPINION_MARKERS_EN + _OPINION_MARKERS_HI + _OPINION_MARKERS_TE

_PREDICTION_MARKERS_EN = [
    "will likely", "might", "could potentially", "is expected to",
    "probably will", "in the future", "going to be",
]
_PREDICTION_MARKERS_HI = ["शायद होगा", "भविष्य में", "हो सकता है"]
_PREDICTION_MARKERS_TE = ["జరగవచ్చు", "భవిష్యత్తులో"]
_ALL_PREDICTION_MARKERS = _PREDICTION_MARKERS_EN + _PREDICTION_MARKERS_HI + _PREDICTION_MARKERS_TE

# Number pattern (integers, floats, percentages, currency)
_NUMBER_PATTERN = re.compile(
    r"(?:₹|Rs\.?|USD|\$|€)?\s*\d[\d,]*(?:\.\d+)?\s*(?:%|percent|crore|lakh|million|billion|thousand)?",
    re.IGNORECASE,
)

# Date patterns
_DATE_PATTERN = re.compile(
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s*\d{4}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{4}\b"
    r"|\b\d{4}\b",
    re.IGNORECASE,
)

# Hindi/Telugu sentence delimiters
_INDIC_SENTENCE_SPLIT = re.compile(r"[।|?\n]+")


# ── spaCy loader ────────────────────────────────────────────────────────

_nlp_en = None


def _get_spacy_en():
    """Lazy-load English spaCy model."""
    global _nlp_en
    if _nlp_en is None:
        try:
            import spacy
            _nlp_en = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm loaded successfully")
        except (ImportError, OSError) as e:
            logger.warning("spaCy English model unavailable: %s", e)
            _nlp_en = False  # Mark as failed, don't retry
    return _nlp_en if _nlp_en is not False else None


# ── Checkability scoring ─────────────────────────────────────────────────


def _assess_claimability(text: str) -> Claimability:
    """Assess whether a sentence is checkable, non-checkable, or ambiguous."""
    lower = text.lower().strip()

    # Questions are non-checkable
    if _QUESTION_PATTERN.search(text):
        return Claimability.NON_CHECKABLE

    # Opinion markers → non-checkable
    for marker in _ALL_OPINION_MARKERS:
        if marker in lower:
            return Claimability.NON_CHECKABLE

    # Prediction markers → ambiguous
    for marker in _ALL_PREDICTION_MARKERS:
        if marker in lower:
            return Claimability.AMBIGUOUS

    # Very short text (< 4 words) → ambiguous
    words = lower.split()
    if len(words) < 4:
        return Claimability.AMBIGUOUS

    return Claimability.CHECKABLE


def _classify_claim_type(text: str, entities: list[str], numbers: list[str]) -> Optional[str]:
    """Heuristic claim type classification."""
    lower = text.lower()

    if numbers and any(w in lower for w in ["percent", "%", "crore", "lakh", "million", "billion"]):
        return "statistical"
    if numbers:
        return "numerical"
    if any(w in lower for w in ["said", "announced", "stated", "declared",
                                 "ने कहा", "बोले", "చెప్పారు", "ప్రకటించారు"]):
        return "attribution"
    if any(w in lower for w in ["banned", "launched", "arrested", "passed", "signed",
                                 "प्रतिबंध", "गिरफ्तार", "నిషేధించారు", "అరెస్ట్"]):
        return "event"
    if entities:
        return "entity"
    return None


# ── Extraction ───────────────────────────────────────────────────────────


def _extract_numbers(text: str) -> list[str]:
    return [m.strip() for m in _NUMBER_PATTERN.findall(text) if m.strip()]


def _extract_dates(text: str) -> list[str]:
    return [m.strip() for m in _DATE_PATTERN.findall(text) if m.strip()]


def _extract_english(text: str) -> list[ExtractedClaim]:
    """Extract claims from English text using spaCy."""
    nlp = _get_spacy_en()
    if nlp is None:
        return _extract_fallback(text)

    doc = nlp(text)
    claims = []

    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text or len(sent_text) < 5:
            continue

        entities = list({ent.text for ent in sent.ents})
        numbers = _extract_numbers(sent_text)
        dates = _extract_dates(sent_text)
        claimability = _assess_claimability(sent_text)
        claim_type = _classify_claim_type(sent_text, entities, numbers)

        claims.append(ExtractedClaim(
            claim_text=sent_text,
            claim_type=claim_type,
            claimability=claimability,
            entities=entities,
            dates=dates,
            numbers=numbers,
        ))

    return claims


def _extract_indic(text: str) -> list[ExtractedClaim]:
    """Extract claims from Hindi/Telugu text using regex sentence splitting."""
    sentences = _INDIC_SENTENCE_SPLIT.split(text)
    claims = []

    for sent_text in sentences:
        sent_text = sent_text.strip()
        if not sent_text or len(sent_text) < 5:
            continue

        numbers = _extract_numbers(sent_text)
        dates = _extract_dates(sent_text)
        claimability = _assess_claimability(sent_text)

        # Basic entity extraction — capitalize words in Indic are often names
        # For Hindi/Telugu, proper NER requires dedicated models (known limitation)
        entities: list[str] = []

        claim_type = _classify_claim_type(sent_text, entities, numbers)

        claims.append(ExtractedClaim(
            claim_text=sent_text,
            claim_type=claim_type,
            claimability=claimability,
            entities=entities,
            dates=dates,
            numbers=numbers,
        ))

    return claims


def _extract_fallback(text: str) -> list[ExtractedClaim]:
    """Fallback extraction using simple sentence splitting (period/newline)."""
    sentences = re.split(r"[.!?\n]+", text)
    claims = []

    for sent_text in sentences:
        sent_text = sent_text.strip()
        if not sent_text or len(sent_text) < 5:
            continue

        numbers = _extract_numbers(sent_text)
        dates = _extract_dates(sent_text)
        claimability = _assess_claimability(sent_text)
        claim_type = _classify_claim_type(sent_text, [], numbers)

        claims.append(ExtractedClaim(
            claim_text=sent_text,
            claim_type=claim_type,
            claimability=claimability,
            entities=[],
            dates=dates,
            numbers=numbers,
        ))

    return claims


def extract_claims(text: str, language: str = "en") -> list[ExtractedClaim]:
    """
    Extract factual claims from text.

    Args:
        text: Normalized input text
        language: ISO 639-1 language code

    Returns:
        Ordered list of ExtractedClaim objects
    """
    if not text or not text.strip():
        return []

    if language == "en":
        return _extract_english(text)
    elif language in ("hi", "te"):
        return _extract_indic(text)
    else:
        return _extract_fallback(text)
