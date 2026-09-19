"""
Tests for the ML dataset pipeline.

Covers: schema validation, label mapping, duplicate detection,
leakage checks, and reproducibility.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
import tempfile

from ml.schemas import (
    NormalizedClaim,
    VeriTraceLabel,
    DatasetSource,
    LABEL_MAPPINGS,
    map_label,
)
from ml.datasets.validate import (
    find_exact_duplicates,
    find_near_duplicates,
    validate_records,
)
from ml.datasets.split import (
    deduplicate,
    stratified_split,
    check_leakage,
)


# ── Schema Validation ────────────────────────────────────────────────────


class TestNormalizedClaim:
    def test_valid_record(self):
        claim = NormalizedClaim(
            id="test_1", claim="Earth is round", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en", dataset="fever",
        )
        errors = claim.validate()
        assert errors == []

    def test_missing_id(self):
        claim = NormalizedClaim(
            id="", claim="A claim", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en", dataset="fever",
        )
        assert "Missing id" in claim.validate()

    def test_missing_claim(self):
        claim = NormalizedClaim(
            id="test_1", claim="", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en", dataset="fever",
        )
        assert "Missing or blank claim" in claim.validate()

    def test_blank_claim(self):
        claim = NormalizedClaim(
            id="test_1", claim="   ", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en", dataset="fever",
        )
        assert "Missing or blank claim" in claim.validate()

    def test_missing_label(self):
        claim = NormalizedClaim(
            id="test_1", claim="A claim", label="",
            mapped_label="SUPPORTED", language="en", dataset="fever",
        )
        assert "Missing original label" in claim.validate()

    def test_invalid_mapped_label(self):
        claim = NormalizedClaim(
            id="test_1", claim="A claim", label="SUPPORTS",
            mapped_label="INVALID", language="en", dataset="fever",
        )
        errors = claim.validate()
        assert any("Invalid mapped_label" in e for e in errors)

    def test_invalid_dataset(self):
        claim = NormalizedClaim(
            id="test_1", claim="A claim", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en", dataset="unknown_ds",
        )
        errors = claim.validate()
        assert any("Invalid dataset" in e for e in errors)

    def test_to_json_roundtrip(self):
        claim = NormalizedClaim(
            id="test_1", claim="A claim", label="SUPPORTS",
            mapped_label="SUPPORTED", language="en",
            evidence=[{"title": "T"}], source="wiki", dataset="fever",
        )
        restored = NormalizedClaim.from_json(claim.to_json())
        assert restored.id == claim.id
        assert restored.claim == claim.claim
        assert restored.evidence == claim.evidence


# ── Label Mapping ────────────────────────────────────────────────────────


class TestLabelMapping:
    def test_fever_supports(self):
        assert map_label("fever", "SUPPORTS") == VeriTraceLabel.SUPPORTED

    def test_fever_refutes(self):
        assert map_label("fever", "REFUTES") == VeriTraceLabel.POTENTIALLY_MISLEADING

    def test_fever_nei(self):
        assert map_label("fever", "NOT ENOUGH INFO") == VeriTraceLabel.INSUFFICIENT_EVIDENCE

    def test_xfact_true(self):
        assert map_label("xfact", "true") == VeriTraceLabel.SUPPORTED

    def test_xfact_false(self):
        assert map_label("xfact", "false") == VeriTraceLabel.POTENTIALLY_MISLEADING

    def test_xfact_half_true(self):
        assert map_label("xfact", "half_true") == VeriTraceLabel.CONFLICTING_EVIDENCE

    def test_averitec_supported(self):
        assert map_label("averitec", "Supported") == VeriTraceLabel.SUPPORTED

    def test_averitec_conflicting(self):
        assert map_label("averitec", "Conflicting Evidence/Cherry-picking") == VeriTraceLabel.CONFLICTING_EVIDENCE

    def test_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset"):
            map_label("imaginary_ds", "SUPPORTS")

    def test_unknown_label_raises(self):
        with pytest.raises(ValueError, match="Unknown label"):
            map_label("fever", "UNKNOWN_LABEL")

    def test_all_fever_labels_mapped(self):
        for label in LABEL_MAPPINGS["fever"]:
            result = map_label("fever", label)
            assert isinstance(result, VeriTraceLabel)

    def test_all_xfact_labels_mapped(self):
        for label in LABEL_MAPPINGS["xfact"]:
            result = map_label("xfact", label)
            assert isinstance(result, VeriTraceLabel)

    def test_all_averitec_labels_mapped(self):
        for label in LABEL_MAPPINGS["averitec"]:
            result = map_label("averitec", label)
            assert isinstance(result, VeriTraceLabel)


# ── Duplicate Detection ──────────────────────────────────────────────────


class TestDuplicateDetection:
    def _make_claims(self, texts):
        return [
            NormalizedClaim(
                id=f"t_{i}", claim=t, label="SUPPORTS",
                mapped_label="SUPPORTED", language="en", dataset="fever",
            )
            for i, t in enumerate(texts)
        ]

    def test_no_duplicates(self):
        records = self._make_claims(["Claim A", "Claim B", "Claim C"])
        assert find_exact_duplicates(records) == []

    def test_exact_duplicate_found(self):
        records = self._make_claims(["Claim A", "Claim B", "Claim A"])
        dups = find_exact_duplicates(records)
        assert len(dups) == 1

    def test_near_duplicate_found(self):
        records = self._make_claims(["Claim A.", "claim a", "Claim B"])
        dups = find_near_duplicates(records)
        assert len(dups) == 1

    def test_deduplication_removes_exact(self):
        records = self._make_claims(["Claim A", "Claim B", "Claim A", "Claim C"])
        unique = deduplicate(records)
        assert len(unique) == 3


# ── Split & Leakage ─────────────────────────────────────────────────────


class TestSplitAndLeakage:
    def _make_dataset(self, n=100):
        labels = ["SUPPORTED", "POTENTIALLY_MISLEADING", "INSUFFICIENT_EVIDENCE"]
        langs = ["en", "hi"]
        return [
            NormalizedClaim(
                id=f"r_{i}", claim=f"Unique claim number {i}",
                label="SUPPORTS", mapped_label=labels[i % len(labels)],
                language=langs[i % len(langs)], dataset="fever",
            )
            for i in range(n)
        ]

    def test_split_sizes_approximate(self):
        records = self._make_dataset(100)
        splits = stratified_split(records)
        assert len(splits["train"]) > 0
        assert len(splits["val"]) > 0
        assert len(splits["test"]) > 0
        total = sum(len(s) for s in splits.values())
        assert total == 100

    def test_no_leakage(self):
        records = self._make_dataset(200)
        splits = stratified_split(records)
        errors = check_leakage(splits)
        assert errors == [], f"Leakage found: {errors}"

    def test_reproducibility(self):
        records = self._make_dataset(100)
        split1 = stratified_split(records, seed=42)
        split2 = stratified_split(records, seed=42)
        ids1 = [r.id for r in split1["train"]]
        ids2 = [r.id for r in split2["train"]]
        assert ids1 == ids2, "Same seed should produce identical splits"

    def test_different_seeds_differ(self):
        records = self._make_dataset(100)
        split1 = stratified_split(records, seed=42)
        split2 = stratified_split(records, seed=99)
        ids1 = [r.id for r in split1["train"]]
        ids2 = [r.id for r in split2["train"]]
        assert ids1 != ids2

    def test_validate_records_returns_report(self):
        records = self._make_dataset(10)
        report = validate_records(records)
        assert report["total_records"] == 10
        assert report["valid_records"] == 10
        assert "class_distribution_mapped" in report
        assert "language_distribution" in report
