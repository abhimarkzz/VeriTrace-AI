"""
Classifier interface and XLM-RoBERTa implementation.

Defines the VerificationClassifier protocol so the system can swap between:
- Local inference (XLMRobertaClassifier)
- GPU inference
- Hosted inference (API-based)

Without changing any frontend or service code.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# VeriTrace canonical labels — must match schemas.py order
LABEL_NAMES = [
    "SUPPORTED",
    "POTENTIALLY_MISLEADING",
    "INSUFFICIENT_EVIDENCE",
    "CONFLICTING_EVIDENCE",
]


@dataclass
class ClassificationResult:
    """Output contract for all classifiers."""
    label: str
    probabilities: dict[str, float]
    model_name: str
    model_version: str
    inference_time_ms: float

    def to_dict(self) -> dict:
        """Serialize to standard contract dictionary."""
        return {
            "label": self.label,
            "probabilities": self.probabilities,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "inference_time_ms": self.inference_time_ms,
        }


@runtime_checkable
class VerificationClassifier(Protocol):
    """Interface for verification classifiers."""

    def predict(self, claim: str) -> ClassificationResult:
        """Classify a single claim."""
        ...

    def predict_batch(self, claims: list[str]) -> list[ClassificationResult]:
        """Classify multiple claims."""
        ...

    @property
    def model_info(self) -> dict:
        """Return model metadata."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the classifier is ready for inference."""
        ...


class XLMRobertaClassifier:
    """
    XLM-RoBERTa sequence classifier.

    Uses a fine-tuned or base model with a classification head.
    Does NOT use raw masked-language modeling as a classifier.
    """

    def __init__(
        self,
        model: Any,
        tokenizer: Any,
        model_name: str,
        model_version: str,
        device: str = "cpu",
        max_length: int = 256,
        label_names: list[str] | None = None,
    ):
        self._model = model
        self._tokenizer = tokenizer
        self._model_name = model_name
        self._model_version = model_version
        self._device = device
        self._max_length = max_length
        self._label_names = label_names or LABEL_NAMES

    @property
    def is_available(self) -> bool:
        return self._model is not None

    @property
    def model_info(self) -> dict:
        return {
            "model_name": self._model_name,
            "model_version": self._model_version,
            "device": self._device,
            "max_length": self._max_length,
            "num_labels": len(self._label_names),
            "label_names": self._label_names,
        }

    def predict(self, claim: str) -> ClassificationResult:
        """Classify a single claim."""
        import torch

        start = time.monotonic()

        inputs = self._tokenizer(
            claim,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
            padding=True,
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).squeeze()

        elapsed = (time.monotonic() - start) * 1000

        # Build probabilities dict
        prob_dict = {}
        for i, label in enumerate(self._label_names):
            prob_dict[label] = round(float(probs[i]), 4)

        predicted_idx = int(probs.argmax())
        predicted_label = self._label_names[predicted_idx]

        return ClassificationResult(
            label=predicted_label,
            probabilities=prob_dict,
            model_name=self._model_name,
            model_version=self._model_version,
            inference_time_ms=round(elapsed, 1),
        )

    def predict_batch(self, claims: list[str]) -> list[ClassificationResult]:
        """Classify multiple claims."""
        return [self.predict(c) for c in claims]


class UnavailableClassifier:
    """
    Placeholder classifier returned when ML is unavailable.

    Never produces fake predictions — always returns ML_UNAVAILABLE.
    """

    def __init__(self, reason: str = "ML dependencies not available"):
        self._reason = reason

    @property
    def is_available(self) -> bool:
        return False

    @property
    def model_info(self) -> dict:
        return {
            "model_name": "none",
            "model_version": "none",
            "status": "ml_unavailable",
            "reason": self._reason,
        }

    def predict(self, claim: str) -> ClassificationResult:
        return ClassificationResult(
            label="ML_UNAVAILABLE",
            probabilities={},
            model_name="none",
            model_version="none",
            inference_time_ms=0.0,
        )

    def predict_batch(self, claims: list[str]) -> list[ClassificationResult]:
        return [self.predict(c) for c in claims]


class DeterministicTestClassifier:
    """
    Deterministic classifier for automated testing and CI/CD.

    Produces consistent, repeatable results without requiring GPU
    or downloading multi-gigabyte models. Uses a cryptographic hash
    of the input claim to deterministically assign probabilities.
    """

    def __init__(
        self,
        model_name: str = "deterministic-test-classifier",
        model_version: str = "v1-deterministic",
        label_names: list[str] | None = None,
        fixed_label: Optional[str] = None,
    ):
        self._model_name = model_name
        self._model_version = model_version
        self._label_names = label_names or LABEL_NAMES
        self._fixed_label = fixed_label

    @property
    def is_available(self) -> bool:
        return True

    @property
    def model_info(self) -> dict:
        return {
            "model_name": self._model_name,
            "model_version": self._model_version,
            "device": "cpu",
            "backend": "deterministic_test",
            "num_labels": len(self._label_names),
            "label_names": self._label_names,
        }

    def predict(self, claim: str) -> ClassificationResult:
        import hashlib

        start = time.monotonic()

        if self._fixed_label and self._fixed_label in self._label_names:
            predicted_label = self._fixed_label
            probs = {}
            for label in self._label_names:
                probs[label] = 0.85 if label == predicted_label else round(0.15 / (len(self._label_names) - 1), 4)
        else:
            # Deterministic hash to seed pseudo-probabilities
            h = int(hashlib.sha256(claim.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % len(self._label_names)
            predicted_label = self._label_names[idx]

            # Generate pseudo-probabilities that sum to ~1.0
            probs = {}
            remaining = 0.18
            step = remaining / (len(self._label_names) - 1)
            for i, label in enumerate(self._label_names):
                if i == idx:
                    probs[label] = 0.82
                else:
                    probs[label] = round(step, 4)

        elapsed = (time.monotonic() - start) * 1000

        return ClassificationResult(
            label=predicted_label,
            probabilities=probs,
            model_name=self._model_name,
            model_version=self._model_version,
            inference_time_ms=round(elapsed, 2),
        )

    def predict_batch(self, claims: list[str]) -> list[ClassificationResult]:
        return [self.predict(c) for c in claims]


class HostedInferenceClassifier:
    """
    Hosted inference classifier that calls an external HTTP API.

    Enables switching between local and hosted GPU infrastructure
    (e.g., HuggingFace Inference Endpoints, vLLM, or Triton server)
    without changing frontend code.
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        model_name: str = "hosted-xlm-roberta",
        model_version: str = "hosted-v1",
        label_names: list[str] | None = None,
        timeout: float = 10.0,
    ):
        self._endpoint_url = endpoint_url
        self._api_key = api_key
        self._model_name = model_name
        self._model_version = model_version
        self._label_names = label_names or LABEL_NAMES
        self._timeout = timeout

    @property
    def is_available(self) -> bool:
        return bool(self._endpoint_url)

    @property
    def model_info(self) -> dict:
        return {
            "model_name": self._model_name,
            "model_version": self._model_version,
            "device": "hosted_endpoint",
            "backend": "hosted",
            "endpoint_url": self._endpoint_url,
            "num_labels": len(self._label_names),
        }

    def predict(self, claim: str) -> ClassificationResult:
        import httpx

        start = time.monotonic()
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {"inputs": claim}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self._endpoint_url, json=payload, headers=headers)
                if response.status_code >= 400:
                    raise RuntimeError(f"HTTP error {response.status_code}: {response.text}")
                data = response.json()

            elapsed = (time.monotonic() - start) * 1000

            # Parse HuggingFace or custom response format
            probs = {}
            predicted_label = "INSUFFICIENT_EVIDENCE"

            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, list):
                    first = first[0]
                if isinstance(first, dict) and "label" in first:
                    predicted_label = first.get("label", predicted_label)
                    for item in (data[0] if isinstance(data[0], list) else data):
                        if isinstance(item, dict) and "label" in item and "score" in item:
                            probs[item["label"]] = round(float(item["score"]), 4)
            elif isinstance(data, dict):
                predicted_label = data.get("label", predicted_label)
                probs = data.get("probabilities", {})

            return ClassificationResult(
                label=predicted_label,
                probabilities=probs,
                model_name=self._model_name,
                model_version=self._model_version,
                inference_time_ms=round(elapsed, 1),
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            logger.error("Hosted inference failed: %s", e)
            return ClassificationResult(
                label="ML_UNAVAILABLE",
                probabilities={},
                model_name=self._model_name,
                model_version=self._model_version,
                inference_time_ms=round(elapsed, 1),
            )

    def predict_batch(self, claims: list[str]) -> list[ClassificationResult]:
        return [self.predict(c) for c in claims]

