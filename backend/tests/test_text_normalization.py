"""
Tests for text normalization service.

Covers: whitespace, URLs, mentions, hashtags, forwarded prefixes,
repeated punctuation, Unicode, numbers, dates preservation.
"""

import pytest
from app.services.text_normalization import normalize_text


class TestTextNormalization:
    # ── Whitespace ───────────────────────────────────────────────────────

    def test_collapse_whitespace(self):
        assert normalize_text("hello    world") == "hello world"

    def test_strip_leading_trailing(self):
        assert normalize_text("  hello world  ") == "hello world"

    def test_collapse_newlines(self):
        result = normalize_text("line1\n\n\n\n\nline2")
        assert result == "line1\n\nline2"

    # ── URLs ─────────────────────────────────────────────────────────────

    def test_replace_url(self):
        result = normalize_text("Check https://example.com/article for details")
        assert "[URL]" in result
        assert "https://example.com" not in result

    def test_replace_multiple_urls(self):
        result = normalize_text("See https://a.com and http://b.com for info")
        assert result.count("[URL]") == 2

    # ── Mentions ─────────────────────────────────────────────────────────

    def test_replace_mention(self):
        result = normalize_text("As @elonmusk said yesterday")
        assert "[MENTION]" in result
        assert "@elonmusk" not in result

    # ── Hashtags ─────────────────────────────────────────────────────────

    def test_hashtag_camel_case_split(self):
        result = normalize_text("#FakeNewsBusted today")
        assert "Fake News Busted" in result
        assert "#" not in result

    def test_hashtag_simple(self):
        result = normalize_text("#breaking news today")
        assert "breaking" in result

    # ── Forwarded Prefixes ───────────────────────────────────────────────

    def test_forwarded_prefix(self):
        result = normalize_text("Forwarded: Big news today!")
        assert "Forwarded:" not in result
        assert "Big news today!" in result

    def test_fwd_prefix(self):
        result = normalize_text("Fwd: Check this out")
        assert "Fwd:" not in result
        assert "Check this out" in result

    # ── Repeated Punctuation ─────────────────────────────────────────────

    def test_collapse_exclamation(self):
        result = normalize_text("Breaking news!!!!!!")
        assert result == "Breaking news!"

    def test_collapse_question_marks(self):
        result = normalize_text("Is this true????")
        assert result == "Is this true?"

    # ── Repeated Characters ──────────────────────────────────────────────

    def test_collapse_repeated_chars(self):
        result = normalize_text("soooooo goooood")
        assert "soo" in result
        assert "sooo" not in result

    # ── Unicode ──────────────────────────────────────────────────────────

    def test_nfc_normalization(self):
        # é composed vs decomposed
        result = normalize_text("caf\u0065\u0301")
        assert "café" in result or "cafe" in result

    def test_remove_zero_width(self):
        result = normalize_text("hello\u200bworld")
        assert "\u200b" not in result
        assert "helloworld" in result

    # ── Preserve Numbers and Dates ───────────────────────────────────────

    def test_preserve_numbers(self):
        result = normalize_text("The GDP grew by 7.5% in 2024")
        assert "7.5%" in result
        assert "2024" in result

    def test_preserve_currency(self):
        result = normalize_text("Revenue was ₹50,000 crore last quarter")
        assert "₹50,000" in result
        assert "crore" in result

    def test_preserve_dates(self):
        result = normalize_text("Signed on 15/08/2024 by the PM")
        assert "15/08/2024" in result

    # ── Empty / Minimal Input ────────────────────────────────────────────

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_whitespace_only(self):
        assert normalize_text("   ") == ""

    # ── Hindi Text ───────────────────────────────────────────────────────

    def test_hindi_preserved(self):
        result = normalize_text("भारत ने UPI भुगतान पर प्रतिबंध लगा दिया है।")
        assert "भारत" in result
        assert "UPI" in result
        assert "प्रतिबंध" in result

    # ── Telugu Text ──────────────────────────────────────────────────────

    def test_telugu_preserved(self):
        result = normalize_text("భారతదేశంలో డిజిటల్ చెల్లింపులు నిషేధించబడ్డాయి.")
        assert "భారతదేశంలో" in result
        assert "డిజిటల్" in result
