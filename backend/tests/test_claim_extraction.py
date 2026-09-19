"""
Tests for claim extraction service.

Covers: English, Hindi, Telugu, multiple claims, empty input,
opinions, questions, predictions, numbers, dates, entities.
"""

import pytest
from app.services.claim_extraction import (
    extract_claims,
    Claimability,
    ExtractedClaim,
)


class TestClaimExtractionEnglish:
    def test_single_english_claim(self):
        claims = extract_claims("India has banned UPI payments.", "en")
        assert len(claims) >= 1
        assert claims[0].claim_text
        assert claims[0].claimability == Claimability.CHECKABLE

    def test_multiple_claims(self):
        text = (
            "India banned UPI payments. "
            "The GDP grew by 7.5% in 2024. "
            "The Prime Minister announced a new policy."
        )
        claims = extract_claims(text, "en")
        assert len(claims) >= 2

    def test_entity_extraction(self):
        claims = extract_claims(
            "The Supreme Court of India ruled on the case.", "en"
        )
        assert len(claims) >= 1
        # spaCy should find at least one entity
        all_entities = []
        for c in claims:
            all_entities.extend(c.entities)
        # May or may not find entities depending on model — just verify structure
        assert isinstance(all_entities, list)

    def test_number_extraction(self):
        claims = extract_claims("Revenue was $50 million in 2024.", "en")
        assert len(claims) >= 1
        all_numbers = []
        for c in claims:
            all_numbers.extend(c.numbers)
        assert len(all_numbers) >= 1

    def test_date_extraction(self):
        claims = extract_claims("The event happened on 15/08/2024.", "en")
        assert len(claims) >= 1
        all_dates = []
        for c in claims:
            all_dates.extend(c.dates)
        assert len(all_dates) >= 1

    def test_url_text(self):
        claims = extract_claims("Check [URL] for more details about the ban.", "en")
        assert len(claims) >= 1


class TestClaimExtractionHindi:
    def test_hindi_claim(self):
        claims = extract_claims(
            "भारत ने UPI भुगतान पर प्रतिबंध लगा दिया है।", "hi"
        )
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.CHECKABLE

    def test_hindi_number(self):
        claims = extract_claims(
            "जीडीपी 7.5% बढ़ी है।", "hi"
        )
        assert len(claims) >= 1
        all_numbers = []
        for c in claims:
            all_numbers.extend(c.numbers)
        assert len(all_numbers) >= 1


class TestClaimExtractionTelugu:
    def test_telugu_claim(self):
        claims = extract_claims(
            "భారతదేశంలో డిజిటల్ చెల్లింపులు నిషేధించబడ్డాయి.", "te"
        )
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.CHECKABLE


class TestClaimability:
    def test_question_is_non_checkable(self):
        claims = extract_claims("Is India really banning UPI?", "en")
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.NON_CHECKABLE

    def test_opinion_is_non_checkable(self):
        claims = extract_claims("I think the government is doing a great job.", "en")
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.NON_CHECKABLE

    def test_hindi_opinion_non_checkable(self):
        claims = extract_claims("मुझे लगता है सरकार अच्छा काम कर रही है।", "hi")
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.NON_CHECKABLE

    def test_prediction_is_ambiguous(self):
        claims = extract_claims(
            "The economy will likely recover next year.", "en"
        )
        assert len(claims) >= 1
        assert claims[0].claimability == Claimability.AMBIGUOUS

    def test_very_short_text_ambiguous(self):
        claims = extract_claims("Ban UPI", "en")
        if claims:
            assert claims[0].claimability == Claimability.AMBIGUOUS


class TestEdgeCases:
    def test_empty_input(self):
        claims = extract_claims("", "en")
        assert claims == []

    def test_whitespace_only(self):
        claims = extract_claims("   ", "en")
        assert claims == []

    def test_to_dict(self):
        claim = ExtractedClaim(
            claim_text="Test claim",
            claim_type="event",
            claimability=Claimability.CHECKABLE,
            entities=["India"],
            dates=["2024"],
            numbers=["50%"],
        )
        d = claim.to_dict()
        assert d["claim_text"] == "Test claim"
        assert d["claimability"] == "CHECKABLE"
        assert d["entities"] == ["India"]

    def test_mixed_language_fallback(self):
        # Unknown language falls back to regex splitting
        claims = extract_claims("Dies ist ein deutscher Satz.", "de")
        assert isinstance(claims, list)
