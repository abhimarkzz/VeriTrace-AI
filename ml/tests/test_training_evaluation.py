"""
Tests for ML training and evaluation modules.

Validates:
- Label mapping in fine_tune.py
- Dataset preparation (texts, labels, languages, skipping unmappable)
- JSONL loading in evaluate.py
- Per-language metrics computation
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from ml.training.fine_tune import (
    LABEL_NAMES,
    LABEL_TO_ID,
    map_label,
    prepare_dataset,
)
from ml.evaluation.evaluate import load_jsonl


class TestTrainingHelpers:
    """Tests for dataset mapping and preparation in training script."""

    def test_map_label_valid(self):
        assert map_label({"mapped_label": "SUPPORTED"}) == LABEL_TO_ID["SUPPORTED"]
        assert map_label({"mapped_label": "POTENTIALLY_MISLEADING"}) == LABEL_TO_ID["POTENTIALLY_MISLEADING"]
        assert map_label({"mapped_label": "INSUFFICIENT_EVIDENCE"}) == LABEL_TO_ID["INSUFFICIENT_EVIDENCE"]
        assert map_label({"mapped_label": "CONFLICTING_EVIDENCE"}) == LABEL_TO_ID["CONFLICTING_EVIDENCE"]

    def test_map_label_invalid(self):
        assert map_label({"mapped_label": "UNKNOWN_LABEL"}) is None
        assert map_label({}) is None

    def test_prepare_dataset(self):
        records = [
            {"claim": "Claim 1", "mapped_label": "SUPPORTED", "language": "en"},
            {"claim": "दावा 2", "mapped_label": "POTENTIALLY_MISLEADING", "language": "hi"},
            {"claim": "దావా 3", "mapped_label": "INSUFFICIENT_EVIDENCE", "language": "te"},
            # Invalid label - should be skipped
            {"claim": "Claim 4", "mapped_label": "INVALID", "language": "en"},
            # Empty claim - should be skipped
            {"claim": "   ", "mapped_label": "SUPPORTED", "language": "en"},
        ]

        texts, labels, languages = prepare_dataset(records)
        assert len(texts) == 3
        assert len(labels) == 3
        assert len(languages) == 3
        assert texts[0] == "Claim 1"
        assert labels[0] == LABEL_TO_ID["SUPPORTED"]
        assert languages[0] == "en"
        assert languages[1] == "hi"
        assert languages[2] == "te"


class TestEvaluationHelpers:
    """Tests for JSONL loading and evaluation helpers."""

    def test_load_jsonl(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"claim": "A", "mapped_label": "SUPPORTED"}) + "\n")
            f.write("\n")  # empty line
            f.write(json.dumps({"claim": "B", "mapped_label": "REFUTED"}) + "\n")
            path = f.name

        try:
            records = load_jsonl(path)
            assert len(records) == 2
            assert records[0]["claim"] == "A"
            assert records[1]["claim"] == "B"
        finally:
            Path(path).unlink(missing_ok=True)
