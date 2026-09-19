"""
Curated Multilingual NLI and Verification Benchmark Suite.

Evaluates the claim-evidence relationship across:
  - SUPPORTS
  - CONTRADICTS
  - NOT_ENOUGH_INFORMATION

Covers:
  - English (en), Hindi (hi), Telugu (te)
  - Paraphrasing
  - Explicit negation ("not", "never", "नहीं", "లేదు")
  - Number changes (50% vs 5%, 500 vs 2000)
  - Date changes (2021 vs 2024)
  - Entity changes (SEBI vs CCI, Delhi vs Mumbai)
  - Partial claims and out-of-context statements
  - Adversarial false support cases (high lexical overlap with inverted polarities)
"""

from __future__ import annotations

import pytest

from app.services.evidence.nli import get_nli_model
from app.services.evidence.verifier import (
    ClaimEvidenceRelation,
    classify_relation,
)


CURATED_NLI_BENCHMARK_CASES = [
    # ── 1. English Benchmark Cases ───────────────────────────────────────────
    {
        "id": "EN-SUP-01",
        "lang": "en",
        "type": "paraphrase",
        "expected": ClaimEvidenceRelation.SUPPORTS,
        "premise": "The monetary policy committee voted unanimously to keep the policy repo rate unchanged at 6.50 percent.",
        "hypothesis": "Reserve Bank of India maintained the key repo rate at 6.5%.",
    },
    {
        "id": "EN-CON-01",
        "lang": "en",
        "type": "negation",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "NPCI issued an official clarification confirming that UPI services are operating normally and will not be discontinued.",
        "hypothesis": "UPI digital payments have been banned and shut down nationwide.",
    },
    {
        "id": "EN-CON-02",
        "lang": "en",
        "type": "number_change",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "Official figures confirm an inflation rate of 4.8 percent for the past quarter.",
        "hypothesis": "Inflation skyrocketed to 48 percent last quarter.",
    },
    {
        "id": "EN-CON-03",
        "lang": "en",
        "type": "date_change",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "The bilateral climate agreement was concluded in November 2021 in Glasgow.",
        "hypothesis": "The climate agreement was signed for the first time in 2026.",
    },
    {
        "id": "EN-CON-04",
        "lang": "en",
        "type": "entity_change",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "The Competition Commission of India approved the telecom merger with divestment stipulations.",
        "hypothesis": "The Securities and Exchange Board of India (SEBI) approved the telecom merger.",
    },
    {
        "id": "EN-NEU-01",
        "lang": "en",
        "type": "partial_claim",
        "expected": ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION,
        "premise": "The Prime Minister held discussions regarding infrastructure projects in coastal regions.",
        "hypothesis": "A 100-billion dollar deepwater port was inaugurated during the visit.",
    },
    {
        "id": "EN-ADV-01",
        "lang": "en",
        "type": "false_support_adversarial",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "The regulatory board has NOT approved the proposed transaction tariff hike.",
        "hypothesis": "The regulatory board has approved the proposed transaction tariff hike.",
    },

    # ── 2. Hindi Benchmark Cases ─────────────────────────────────────────────
    {
        "id": "HI-SUP-01",
        "lang": "hi",
        "type": "paraphrase",
        "expected": ClaimEvidenceRelation.SUPPORTS,
        "premise": "भारतीय अंतरिक्ष अनुसंधान संगठन (इसरो) द्वारा सौर मिशन आदित्य एल1 का सफल प्रक्षेपण किया गया।",
        "hypothesis": "इसरो ने आदित्य L1 सौर मिशन सफलतापूर्वक लॉन्च किया।",
    },
    {
        "id": "HI-CON-01",
        "lang": "hi",
        "type": "negation",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "खाद्य मंत्रालय ने स्पष्ट किया कि प्रधानमंत्री गरीब कल्याण अन्न योजना बंद नहीं की गई है और यह निरंतर जारी रहेगी।",
        "hypothesis": "सरकार ने मुफ्त राशन वितरण योजना को पूरी तरह से बंद कर दिया है।",
    },
    {
        "id": "HI-CON-02",
        "lang": "hi",
        "type": "number_change",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "मंडी में टमाटर का थोक भाव 40 से 50 रुपये प्रति किलो दर्ज किया गया।",
        "hypothesis": "टमाटर की कीमत 500 रुपये प्रति किलो तक पहुंच गई है।",
    },
    {
        "id": "HI-NEU-01",
        "lang": "hi",
        "type": "partial_claim",
        "expected": ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION,
        "premise": "स्वास्थ्य विभाग ने बदलते मौसम में बच्चों की देखभाल से संबंधित सामान्य परामर्श जारी किया।",
        "hypothesis": "राज्य के सभी विद्यालयों को 15 दिनों के लिए बंद करने का आदेश दिया गया है।",
    },

    # ── 3. Telugu Benchmark Cases ────────────────────────────────────────────
    {
        "id": "TE-SUP-01",
        "lang": "te",
        "type": "paraphrase",
        "expected": ClaimEvidenceRelation.SUPPORTS,
        "premise": "రాష్ట్రంలో రైతుల సంక్షేమం కోసం ప్రభుత్వం పంటల బీమా పథకాన్ని అమలు చేస్తోంది.",
        "hypothesis": "ప్రభుత్వం రైతు పంట బీమా పథకాన్ని అమలు చేస్తోంది.",
    },
    {
        "id": "TE-CON-01",
        "lang": "te",
        "type": "negation",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "తెలంగాణ పౌరసరఫరాల శాఖ రేషన్ బియ్యం పంపిణీ యథావిధిగా కొనసాగుతుందని, ఎలాంటి రద్దు లేదని తెలిపింది.",
        "hypothesis": "తెలంగాణలో రేషన్ బియ్యం పంపిణీ పథకాన్ని ప్రభుత్వం రద్దు చేసింది.",
    },
    {
        "id": "TE-CON-02",
        "lang": "te",
        "type": "number_change",
        "expected": ClaimEvidenceRelation.CONTRADICTS,
        "premise": "గ్రేటర్ హైదరాబాద్ పరిధిలో మెట్రో ఛార్జీలు 5 రూపాయలు మాత్రమే సవరించబడ్డాయి.",
        "hypothesis": "మెట్రో రైలు టికెట్ ధరలు ఏకంగా 50 రూపాయలు పెంచబడ్డాయి.",
    },
    {
        "id": "TE-NEU-01",
        "lang": "te",
        "type": "partial_claim",
        "expected": ClaimEvidenceRelation.NOT_ENOUGH_INFORMATION,
        "premise": "రాష్ట్రంలో భారీ వర్షాలు కురిసే అవకాశం ఉందని వాతావరణ శాఖ హెచ్చరించింది.",
        "hypothesis": "తీర ప్రాంతాల ప్రజలందరినీ ప్రభుత్వం ఖాళీ చేయించింది.",
    },
]


class TestMultilingualNLIBenchmarks:
    """Rigorous evaluation of textual entailment and claim-evidence verification."""

    @pytest.fixture(scope="class")
    def nli_model(self):
        return get_nli_model()

    def test_curated_nli_multilingual_benchmark(self, nli_model):
        """
        Evaluate all curated test pairs across EN, HI, and TE.
        Calculates per-language match rates and prints breakdown.
        """
        results_by_lang: dict[str, list[bool]] = {"en": [], "hi": [], "te": []}
        category_results: dict[str, list[bool]] = {}

        for test_case in CURATED_NLI_BENCHMARK_CASES:
            lang = test_case["lang"]
            c_type = test_case["type"]
            expected = test_case["expected"]

            # Predict relationship using NLI model
            nli_out = nli_model.predict(
                premise=test_case["premise"],
                hypothesis=test_case["hypothesis"],
                language=lang,
            )

            # Classify using production decision thresholding
            # High relevance proxy since these are pre-selected candidate pairs
            rel, score = classify_relation(relevance_score=0.85, nli_out=nli_out)

            is_correct = (rel == expected)
            results_by_lang[lang].append(is_correct)
            category_results.setdefault(c_type, []).append(is_correct)

            # Assert individual cases or log details
            print(f"[{test_case['id']}] expected={expected.value}, predicted={rel.value}, match={is_correct}")

        # Compute summary metrics
        print("\n--- Multilingual NLI Accuracy ---")
        for lang, vals in results_by_lang.items():
            acc = sum(vals) / len(vals)
            print(f"Language [{lang.upper()}]: {acc * 100:.1f}% ({sum(vals)}/{len(vals)})")
            assert acc >= 0.70, f"NLI accuracy for {lang} fell below gate threshold: {acc:.2f}"

        # Category breakdown
        print("\n--- Category Breakdown ---")
        for cat, vals in category_results.items():
            print(f"Category [{cat}]: {sum(vals)}/{len(vals)}")

    def test_false_support_adversarial_pairs(self, nli_model):
        """
        Critical safety test: Ensure that sentences with high word overlap but inverted
        polarity (negation) are NOT falsely classified as SUPPORTS.
        """
        adversarial_pairs = [
            ("The medicine is proven safe.", "The medicine is NOT safe.", "en"),
            ("The policy has been cancelled.", "The policy has NOT been cancelled.", "en"),
            ("सड़क निर्माण कार्य पूरा हो गया है।", "सड़क निर्माण कार्य पूरा नहीं हुआ है।", "hi"),
            ("ప్రాజెక్ట్ ప్రారంభమైంది.", "ప్రాజెక్ట్ ఇంకా ప్రారంభం కాలేదు.", "te"),
        ]

        for premise, hypothesis, lang in adversarial_pairs:
            nli_out = nli_model.predict(premise=premise, hypothesis=hypothesis, language=lang)
            rel, _ = classify_relation(relevance_score=0.90, nli_out=nli_out)
            assert rel != ClaimEvidenceRelation.SUPPORTS, (
                f"Safety violation: Negated claim was falsely classified as SUPPORTS! "
                f"Premise: '{premise}', Hypothesis: '{hypothesis}'"
            )
