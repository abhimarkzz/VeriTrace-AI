"""
Language detection service.

Uses langdetect (Google's language detection algorithm) to identify
the language of input text. Supports 55 languages including English,
Hindi, and Telugu.

Library: langdetect (https://github.com/Mimino666/langdetect)
Based on: Nakatani Shuyo's language-detection (Google)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# VeriTrace supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}


class DetectionStatus(str, Enum):
    OK = "ok"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    DETECTION_UNAVAILABLE = "detection_unavailable"
    EMPTY_INPUT = "empty_input"


@dataclass
class LanguageDetectionResult:
    """Result from language detection."""
    language_code: str
    language_name: str
    confidence: float
    status: DetectionStatus
    all_candidates: list[dict] | None = None

    @property
    def is_supported(self) -> bool:
        return self.status == DetectionStatus.OK


def _init_detector():
    """Initialize langdetect with deterministic seed."""
    try:
        from langdetect import DetectorFactory
        DetectorFactory.seed = 0  # Deterministic results
        return True
    except ImportError:
        logger.error("langdetect not installed. Run: pip install langdetect")
        return False


# Initialize on import
_detector_available = _init_detector()


INDIC_SCRIPTS = {
    "hi": (0x0900, 0x097F),  # Devanagari
    "te": (0x0C00, 0x0C7F),  # Telugu
}

UNSUPPORTED_SCRIPTS = [
    (0x0400, 0x04FF, "Cyrillic"),
    (0x0600, 0x06FF, "Arabic"),
    (0x4E00, 0x9FFF, "CJK"),
    (0x3040, 0x30FF, "Japanese"),
    (0xAC00, 0xD7AF, "Korean"),
    (0x0B80, 0x0BFF, "Tamil"),
    (0x0980, 0x09FF, "Bengali"),
    (0x0A80, 0x0AFF, "Gujarati"),
    (0x0D00, 0x0D7F, "Malayalam"),
    (0x0C80, 0x0CFF, "Kannada"),
    (0x0A00, 0x0A7F, "Gurmukhi"),
]

FOREIGN_DIACRITICS = set("éèêëàâçîïôùûœæäöüßáíóúñ¿¡ãõàèéìòùøåæłśćżźęąčšžýřďťňăîșțâ")

FOREIGN_LANGUAGE_STOPWORDS = {
    "fr": {
        "le", "la", "les", "du", "des", "un", "une", "est", "sont", "dans",
        "pour", "avec", "sur", "qui", "que", "ce", "cette", "ces", "au",
        "aux", "par", "ont", "pas", "plus", "ne", "gouvernement", "interdit",
        "paiements", "francais",
    },
    "de": {
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
        "einem", "einer", "eines", "und", "ist", "sind", "nicht", "mit",
        "auf", "für", "von", "vom", "im", "zu", "zum", "zur", "dass",
        "hat", "haben", "wird", "werden", "war", "waren", "auch", "als",
        "bundesregierung", "gesetz",
    },
    "es": {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "del",
        "por", "para", "con", "que", "como", "más", "pero", "ha", "han",
        "fue", "este", "esta", "estos", "estas", "gobierno",
    },
    "it": {
        "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "del",
        "della", "dei", "delle", "dal", "nel", "nella", "con", "su", "sul",
        "per", "tra", "fra", "non", "che", "sono", "ha", "hanno", "questo",
        "questa", "governo",
    },
    "pt": {
        "os", "as", "um", "uma", "uns", "umas", "no", "na", "nos", "nas",
        "do", "da", "dos", "das", "que", "por", "para", "com", "não",
        "seu", "sua", "seus", "suas", "são", "foi", "pelo", "pela", "governo",
    },
    "nl": {
        "het", "de", "een", "van", "en", "in", "op", "te", "met", "voor",
        "zijn", "niet", "aan", "om", "dan", "maar",
    },
}


def _detect_indic_script(text: str) -> str | None:
    """Detect Hindi (Devanagari) or Telugu script by character code points."""
    hi_count = 0
    te_count = 0
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            hi_count += 1
        elif 0x0C00 <= cp <= 0x0C7F:
            te_count += 1

    if hi_count > 0 and hi_count >= te_count:
        return "hi"
    if te_count > 0 and te_count > hi_count:
        return "te"
    return None


def _has_unsupported_script(text: str) -> bool:
    """Check if text contains explicit unsupported non-Latin scripts."""
    for ch in text:
        cp = ord(ch)
        for start, end, _ in UNSUPPORTED_SCRIPTS:
            if start <= cp <= end:
                return True
    return False


def _is_truly_foreign_latin(text: str, candidate_lang: str) -> bool:
    """
    Check whether Latin-script text has genuine markers of a foreign European language.
    Prevents false negatives on short English claims like 'Prime Minister Modi Died'.
    """
    import re

    lower = text.lower()
    # Check for foreign diacritics / special characters
    if any(c in FOREIGN_DIACRITICS for c in lower):
        return True

    words = set(re.findall(r"[a-zA-Z]+", lower))
    if not words:
        return False

    # Check candidate language specific stopwords
    if candidate_lang in FOREIGN_LANGUAGE_STOPWORDS:
        matched = words.intersection(FOREIGN_LANGUAGE_STOPWORDS[candidate_lang])
        if len(matched) >= 2 or (len(words) <= 3 and len(matched) >= 1):
            return True

    # Check across all foreign language stopwords
    for lang, sw in FOREIGN_LANGUAGE_STOPWORDS.items():
        matched = words.intersection(sw)
        if len(matched) >= 2:
            return True

    return False


def detect_language(text: str, requested: str = "auto") -> LanguageDetectionResult:
    """
    Detect the language of input text.

    Args:
        text: Input text to analyze
        requested: User-requested language code ("auto" for detection,
                   or an explicit code like "en", "hi", "te")

    Returns:
        LanguageDetectionResult with language_code, language_name,
        confidence, and status.
    """
    # Handle explicit language request (not "auto")
    if requested and requested != "auto":
        if requested in SUPPORTED_LANGUAGES:
            return LanguageDetectionResult(
                language_code=requested,
                language_name=SUPPORTED_LANGUAGES[requested],
                confidence=1.0,
                status=DetectionStatus.OK,
            )
        return LanguageDetectionResult(
            language_code=requested,
            language_name="Unknown",
            confidence=1.0,
            status=DetectionStatus.UNSUPPORTED_LANGUAGE,
        )

    # Handle empty input
    clean = text.strip()
    if not clean:
        return LanguageDetectionResult(
            language_code="",
            language_name="",
            confidence=0.0,
            status=DetectionStatus.EMPTY_INPUT,
        )

    # Check Indic script directly (Hindi / Telugu)
    script_lang = _detect_indic_script(clean)
    if script_lang:
        return LanguageDetectionResult(
            language_code=script_lang,
            language_name=SUPPORTED_LANGUAGES[script_lang],
            confidence=0.99,
            status=DetectionStatus.OK,
            all_candidates=[{"language_code": script_lang, "confidence": 0.99}],
        )

    # Check for unsupported non-Latin scripts (Arabic, Cyrillic, CJK, etc.)
    if _has_unsupported_script(clean):
        try:
            from langdetect import detect_langs

            results = detect_langs(clean)
            top_lang = str(results[0].lang) if results else "unknown"
            candidates = [
                {"language_code": str(r.lang), "confidence": round(float(r.prob), 4)}
                for r in results
            ]
        except Exception:
            top_lang = "unknown"
            candidates = []

        return LanguageDetectionResult(
            language_code=top_lang,
            language_name="Unknown",
            confidence=0.95,
            status=DetectionStatus.UNSUPPORTED_LANGUAGE,
            all_candidates=candidates,
        )

    # Detect automatically using langdetect
    if not _detector_available:
        return LanguageDetectionResult(
            language_code="en",
            language_name="English",
            confidence=0.0,
            status=DetectionStatus.DETECTION_UNAVAILABLE,
        )

    try:
        from langdetect import detect_langs

        results = detect_langs(clean)
        if not results:
            return LanguageDetectionResult(
                language_code="en",
                language_name="English",
                confidence=0.0,
                status=DetectionStatus.DETECTION_UNAVAILABLE,
            )

        # Get top result
        top = results[0]
        lang_code = str(top.lang)
        confidence = float(top.prob)

        # Build all candidates
        candidates = [
            {"language_code": str(r.lang), "confidence": round(float(r.prob), 4)}
            for r in results
        ]

        # Check if directly supported
        if lang_code in SUPPORTED_LANGUAGES:
            return LanguageDetectionResult(
                language_code=lang_code,
                language_name=SUPPORTED_LANGUAGES[lang_code],
                confidence=round(confidence, 4),
                status=DetectionStatus.OK,
                all_candidates=candidates,
            )

        # Disambiguation for Latin-script text:
        # Statistical n-gram models often mistakenly classify short English headlines or
        # proper nouns (e.g. 'Prime Minister Modi Died', 'PM Modi dead', 'Metadata test claim')
        # as German (de), Italian (it), Catalan (ca), Somali (so), Romanian (ro), etc.
        # If there are no distinctive foreign diacritics or foreign stopwords, resolve to English.
        if not _is_truly_foreign_latin(clean, lang_code):
            return LanguageDetectionResult(
                language_code="en",
                language_name="English",
                confidence=0.95,
                status=DetectionStatus.OK,
                all_candidates=[{"language_code": "en", "confidence": 0.95}] + candidates,
            )

        return LanguageDetectionResult(
            language_code=lang_code,
            language_name="Unknown",
            confidence=round(confidence, 4),
            status=DetectionStatus.UNSUPPORTED_LANGUAGE,
            all_candidates=candidates,
        )

    except Exception as e:
        logger.exception("Language detection failed: %s", e)
        # Default to English for Latin-script input on failure
        return LanguageDetectionResult(
            language_code="en",
            language_name="English",
            confidence=0.5,
            status=DetectionStatus.OK,
        )

