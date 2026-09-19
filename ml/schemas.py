"""
Common normalized schema for all fact-verification datasets.

Every dataset record is normalized into this schema before
splitting, training, or evaluation. Original labels are always
preserved alongside the mapped VeriTrace labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class VeriTraceLabel(str, Enum):
    """VeriTrace canonical verification labels."""
    SUPPORTED = "SUPPORTED"
    POTENTIALLY_MISLEADING = "POTENTIALLY_MISLEADING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class DatasetSource(str, Enum):
    """Known dataset sources."""
    XFACT = "xfact"
    FEVER = "fever"
    AVERITEC = "averitec"


# ── Label Mappings ──────────────────────────────────────────────────────
# Each mapping is explicit and documented. Original labels are NEVER
# silently equated — they are preserved in the `label` field.

LABEL_MAPPINGS: dict[str, dict[str, VeriTraceLabel]] = {
    "xfact": {
        "true": VeriTraceLabel.SUPPORTED,
        "mostly_true": VeriTraceLabel.SUPPORTED,
        "half_true": VeriTraceLabel.CONFLICTING_EVIDENCE,
        "mostly_false": VeriTraceLabel.POTENTIALLY_MISLEADING,
        "false": VeriTraceLabel.POTENTIALLY_MISLEADING,
        "unverifiable": VeriTraceLabel.INSUFFICIENT_EVIDENCE,
        "other": VeriTraceLabel.INSUFFICIENT_EVIDENCE,
    },
    "fever": {
        "SUPPORTS": VeriTraceLabel.SUPPORTED,
        "REFUTES": VeriTraceLabel.POTENTIALLY_MISLEADING,
        "NOT ENOUGH INFO": VeriTraceLabel.INSUFFICIENT_EVIDENCE,
    },
    "averitec": {
        "Supported": VeriTraceLabel.SUPPORTED,
        "Refuted": VeriTraceLabel.POTENTIALLY_MISLEADING,
        "Not Enough Evidence": VeriTraceLabel.INSUFFICIENT_EVIDENCE,
        "Conflicting Evidence/Cherry-picking": VeriTraceLabel.CONFLICTING_EVIDENCE,
    },
}


def map_label(dataset: str, original_label: str) -> VeriTraceLabel:
    """
    Map an original dataset label to the VeriTrace canonical label.

    Raises ValueError if the label is unknown — never silently drops.
    """
    mapping = LABEL_MAPPINGS.get(dataset)
    if mapping is None:
        raise ValueError(f"Unknown dataset: {dataset}")
    mapped = mapping.get(original_label)
    if mapped is None:
        raise ValueError(
            f"Unknown label '{original_label}' for dataset '{dataset}'. "
            f"Known labels: {list(mapping.keys())}"
        )
    return mapped


@dataclass
class EvidenceRecord:
    """A single evidence item attached to a claim."""
    title: str = ""
    snippet: str = ""
    url: str = ""


@dataclass
class NormalizedClaim:
    """
    Common normalized record for all datasets.

    Fields:
        id:           Unique ID in format "{dataset}_{original_id}"
        claim:        The factual claim text
        label:        Original dataset label (preserved as-is)
        mapped_label: VeriTrace canonical label (explicit mapping)
        language:     ISO 639-1 language code
        evidence:     List of evidence records
        source:       Original source attribution
        dataset:      Dataset name ("xfact", "fever", "averitec")
    """
    id: str
    claim: str
    label: str
    mapped_label: str
    language: str
    evidence: list[dict] = field(default_factory=list)
    source: str = ""
    dataset: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict) -> NormalizedClaim:
        return cls(**d)

    @classmethod
    def from_json(cls, s: str) -> NormalizedClaim:
        return cls.from_dict(json.loads(s))

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors = []
        if not self.id:
            errors.append("Missing id")
        if not self.claim or not self.claim.strip():
            errors.append("Missing or blank claim")
        if not self.label:
            errors.append("Missing original label")
        if not self.mapped_label:
            errors.append("Missing mapped_label")
        if self.mapped_label and self.mapped_label not in [v.value for v in VeriTraceLabel]:
            errors.append(f"Invalid mapped_label: {self.mapped_label}")
        if not self.language:
            errors.append("Missing language")
        if not self.dataset:
            errors.append("Missing dataset")
        if self.dataset and self.dataset not in [d.value for d in DatasetSource]:
            errors.append(f"Invalid dataset: {self.dataset}")
        return errors
