"""
Tests for language detection service.

Covers: English, Hindi, Telugu, mixed-language, unsupported language,
empty input, explicit language request.
"""

import pytest
from app.services.language_detection import (
    detect_language,
    DetectionStatus,
    SUPPORTED_LANGUAGES,
)


class TestLanguageDetection:
    # ── English ──────────────────────────────────────────────────────────

    def test_english_text(self):
        result = detect_language("India has banned UPI payments.")
        assert result.language_code == "en"
        assert result.status == DetectionStatus.OK
        assert result.confidence > 0.5

    def test_english_longer_text(self):
        result = detect_language(
            "The Supreme Court of India ruled today that the new policy "
            "regarding digital payments is constitutional."
        )
        assert result.language_code == "en"
        assert result.is_supported

    # ── Hindi ────────────────────────────────────────────────────────────

    def test_hindi_text(self):
        result = detect_language("भारत ने UPI भुगतान पर प्रतिबंध लगा दिया है।")
        assert result.language_code == "hi"
        assert result.status == DetectionStatus.OK

    # ── Telugu ───────────────────────────────────────────────────────────

    def test_telugu_text(self):
        result = detect_language(
            "భారతదేశంలో డిజిటల్ చెల్లింపులు నిషేధించబడ్డాయి అని ప్రభుత్వం ప్రకటించింది."
        )
        assert result.language_code == "te"
        assert result.status == DetectionStatus.OK

    # ── Unsupported Language ─────────────────────────────────────────────

    def test_unsupported_language(self):
        # French should be detected but marked unsupported
        result = detect_language(
            "Le gouvernement français a interdit les paiements numériques."
        )
        assert result.status == DetectionStatus.UNSUPPORTED_LANGUAGE
        assert result.language_code == "fr"

    # ── Explicit Language Request ────────────────────────────────────────

    def test_explicit_english(self):
        result = detect_language("Any text here", requested="en")
        assert result.language_code == "en"
        assert result.status == DetectionStatus.OK
        assert result.confidence == 1.0

    def test_explicit_hindi(self):
        result = detect_language("Any text here", requested="hi")
        assert result.language_code == "hi"
        assert result.status == DetectionStatus.OK

    def test_explicit_unsupported(self):
        result = detect_language("Any text here", requested="ja")
        assert result.status == DetectionStatus.UNSUPPORTED_LANGUAGE

    # ── Edge Cases ───────────────────────────────────────────────────────

    def test_empty_input(self):
        result = detect_language("")
        assert result.status == DetectionStatus.EMPTY_INPUT

    def test_whitespace_only(self):
        result = detect_language("   ")
        assert result.status == DetectionStatus.EMPTY_INPUT

    def test_auto_mode_explicit(self):
        result = detect_language("This is English text", requested="auto")
        assert result.language_code == "en"
        assert result.status == DetectionStatus.OK

    def test_confidence_has_value(self):
        result = detect_language("This is a fairly long English sentence for testing.")
        assert result.confidence > 0.0
        assert result.confidence <= 1.0

    def test_all_candidates_present(self):
        result = detect_language("This is English text for analysis purposes.")
        assert result.all_candidates is not None
        assert len(result.all_candidates) > 0

    # ── Short English Claims Disambiguation ──────────────────────────────

    def test_short_english_headlines(self):
        claims = [
            "Prime Minister Modi Died",
            "PM Modi dead",
            "Modi resigned",
            "Amit Shah hospital",
            "Rahul Gandhi speech",
            "Metadata test claim.",
        ]
        for claim in claims:
            res = detect_language(claim)
            assert res.language_code == "en", f"Failed for '{claim}': got {res.language_code}"
            assert res.status == DetectionStatus.OK, f"Status failed for '{claim}': got {res.status}"
            assert res.is_supported

