"""
Model loader — handles downloading and caching HuggingFace models.

Gracefully returns ML_UNAVAILABLE if torch or transformers
cannot be imported, or if model download fails.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    LOADED = "loaded"
    LOADING = "loading"
    ML_UNAVAILABLE = "ml_unavailable"
    DOWNLOAD_FAILED = "download_failed"
    INVALID_PATH = "invalid_path"


@dataclass
class ModelInfo:
    """Metadata about a loaded model."""
    model_name: str
    model_version: str
    device: str
    max_length: int
    num_labels: int
    status: ModelStatus
    load_time_ms: float = 0.0
    error: Optional[str] = None


def _resolve_device(requested: str) -> str:
    """Resolve device with graceful fallback to CPU."""
    if not requested or requested.lower() == "cpu":
        return "cpu"

    req = requested.lower()
    try:
        import torch
        if req == "auto":
            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        elif req == "cuda":
            if torch.cuda.is_available():
                return "cuda"
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            return "cpu"
        elif req == "mps":
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            logger.warning("MPS requested but not available. Falling back to CPU.")
            return "cpu"
    except (ImportError, Exception):
        pass

    if req not in ("cpu", "auto", "cuda", "mps"):
        logger.warning("Unknown device '%s' requested. Falling back to CPU.", requested)
    return "cpu"


def load_sequence_classifier(
    model_name: str,
    num_labels: int = 4,
    device: str = "auto",
    max_length: int = 256,
) -> tuple[Any, Any, ModelInfo]:
    """
    Load a HuggingFace sequence classification model + tokenizer.

    Returns (model, tokenizer, info).
    On failure, returns (None, None, info) with status != LOADED.
    """
    resolved_device = _resolve_device(device)
    start = time.monotonic()

    # Check for empty or malformed path
    if not model_name or not model_name.strip():
        return None, None, ModelInfo(
            model_name=model_name or "",
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.INVALID_PATH,
            error="Model name or path cannot be empty",
        )

    # Check for non-existent local file/dir path
    if model_name.startswith(("/", "./", "../", "~")) and not os.path.exists(os.path.expanduser(model_name)):
        return None, None, ModelInfo(
            model_name=model_name,
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.INVALID_PATH,
            error=f"Local model path does not exist: {model_name}",
        )

    # Check if transformers is available
    try:
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            AutoConfig,
        )
    except ImportError:
        logger.error("transformers not installed — ML inference unavailable")
        return None, None, ModelInfo(
            model_name=model_name,
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.ML_UNAVAILABLE,
            error="transformers not installed. Install with: pip install transformers",
        )

    # Check if torch is available
    try:
        import torch  # noqa: F401
    except ImportError:
        logger.error("PyTorch not installed — ML inference unavailable")
        return None, None, ModelInfo(
            model_name=model_name,
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.ML_UNAVAILABLE,
            error="PyTorch not installed. Install with: pip install torch",
        )

    # Load model
    try:
        logger.info("Loading model '%s' on %s...", model_name, resolved_device)

        tokenizer = AutoTokenizer.from_pretrained(model_name)


        # Try loading with existing config first (fine-tuned checkpoint)
        try:
            config = AutoConfig.from_pretrained(model_name)
            if config.num_labels != num_labels:
                logger.info(
                    "Model has %d labels, overriding to %d",
                    config.num_labels, num_labels,
                )
                model = AutoModelForSequenceClassification.from_pretrained(
                    model_name,
                    num_labels=num_labels,
                    ignore_mismatched_sizes=True,
                )
            else:
                model = AutoModelForSequenceClassification.from_pretrained(model_name)
        except Exception:
            # Base model without classification head — add one
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=num_labels,
                ignore_mismatched_sizes=True,
            )

        model.to(resolved_device)
        model.eval()

        elapsed = (time.monotonic() - start) * 1000
        version = getattr(model.config, "_name_or_path", model_name)

        logger.info(
            "Model loaded: %s (%.0fms, device=%s, labels=%d)",
            model_name, elapsed, resolved_device, num_labels,
        )

        return model, tokenizer, ModelInfo(
            model_name=model_name,
            model_version=version,
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.LOADED,
            load_time_ms=round(elapsed, 1),
        )

    except OSError as e:
        elapsed = (time.monotonic() - start) * 1000
        err_msg = str(e)
        logger.error("Model download/load failed: %s", err_msg)
        is_invalid = any(kw in err_msg.lower() for kw in ("not a valid", "is not a local folder", "cannot find", "not found"))
        status = ModelStatus.INVALID_PATH if is_invalid else ModelStatus.DOWNLOAD_FAILED
        return None, None, ModelInfo(
            model_name=model_name,
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=status,
            load_time_ms=round(elapsed, 1),
            error=err_msg,
        )
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        logger.exception("Unexpected error loading model: %s", e)
        return None, None, ModelInfo(
            model_name=model_name,
            model_version="unknown",
            device=resolved_device,
            max_length=max_length,
            num_labels=num_labels,
            status=ModelStatus.ML_UNAVAILABLE,
            load_time_ms=round(elapsed, 1),
            error=str(e),
        )
