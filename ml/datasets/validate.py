"""
Dataset validation and statistics reporting.

Reports: sample counts, class distribution, language distribution,
missing values, exact duplicates, and near-duplicates.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from ml.schemas import NormalizedClaim, VeriTraceLabel

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_normalized(path: Path) -> list[NormalizedClaim]:
    """Load NormalizedClaim records from JSONL."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(NormalizedClaim.from_json(line))
    return records


def find_exact_duplicates(records: list[NormalizedClaim]) -> list[tuple[str, str]]:
    """Find records with identical claim text. Returns pairs of (id1, id2)."""
    seen: dict[str, str] = {}
    duplicates = []
    for r in records:
        key = r.claim.strip()
        if key in seen:
            duplicates.append((seen[key], r.id))
        else:
            seen[key] = r.id
    return duplicates


def find_near_duplicates(records: list[NormalizedClaim]) -> list[tuple[str, str]]:
    """
    Find near-duplicate claims using normalized lowercase comparison.
    More aggressive than exact: strips punctuation and collapses whitespace.
    """
    import re
    seen: dict[str, str] = {}
    duplicates = []
    for r in records:
        key = re.sub(r"[^\w\s]", "", r.claim.lower().strip())
        key = " ".join(key.split())
        if key in seen:
            duplicates.append((seen[key], r.id))
        else:
            seen[key] = r.id
    return duplicates


def validate_records(records: list[NormalizedClaim]) -> dict:
    """Run full validation and return a structured report."""
    report = {
        "total_records": len(records),
        "valid_records": 0,
        "invalid_records": 0,
        "validation_errors": [],
        "class_distribution_original": {},
        "class_distribution_mapped": {},
        "language_distribution": {},
        "dataset_distribution": {},
        "missing_values": {"claim": 0, "label": 0, "language": 0, "evidence": 0},
        "exact_duplicates": 0,
        "near_duplicates": 0,
        "samples": [],
    }

    label_counter = Counter()
    mapped_counter = Counter()
    lang_counter = Counter()
    dataset_counter = Counter()

    for r in records:
        errors = r.validate()
        if errors:
            report["invalid_records"] += 1
            report["validation_errors"].extend(errors)
        else:
            report["valid_records"] += 1

        label_counter[r.label] += 1
        mapped_counter[r.mapped_label] += 1
        lang_counter[r.language] += 1
        dataset_counter[r.dataset] += 1

        if not r.claim.strip():
            report["missing_values"]["claim"] += 1
        if not r.label:
            report["missing_values"]["label"] += 1
        if not r.language:
            report["missing_values"]["language"] += 1
        if not r.evidence:
            report["missing_values"]["evidence"] += 1

    report["class_distribution_original"] = dict(label_counter.most_common())
    report["class_distribution_mapped"] = dict(mapped_counter.most_common())
    report["language_distribution"] = dict(lang_counter.most_common())
    report["dataset_distribution"] = dict(dataset_counter.most_common())

    exact_dups = find_exact_duplicates(records)
    near_dups = find_near_duplicates(records)
    report["exact_duplicates"] = len(exact_dups)
    report["near_duplicates"] = len(near_dups)

    # Sample records (first 3)
    for r in records[:3]:
        report["samples"].append({
            "id": r.id,
            "claim": r.claim[:100],
            "label": r.label,
            "mapped_label": r.mapped_label,
            "language": r.language,
            "dataset": r.dataset,
        })

    return report


def print_report(report: dict) -> None:
    """Pretty-print a validation report."""
    print("\n" + "=" * 60)
    print("DATASET VALIDATION REPORT")
    print("=" * 60)
    print(f"Total records:    {report['total_records']}")
    print(f"Valid records:    {report['valid_records']}")
    print(f"Invalid records:  {report['invalid_records']}")
    print(f"Exact duplicates: {report['exact_duplicates']}")
    print(f"Near duplicates:  {report['near_duplicates']}")

    print("\n--- Class Distribution (Original Labels) ---")
    for label, count in report["class_distribution_original"].items():
        print(f"  {label}: {count}")

    print("\n--- Class Distribution (Mapped Labels) ---")
    for label, count in report["class_distribution_mapped"].items():
        print(f"  {label}: {count}")

    print("\n--- Language Distribution ---")
    for lang, count in report["language_distribution"].items():
        print(f"  {lang}: {count}")

    print("\n--- Dataset Distribution ---")
    for ds, count in report["dataset_distribution"].items():
        print(f"  {ds}: {count}")

    print("\n--- Missing Values ---")
    for field, count in report["missing_values"].items():
        print(f"  {field}: {count}")

    print("\n--- Samples ---")
    for s in report["samples"]:
        print(f"  [{s['dataset']}] {s['id']}: {s['claim']}...")
    print("=" * 60)


def validate_file(path: Path) -> dict:
    """Validate a single JSONL file and return report."""
    records = load_normalized(path)
    report = validate_records(records)
    print_report(report)
    return report


def validate_all() -> dict:
    """Validate the merged normalized_all.jsonl file."""
    all_path = PROCESSED_DIR / "normalized_all.jsonl"
    if not all_path.exists():
        logger.error("File not found: %s. Run normalize.py first.", all_path)
        return {}
    return validate_file(all_path)


if __name__ == "__main__":
    validate_all()
