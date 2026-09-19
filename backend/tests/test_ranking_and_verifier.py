"""
Comprehensive tests for STEP 7: Evidence Ranking and Claim/Evidence Verification.

Validates:
- Ranking signals: semantic similarity, entity overlap, recency decay, source metadata
- Source-grouping logic: repeated/syndicated articles from same publisher grouped
- NLI entailment: support, contradiction, neutral with explicit thresholds
- Multilingual coverage validation: English, Hindi, Telugu
- Verdict synthesis:
  • support case
  • contradiction case
  • neutral case
  • conflicting evidence
  • duplicate evidence
  • irrelevant evidence
  • no evidence
  • multilingual examples
- End-to-end pipeline integration and event tracking
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.models.evidence import Evidence
from app.models.pipeline_event import PipelineEvent
from app.schemas.analysis import AnalysisRequest, Assessment, EvidenceStrength, Language
from app.schemas.evidence import Relation
from app.services.analysis_service import analyze_claim
from app.services.evidence import (
    ClaimEvidenceRelation,
    LanguageCoverageValidator,
    MultilingualDeterministicNLI,
    NLIOutput,
    NormalizedEvidence,
    RankedEvidence,
    SourceMetadata,
    group_and_rank_evidence,
    rank_and_verify_evidence,
    synthesize_evidence_verdict,
    verify_evidence,
)
from app.services.evidence.ranking import (
    compute_composite_relevance,
    compute_entity_overlap,
    compute_recency_score,
    compute_semantic_similarity,
    extract_domain,
    extract_source_metadata,
)
from app.services.evidence.verifier import classify_relation


# ── Fixtures & Helper Factory ───────────────────────────────────────────


def make_evidence(
    source_name: str,
    url: str,
    title: str,
    snippet: str,
    published_at: str | None = "2024-01-10T12:00:00Z",
    external_rating: str | None = None,
    source_type: str = "fact_check",
) -> NormalizedEvidence:
    return NormalizedEvidence(
        source_name=source_name,
        title=title,
        url=url,
        snippet=snippet,
        published_at=published_at,
        retrieved_at="2024-01-11T12:00:00Z",
        source_type=source_type,
        external_rating=external_rating,
    )


# ── Test Evidence Ranking Signals & Source Grouping ──────────────────────


class TestEvidenceRanking:
    """Unit tests for multi-signal ranking and publisher grouping."""

    def test_domain_extraction(self):
        assert extract_domain("https://www.boomlive.in/fact-check/article") == "boomlive.in"
        assert extract_domain("http://sub.domain.co.uk/page") == "sub.domain.co.uk"
        assert extract_domain("invalid-url") == "unknown"

    def test_source_metadata_separation(self):
        ev = make_evidence(
            source_name="Boom Live",
            url="https://boomlive.in/upi-ban",
            title="UPI debunked",
            snippet="Clarification on UPI network",
            published_at="2024-01-05T10:00:00Z",
            external_rating="False",
        )
        meta = extract_source_metadata(ev)
        assert meta.publisher == "Boom Live"
        assert meta.domain == "boomlive.in"
        assert meta.is_verified_fact_checker is True
        assert meta.external_rating == "False"
        assert isinstance(meta.published_at, datetime)

    def test_semantic_similarity_multilingual(self):
        # English match
        sim_en = compute_semantic_similarity(
            "India has banned UPI payments",
            "Reports claiming India has banned UPI payments are completely false",
            language="en",
        )
        assert sim_en > 0.40

        # Hindi match
        sim_hi = compute_semantic_similarity(
            "यूपीआई लेनदेन बंद होने की अफवाह",
            "पड़ताल: क्या सरकार ने यूपीआई लेनदेन बंद कर दिया है? जानें सच",
            language="hi",
        )
        assert sim_hi > 0.25

        # Telugu match
        sim_te = compute_semantic_similarity(
            "యూపీఐ లావాదేవీలు రద్దు ప్రచారం",
            "యూపీఐ లావాదేవీలు రద్దు చేశారంటూ జరుగుతున్న ప్రచారంలో నిజం లేదు",
            language="te",
        )
        assert sim_te > 0.25

        # Disconnected texts should have very low similarity
        sim_diff = compute_semantic_similarity(
            "India has banned UPI payments",
            "Scientists discover a new species of deep sea jellyfish in the Pacific Ocean",
            language="en",
        )
        assert sim_diff < 0.15

    def test_entity_overlap_with_numbers(self):
        claim = "NPCI announces 10 percent transaction fee on 5000 rupees UPI"
        matching_text = "Rumors of a 10 percent fee on 5000 rupees transactions debunked"
        mismatched_text = "Government reviews banking regulations without any fee mentioned"

        score_match = compute_entity_overlap(claim, matching_text)
        score_mismatch = compute_entity_overlap(claim, mismatched_text)

        assert score_match > 0.50
        assert score_mismatch < 0.25

    def test_recency_decay(self):
        # Recent date
        recent = datetime(2026, 1, 1, tzinfo=timezone.utc)
        score_recent = compute_recency_score(recent)

        # Old date (10 years ago)
        old = datetime(2015, 1, 1, tzinfo=timezone.utc)
        score_old = compute_recency_score(old)

        assert score_recent > score_old
        assert score_old >= 0.20
        # Missing date gets default
        assert compute_recency_score(None) == 0.60

    def test_source_grouping_prevents_duplicate_publisher_inflation(self):
        """Syndicated or multiple articles from Boom Live should only yield ONE primary representative."""
        claim = "UPI payments are banned across India"
        candidates = [
            make_evidence("Boom Live", "https://boomlive.in/article-1", "UPI ban false", "NPCI says UPI is active"),
            make_evidence("Boom Live Mirror", "https://boomlive.in/article-2", "UPI ban false copy", "NPCI says UPI is active"),
            make_evidence("Boom Live Syndicated", "https://boomlive.in/article-3", "UPI ban false feed", "NPCI active"),
            make_evidence("Factly", "https://factly.in/upi-claim", "Fact check on UPI shutdown", "No ban circular issued"),
        ]

        ranked = group_and_rank_evidence(claim, candidates, language="en", top_k=5)
        assert len(ranked) == 4

        # Boom Live items should share the same group_id
        boom_items = [r for r in ranked if r.group_id == "boomlive.in"]
        assert len(boom_items) == 3

        # Exactly ONE Boom Live item is primary; the other two are marked non-primary
        primary_boom = [r for r in boom_items if r.is_primary_in_group]
        secondary_boom = [r for r in boom_items if not r.is_primary_in_group]
        assert len(primary_boom) == 1
        assert len(secondary_boom) == 2

        # Factly item is primary in its own group
        factly_item = next(r for r in ranked if r.group_id == "factly.in")
        assert factly_item.is_primary_in_group is True


# ── Test NLI Entailment & Language Coverage ─────────────────────────────


class TestNLIAndLanguageCoverage:
    """Unit tests for NLI entailment logic and multilingual support validation."""

    def test_language_coverage_validator(self):
        assert LanguageCoverageValidator.is_language_supported("en")
        assert LanguageCoverageValidator.is_language_supported("hi")
        assert LanguageCoverageValidator.is_language_supported("te")
        assert not LanguageCoverageValidator.is_language_supported("fr")

        assert LanguageCoverageValidator.validate_language("en") == "en"
        assert LanguageCoverageValidator.validate_language("fr") == "UNSUPPORTED_NLI_LANGUAGE"

    def test_deterministic_nli_english_support(self):
        model = MultilingualDeterministicNLI()
        res = model.predict(
            premise="Government confirms that UPI transactions reached a record high.",
            hypothesis="UPI transactions reached a record high.",
            language="en",
        )
        assert res.predicted_label == "entailment"
        assert res.probabilities["entailment"] >= 0.80

    def test_deterministic_nli_english_contradiction(self):
        model = MultilingualDeterministicNLI()
        res = model.predict(
            premise="NPCI clarifies that reports of a ban or shutdown on UPI are false and unfounded.",
            hypothesis="India has banned UPI payments.",
            language="en",
        )
        assert res.predicted_label == "contradiction"
        assert res.probabilities["contradiction"] >= 0.80

    def test_deterministic_nli_hindi_contradiction(self):
        model = MultilingualDeterministicNLI()
        res = model.predict(
            premise="विश्वास न्यूज की पड़ताल: सरकार द्वारा यूपीआई लेनदेन बंद करने का दावा पूरी तरह झूठा और भ्रामक है।",
            hypothesis="सरकार ने यूपीआई लेनदेन बंद कर दिया है।",
            language="hi",
        )
        assert res.predicted_label == "contradiction"
        assert res.probabilities["contradiction"] >= 0.80

    def test_deterministic_nli_telugu_contradiction(self):
        model = MultilingualDeterministicNLI()
        res = model.predict(
            premise="ఎన్‌పీసీఐ వివరణ: యూపీఐ లావాదేవీలు నిలిపివేస్తున్నట్లు జరుగుతున్న ప్రచారం పూర్తిగా అబద్ధం మరియు తప్పు.",
            hypothesis="యూపీఐ లావాదేవీలు నిలిపివేస్తున్నారు.",
            language="te",
        )
        assert res.predicted_label == "contradiction"
        assert res.probabilities["contradiction"] >= 0.80

    def test_deterministic_nli_neutral_inconclusive(self):
        model = MultilingualDeterministicNLI()
        res = model.predict(
            premise="The weather forecast for New Delhi predicts light rainfall tomorrow morning.",
            hypothesis="India has banned UPI payments.",
            language="en",
        )
        assert res.predicted_label == "neutral"
        assert res.probabilities["neutral"] >= 0.60


# ── Test Threshold Configuration & Relation Classification ──────────────


class TestThresholdClassification:
    """Verifies that configurable thresholds determine relation output."""

    def test_relevance_gate_rejects_irrelevant_evidence(self):
        nli_out = NLIOutput(
            predicted_label="entailment",
            probabilities={"entailment": 0.95, "contradiction": 0.02, "neutral": 0.03},
            score=0.95,
            model_name="test",
            language="en",
        )
        # Low relevance below min threshold (0.30)
        rel, score = classify_relation(
            relevance_score=0.15,
            nli_out=nli_out,
            min_relevance_threshold=0.30,
        )
        assert rel == ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION

    def test_configurable_contradiction_threshold(self):
        nli_out = NLIOutput(
            predicted_label="contradiction",
            probabilities={"contradiction": 0.70, "entailment": 0.10, "neutral": 0.20},
            score=0.70,
            model_name="test",
            language="en",
        )
        # Passes threshold 0.65
        rel_pass, _ = classify_relation(
            relevance_score=0.85,
            nli_out=nli_out,
            contradiction_threshold=0.65,
        )
        assert rel_pass == ClaimEvidenceRelation.CONTRADICTS

        # Fails higher threshold 0.80
        rel_fail, _ = classify_relation(
            relevance_score=0.85,
            nli_out=nli_out,
            contradiction_threshold=0.80,
        )
        assert rel_fail == ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION


# ── Test Verdict Synthesis Scenarios ────────────────────────────────────


class TestVerdictSynthesisScenarios:
    """Comprehensive tests for all required verdict cases."""

    def test_no_evidence_case(self):
        claim = "Random unique assertion xyz"
        verified, synthesis = rank_and_verify_evidence(claim, candidates=[], language="en")
        assert verified == []
        assert synthesis.assessment == Assessment.INSUFFICIENT_EVIDENCE
        assert synthesis.independent_support_count == 0
        assert synthesis.independent_contradict_count == 0

    def test_one_strong_contradiction_case(self):
        """A verified fact checker refuting a claim results in POTENTIALLY_MISLEADING."""
        claim = "India has banned UPI payments nationwide."
        candidates = [
            make_evidence(
                source_name="Boom Live Fact Check",
                url="https://boomlive.in/upi-debunked",
                title="Viral Claim on UPI Payments Ban is False",
                snippet="NPCI clarifies reports of a ban on UPI payments are false and unfounded.",
                source_type="fact_check",
                external_rating="False",
            )
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="en")
        assert len(verified) == 1
        assert verified[0].relation == ClaimEvidenceRelation.CONTRADICTS
        assert synthesis.assessment == Assessment.POTENTIALLY_MISLEADING
        assert synthesis.has_strong_contradiction is True
        assert synthesis.confidence >= 0.80

    def test_multiple_supporting_sources_case(self):
        """Multiple independent sources entailing the claim result in SUPPORTED."""
        claim = "UPI transactions reached record high in December."
        candidates = [
            make_evidence(
                source_name="Economic Times",
                url="https://economictimes.indiatimes.com/upi-record",
                title="UPI transactions reached record high in December",
                snippet="Government confirms that UPI transactions reached a record high in December.",
            ),
            make_evidence(
                source_name="LiveMint",
                url="https://livemint.com/upi-growth",
                title="December UPI numbers verified record high",
                snippet="NPCI data verified record high volume of UPI transactions.",
            ),
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="en")
        assert len(verified) == 2
        assert all(v.relation == ClaimEvidenceRelation.SUPPORTS for v in verified)
        assert synthesis.assessment == Assessment.SUPPORTED
        assert synthesis.independent_support_count == 2
        assert synthesis.confidence >= 0.85

    def test_conflicting_evidence_case(self):
        """Independent sources disagreeing results in CONFLICTING_EVIDENCE."""
        claim = "New health protocol approved by authorities."
        candidates = [
            make_evidence(
                source_name="Source A (Supporter)",
                url="https://source-a.org/news",
                title="New health protocol confirmed and approved",
                snippet="Government confirms that the new health protocol is accurate and approved into law.",
            ),
            make_evidence(
                source_name="Source B (Denier)",
                url="https://source-b.org/news",
                title="Health ministry denies approval of new protocol",
                snippet="Health ministry clarifies that reports of approval are false and unfounded.",
            ),
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="en")
        assert synthesis.assessment == Assessment.CONFLICTING_EVIDENCE
        assert synthesis.independent_support_count >= 1
        assert synthesis.independent_contradict_count >= 1

    def test_duplicate_sources_grouped_properly(self):
        """Repeated articles from the same publisher do not inflate independent count."""
        claim = "India has banned UPI payments."
        candidates = [
            make_evidence("Boom Live", "https://boomlive.in/upi-1", "UPI Ban in India False", "Viral posts claiming India has banned UPI payments are false and debunked."),
            make_evidence("Boom Live", "https://boomlive.in/upi-2", "UPI Ban in India False Copy", "Viral posts claiming India has banned UPI payments are false and debunked."),
            make_evidence("Boom Live", "https://boomlive.in/upi-3", "UPI Ban in India False Feed", "Viral posts claiming India has banned UPI payments are false and debunked."),
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="en")
        assert len(verified) == 3
        # Exactly one independent source counted
        assert synthesis.independent_contradict_count == 1
        assert synthesis.assessment == Assessment.POTENTIALLY_MISLEADING

    def test_irrelevant_evidence_maps_to_insufficient(self):
        """Candidate texts talking about completely unrelated topics are filtered."""
        claim = "India has banned UPI payments."
        candidates = [
            make_evidence(
                source_name="Marine Science Journal",
                url="https://marine.org/jellyfish",
                title="Pacific Ocean deep sea marine ecosystem",
                snippet="Researchers observe bioluminescence in jellyfish in the deep Pacific trench.",
            )
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="en")
        assert len(verified) == 1
        assert verified[0].relation == ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION
        assert synthesis.assessment == Assessment.INSUFFICIENT_EVIDENCE

    def test_multilingual_hindi_support_case(self):
        claim = "यूपीआई लेनदेन के नए आंकड़े जारी"
        candidates = [
            make_evidence(
                source_name="दैनिक जागरण (Dainik Jagran)",
                url="https://jagran.com/upi-data",
                title="यूपीआई लेनदेन के आधिकारिक आंकड़े जारी",
                snippet="सरकार की आधिकारिक घोषणा: यूपीआई के लेनदेन के रिकॉर्ड आंकड़े सच और प्रमाणित हैं।",
            )
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="hi")
        assert len(verified) == 1
        assert verified[0].relation == ClaimEvidenceRelation.SUPPORTS
        assert synthesis.assessment == Assessment.SUPPORTED

    def test_multilingual_telugu_contradiction_case(self):
        claim = "యూపీఐ సేవలు నిలిపివేత"
        candidates = [
            make_evidence(
                source_name="ఫ్యాక్ట్ లీ (Factly Telugu)",
                url="https://telugu.factly.in/upi-debunked",
                title="యూపీఐ సేవలు నిలిపివేస్తున్నారనే ప్రచారం అవాస్తవం",
                snippet="ఎన్‌పీసీఐ ప్రకటన: యూపీఐ సేవలు నిలిపివేయలేదు, ఈ ప్రచారం పూర్తిగా అబద్ధం మరియు తప్పు.",
            )
        ]

        verified, synthesis = rank_and_verify_evidence(claim, candidates, language="te")
        assert len(verified) == 1
        assert verified[0].relation == ClaimEvidenceRelation.CONTRADICTS
        assert synthesis.assessment == Assessment.POTENTIALLY_MISLEADING


# ── Test End-to-End Pipeline Integration & DB Persistence ───────────────


class TestPipelineStep7Integration:
    """Validates analyze_claim end-to-end with ranking, verification, and DB events."""

    @pytest.mark.asyncio
    async def test_pipeline_records_ranking_and_verification_events(self, async_session):
        request = AnalysisRequest(
            text="Viral WhatsApp forward claims that UPI payments are banned nationwide.",
            language=Language.EN,
        )

        async with async_session() as session:
            response = await analyze_claim(request, session=session)

            assert response.analysis_id is not None
            assert len(response.evidence) >= 1
            assert response.evidence[0].relation in (Relation.CONTRADICT, Relation.SUPPORT, Relation.INSUFFICIENT)

            # Query pipeline events from database
            from sqlalchemy import select
            pe_query = await session.execute(
                select(PipelineEvent).where(PipelineEvent.analysis_id == response.analysis_id)
            )
            events = {e.stage: e for e in pe_query.scalars().all()}

            assert "evidence_retrieval" in events
            assert "evidence_ranking" in events
            assert "evidence_verification" in events
            assert "assessment_generation" in events

            ranking_ev = events["evidence_ranking"]
            assert ranking_ev.status == "completed"
            assert "ranked_count" in ranking_ev.metadata_
            assert "independent_groups" in ranking_ev.metadata_

            verif_ev = events["evidence_verification"]
            assert verif_ev.status == "completed"
            assert "evidence_verdict" in verif_ev.metadata_
