"""
Comprehensive tests for VeriTrace ML inference subsystem (STEP 5).

Covers:
- VeriTraceTokenizer tests (multilingual, encode/decode, token counting)
- Long text truncation
- Unknown / unsupported language handling
- Model loader path validation (malformed paths)
- Device resolution & CPU fallback
- Controlled ML_UNAVAILABLE state (no silent mock fakes)
- Deterministic inference tests
- Hosted inference abstraction
- Model registry lifecycle and health reporting
- Analysis service integration with ML model
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import Response

from app.ml.classifier import (
    ClassificationResult,
    DeterministicTestClassifier,
    HostedInferenceClassifier,
    UnavailableClassifier,
    VerificationClassifier,
    LABEL_NAMES,
)
from app.ml.inference import (
    classify_claim,
    classify_claims_batch,
    get_model_health,
    is_ml_available,
)
from app.ml.model_loader import (
    ModelInfo,
    ModelStatus,
    _resolve_device,
    load_sequence_classifier,
)
from app.ml.model_registry import ModelRegistry, registry
from app.ml.tokenizer import VeriTraceTokenizer
from app.schemas.analysis import AnalysisRequest, Assessment, Language
from app.services.analysis_service import analyze_claim


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tokenizer Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVeriTraceTokenizer:
    """Tests for VeriTraceTokenizer with HuggingFace AutoTokenizer."""

    @pytest.fixture(scope="class")
    def tokenizer(self):
        """Loads XLM-RoBERTa tokenizer (cached locally)."""
        try:
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("transformers not installed in environment")
        return VeriTraceTokenizer.from_pretrained("xlm-roberta-base", max_length=64)

    def test_multilingual_tokenization(self, tokenizer):
        """Verify tokenization across required languages: English, Hindi, Telugu."""
        texts = {
            "en": "WHO approved a new malaria vaccine for distribution.",
            "hi": "विश्व स्वास्थ्य संगठन ने मलेरिया के नए टीके को मंजूरी दी।",
            "te": "ప్రపంచ ఆరోగ్య సంస్థ కొత్త మలేరియా వ్యాక్సిన్‌ను ఆమోదించింది.",
        }

        for lang, text in texts.items():
            encoded = tokenizer.encode(text)
            assert isinstance(encoded, list)
            assert len(encoded) > 0, f"Failed for language: {lang}"
            assert tokenizer.get_token_count(text) == len(encoded)

            decoded = tokenizer.decode(encoded)
            assert len(decoded) > 0

    def test_long_text_truncation(self, tokenizer):
        """Verify that input exceeding max_length is detected and truncated."""
        # Create a text with > 100 words which exceeds max_length=64
        long_text = "Breaking news: " + " ".join(["verified evidence claim"] * 80)

        assert tokenizer.would_truncate(long_text) is True
        assert tokenizer.get_token_count(long_text) > 64

        # Tokenize with truncation
        tokens = tokenizer.encode(long_text)
        assert len(tokens) <= 64, f"Expected <= 64 tokens, got {len(tokens)}"

        # Short text should NOT truncate
        short_text = "Short claim statement."
        assert tokenizer.would_truncate(short_text) is False
        assert len(tokenizer.encode(short_text)) < 64

    def test_unknown_language_tokenization(self, tokenizer):
        """Verify tokenizer gracefully handles unknown/rare languages without failure."""
        unknown_texts = [
            # Icelandic
            "Þetta er óstaðfest fullyrðing um bóluefni og heilsugæslu.",
            # Swahili
            "Shirika la Afya Duniani limeidhinisha chanjo mpya ya malaria.",
            # Emojis and mixed symbols
            "🚨🔥 Breaking: 100% cure discovered! 💉💊 Check this out!!!",
            # Made-up gibberish
            "Xylophonic flimflam barzoop quuxnor plover.",
        ]

        for text in unknown_texts:
            encoded = tokenizer.encode(text)
            assert isinstance(encoded, list)
            assert len(encoded) > 0
            decoded = tokenizer.decode(encoded)
            assert isinstance(decoded, str)

    def test_batch_tokenization(self, tokenizer):
        """Verify batch tokenization returns matching batch size."""
        batch = [
            "Claim 1: Solar flare causes grid outage.",
            "Claim 2: Government announces new policy.",
            "Claim 3: Drinking water reduces fatigue.",
        ]
        result = tokenizer.tokenize_batch(batch, return_tensors=None)
        assert "input_ids" in result
        assert len(result["input_ids"]) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 2. Model Loader & Fallback Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestModelLoader:
    """Tests for model loading, error handling, and device resolution."""

    def test_malformed_model_path_empty(self):
        """Empty or whitespace model path returns INVALID_PATH."""
        model, tok, info = load_sequence_classifier("")
        assert model is None
        assert tok is None
        assert info.status == ModelStatus.INVALID_PATH
        assert "cannot be empty" in info.error

        model2, tok2, info2 = load_sequence_classifier("   ")
        assert info2.status == ModelStatus.INVALID_PATH

    def test_malformed_model_path_nonexistent_local(self):
        """Nonexistent local path returns INVALID_PATH."""
        model, tok, info = load_sequence_classifier("/nonexistent/local/path/to/weights")
        assert model is None
        assert tok is None
        assert info.status == ModelStatus.INVALID_PATH
        assert "does not exist" in info.error

    def test_cpu_fallback_explicit(self):
        """Explicit CPU request always resolves to 'cpu'."""
        assert _resolve_device("cpu") == "cpu"
        assert _resolve_device("CPU") == "cpu"
        assert _resolve_device("") == "cpu"

    def test_cpu_fallback_unavailable_cuda(self):
        """Requesting CUDA on a system without CUDA falls back to CPU."""
        device = _resolve_device("cuda")
        assert device == "cpu"

    def test_cpu_fallback_unknown_device(self):
        """Requesting an unknown device falls back to CPU."""
        device = _resolve_device("quantum_processing_unit")
        assert device == "cpu"

    def test_controlled_ml_unavailable_when_torch_missing(self):
        """If PyTorch cannot be imported, loader returns ML_UNAVAILABLE (no crash)."""
        with patch.dict("sys.modules", {"torch": None}):
            model, tok, info = load_sequence_classifier("FacebookAI/xlm-roberta-base")
            assert model is None
            assert tok is None
            assert info.status == ModelStatus.ML_UNAVAILABLE
            assert "PyTorch not installed" in info.error or "transformers not installed" in info.error


# ─────────────────────────────────────────────────────────────────────────────
# 3. Classifier Contracts & Implementations
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifiers:
    """Tests for classifier protocol implementations and output contract."""

    def test_classification_result_contract(self):
        """Verify ClassificationResult to_dict matches the required contract."""
        res = ClassificationResult(
            label="SUPPORTED",
            probabilities={"SUPPORTED": 0.85, "POTENTIALLY_MISLEADING": 0.15},
            model_name="xlm-roberta-base",
            model_version="v1.0",
            inference_time_ms=12.5,
        )
        d = res.to_dict()
        assert d["label"] == "SUPPORTED"
        assert d["probabilities"] == {"SUPPORTED": 0.85, "POTENTIALLY_MISLEADING": 0.15}
        assert d["model_name"] == "xlm-roberta-base"
        assert d["model_version"] == "v1.0"
        assert d["inference_time_ms"] == 12.5

    def test_unavailable_classifier_returns_ml_unavailable(self):
        """UnavailableClassifier must always return ML_UNAVAILABLE with empty probabilities."""
        classifier = UnavailableClassifier(reason="Model weights missing")
        assert classifier.is_available is False
        assert classifier.model_info["status"] == "ml_unavailable"

        result = classifier.predict("Any claim statement")
        assert result.label == "ML_UNAVAILABLE"
        assert result.probabilities == {}
        assert result.model_name == "none"
        assert result.inference_time_ms == 0.0

        # Batch prediction
        batch_results = classifier.predict_batch(["Claim 1", "Claim 2"])
        assert len(batch_results) == 2
        assert all(r.label == "ML_UNAVAILABLE" for r in batch_results)

    def test_deterministic_inference(self):
        """DeterministicTestClassifier must return identical results for identical input."""
        classifier = DeterministicTestClassifier(
            model_name="veritrace-deterministic",
            model_version="det-v1",
        )
        assert classifier.is_available is True
        assert isinstance(classifier, VerificationClassifier)

        claim = "The Reserve Bank of India lowered repo rate by 25 basis points."

        # Run inference 5 times
        results = [classifier.predict(claim) for _ in range(5)]

        # Verify all runs produce identical labels and probabilities
        first = results[0]
        assert first.label in LABEL_NAMES
        assert len(first.probabilities) == 4
        assert first.model_name == "veritrace-deterministic"

        for r in results[1:]:
            assert r.label == first.label
            assert r.probabilities == first.probabilities

    def test_deterministic_fixed_label(self):
        """Fixed label configuration forces the specified label."""
        classifier = DeterministicTestClassifier(fixed_label="POTENTIALLY_MISLEADING")
        result = classifier.predict("Random claim about Mars")
        assert result.label == "POTENTIALLY_MISLEADING"
        assert result.probabilities["POTENTIALLY_MISLEADING"] == 0.85

    def test_hosted_inference_classifier_success(self):
        """HostedInferenceClassifier parses HTTP API responses."""
        classifier = HostedInferenceClassifier(
            endpoint_url="http://mock-inference-service/predict",
            api_key="secret-key",
            model_name="hosted-xlm-roberta",
        )
        assert classifier.is_available is True

        mock_response = [
            [
                {"label": "SUPPORTED", "score": 0.92},
                {"label": "POTENTIALLY_MISLEADING", "score": 0.08},
            ]
        ]

        with patch("httpx.Client.post") as mock_post:
            mock_post.return_value = Response(200, json=mock_response)
            result = classifier.predict("Verified statement.")

            assert result.label == "SUPPORTED"
            assert result.probabilities["SUPPORTED"] == 0.92
            assert result.model_name == "hosted-xlm-roberta"

    def test_hosted_inference_classifier_network_failure(self):
        """Hosted inference network failure gracefully returns ML_UNAVAILABLE."""
        classifier = HostedInferenceClassifier(
            endpoint_url="http://unreachable-host:9999/predict",
        )
        with patch("httpx.Client.post", side_effect=Exception("Connection refused")):
            result = classifier.predict("Any claim.")
            assert result.label == "ML_UNAVAILABLE"
            assert result.probabilities == {}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Model Registry & High-Level Inference Service
# ─────────────────────────────────────────────────────────────────────────────

class TestModelRegistryAndInference:
    """Tests for the global registry and inference facade."""

    def setup_method(self):
        """Unload before each test to guarantee clean slate."""
        registry.unload()

    def teardown_method(self):
        """Unload after each test."""
        registry.unload()

    def test_inference_when_no_model_loaded(self):
        """When no model is loaded, inference returns ML_UNAVAILABLE."""
        assert is_ml_available() is False
        health = get_model_health()
        assert health["status"] == "not_loaded"

        result = classify_claim("Test claim")
        assert result.label == "ML_UNAVAILABLE"
        assert result.probabilities == {}

    def test_register_and_classify(self):
        """Registering a mock/test model enables classification."""
        info = registry.load_mock_model(
            model_name="test-xlmr",
            model_version="test-1.0",
            fixed_label="SUPPORTED",
        )
        assert info.status == ModelStatus.LOADED
        assert is_ml_available() is True

        health = get_model_health()
        assert health["status"] == "loaded"
        assert health["model"] == "test-xlmr"

        result = classify_claim("India launched its third lunar exploration mission.")
        assert result.label == "SUPPORTED"
        assert result.model_name == "test-xlmr"
        assert result.probabilities["SUPPORTED"] == 0.85

    def test_batch_classification(self):
        """classify_claims_batch runs multiple claims."""
        registry.load_mock_model(model_name="batch-xlmr")
        claims = [
            "Vaccines cause 5G connectivity.",
            "Water boils at 100 degrees Celsius at sea level.",
            "A new transit corridor was inaugurated today.",
        ]
        results = classify_claims_batch(claims)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, ClassificationResult)
            assert r.model_name == "batch-xlmr"

    def test_unload_model(self):
        """Unloading clears the classifier and marks ML unavailable."""
        registry.load_mock_model()
        assert is_ml_available() is True

        registry.unload()
        assert is_ml_available() is False
        result = classify_claim("Post-unload claim")
        assert result.label == "ML_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Pipeline Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineIntegration:
    """Tests integration between analysis_service and the ML inference module."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        registry.unload()
        yield
        registry.unload()

    @pytest.mark.asyncio
    async def test_analyze_claim_with_ml_unavailable(self, async_session):
        """When ML is unavailable, pipeline completes honestly without fake predictions."""
        request = AnalysisRequest(
            text="WHO reported a decrease in active cholera cases across the region.",
            language=Language.EN,
        )
        async with async_session() as session:
            response = await analyze_claim(request, session=session)

        # ML was unavailable, so assessment should be INSUFFICIENT_EVIDENCE
        assert response.assessment == Assessment.INSUFFICIENT_EVIDENCE
        assert response.confidence is None
        assert "No ML model is loaded" in response.explanation

    @pytest.mark.asyncio
    async def test_analyze_claim_with_ml_available(self, async_session):
        """When ML is loaded, analyze_claim uses model prediction and records model_run."""
        registry.load_mock_model(
            model_name="FacebookAI/xlm-roberta-base",
            model_version="xlmr-v1.0",
            fixed_label="SUPPORTED",
        )

        request = AnalysisRequest(
            text="WHO declared the end of the public health emergency of international concern.",
            language=Language.EN,
        )
        async with async_session() as session:
            response = await analyze_claim(request, session=session)

        assert response.assessment == Assessment.SUPPORTED
        assert response.confidence is not None
        assert response.confidence > 0.8
        assert response.confidence_breakdown is not None
        assert response.confidence_breakdown.model_confidence == 0.85
        assert "SUPPORTED" in response.confidence_breakdown.probabilities
        assert response.confidence_breakdown.probabilities["SUPPORTED"] == 0.85

