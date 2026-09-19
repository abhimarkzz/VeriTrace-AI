"""
Model registry — singleton that manages loaded models.

Prevents duplicate loading. Provides model health status
for the /api/v1/health endpoint.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.ml.model_loader import ModelInfo, ModelStatus, load_sequence_classifier
from app.ml.classifier import (
    VerificationClassifier,
    XLMRobertaClassifier,
    UnavailableClassifier,
    DeterministicTestClassifier,
    HostedInferenceClassifier,
    LABEL_NAMES,
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Singleton registry for loaded ML models."""

    def __init__(self):
        self._classifier: VerificationClassifier | None = None
        self._model_info: Optional[ModelInfo] = None
        self._loaded_at: Optional[datetime] = None

    @property
    def classifier(self) -> VerificationClassifier:
        if self._classifier is None:
            return UnavailableClassifier("Model not loaded. Call load_model() first.")
        return self._classifier

    @property
    def is_loaded(self) -> bool:
        return (
            self._classifier is not None
            and self._classifier.is_available
        )

    @property
    def model_info(self) -> Optional[ModelInfo]:
        return self._model_info


    def health_status(self) -> dict:
        """Return model health for the health endpoint."""
        if self._model_info is None:
            return {"status": "not_loaded", "model": None}

        return {
            "status": self._model_info.status.value,
            "model": self._model_info.model_name,
            "device": self._model_info.device,
            "num_labels": self._model_info.num_labels,
            "load_time_ms": self._model_info.load_time_ms,
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
            "error": self._model_info.error,
        }

    def load_model(
        self,
        model_name: str,
        num_labels: int = 4,
        device: str = "auto",
        max_length: int = 256,
    ) -> ModelInfo:
        """
        Load a model into the registry.

        If already loaded with the same name, returns cached info.
        """
        if (
            self._model_info is not None
            and self._model_info.model_name == model_name
            and self._model_info.status == ModelStatus.LOADED
        ):
            logger.info("Model '%s' already loaded, skipping", model_name)
            return self._model_info

        model, tokenizer, info = load_sequence_classifier(
            model_name=model_name,
            num_labels=num_labels,
            device=device,
            max_length=max_length,
        )

        self._model_info = info
        self._loaded_at = datetime.now(timezone.utc)

        if info.status == ModelStatus.LOADED and model is not None:
            self._classifier = XLMRobertaClassifier(
                model=model,
                tokenizer=tokenizer,
                model_name=model_name,
                model_version=info.model_version,
                device=info.device,
                max_length=max_length,
                label_names=LABEL_NAMES,
            )
            logger.info("Model registered: %s", model_name)
        else:
            self._classifier = UnavailableClassifier(
                reason=info.error or f"Model status: {info.status.value}"
            )
            logger.warning(
                "Model unavailable: %s — %s", model_name, info.error
            )

        return info

    def register_classifier(
        self,
        classifier: VerificationClassifier,
        model_info: Optional[ModelInfo] = None,
    ) -> None:
        """Register an arbitrary classifier (e.g. for testing or custom inference)."""
        self._classifier = classifier
        if model_info is not None:
            self._model_info = model_info
        else:
            info = classifier.model_info
            self._model_info = ModelInfo(
                model_name=info.get("model_name", "custom"),
                model_version=info.get("model_version", "unknown"),
                device=info.get("device", "cpu"),
                max_length=info.get("max_length", 256),
                num_labels=info.get("num_labels", len(LABEL_NAMES)),
                status=ModelStatus.LOADED if classifier.is_available else ModelStatus.ML_UNAVAILABLE,
            )
        self._loaded_at = datetime.now(timezone.utc)
        logger.info("Custom classifier registered: %s", self._model_info.model_name)

    def load_mock_model(
        self,
        model_name: str = "mock-xlm-roberta",
        model_version: str = "v1-deterministic",
        fixed_label: Optional[str] = None,
    ) -> ModelInfo:
        """Load deterministic test classifier for local dev or automated tests."""
        classifier = DeterministicTestClassifier(
            model_name=model_name,
            model_version=model_version,
            fixed_label=fixed_label,
        )
        info = ModelInfo(
            model_name=model_name,
            model_version=model_version,
            device="cpu",
            max_length=256,
            num_labels=len(LABEL_NAMES),
            status=ModelStatus.LOADED,
        )
        self.register_classifier(classifier, info)
        return info

    def load_hosted_model(
        self,
        endpoint_url: str,
        api_key: Optional[str] = None,
        model_name: str = "hosted-xlm-roberta",
        model_version: str = "hosted-v1",
        timeout: float = 10.0,
    ) -> ModelInfo:
        """Load hosted inference classifier (calls external HTTP API)."""
        classifier = HostedInferenceClassifier(
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_name=model_name,
            model_version=model_version,
            timeout=timeout,
        )
        info = ModelInfo(
            model_name=model_name,
            model_version=model_version,
            device="hosted_endpoint",
            max_length=256,
            num_labels=len(LABEL_NAMES),
            status=ModelStatus.LOADED,
        )
        self.register_classifier(classifier, info)
        return info

    def unload(self):
        """Unload the current model."""
        self._classifier = None
        self._model_info = None
        self._loaded_at = None
        logger.info("Model unloaded")



# Global singleton
registry = ModelRegistry()
