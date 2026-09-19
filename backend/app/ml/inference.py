"""
Inference service — high-level API for running classification.

This is the single entry point that analysis_service.py calls.
Handles the classifier being unavailable gracefully.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.ml.classifier import ClassificationResult
from app.ml.model_registry import registry

logger = logging.getLogger(__name__)


def classify_claim(claim: str) -> ClassificationResult:
    """
    Classify a claim using the loaded model.

    Returns ML_UNAVAILABLE result if no model is loaded,
    never silently falls back to mock data.
    """
    classifier = registry.classifier
    return classifier.predict(claim)


def classify_claims_batch(claims: list[str]) -> list[ClassificationResult]:
    """Classify multiple claims."""
    classifier = registry.classifier
    return classifier.predict_batch(claims)


def is_ml_available() -> bool:
    """Check if ML inference is available."""
    return registry.is_loaded


def get_model_health() -> dict:
    """Get model health status for the health endpoint."""
    return registry.health_status()
