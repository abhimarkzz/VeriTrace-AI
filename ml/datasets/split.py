"""
Stratified train/val/test split with leakage prevention.

Splits normalized data into train/val/test sets:
- Stratified by mapped_label and language
- Deduplicates before splitting
- Verifies zero claim overlap between splits
- Creates per-language evaluation subsets for en/hi/te
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from collections import Counter
from pathlib import Path

from ml.schemas import NormalizedClaim

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 42
TARGET_LANGUAGES = ["en", "hi", "te"]


def _load_all_normalized() -> list[NormalizedClaim]:
    """Load the merged normalized file."""
    path = PROCESSED_DIR / "normalized_all.jsonl"
    if not path.exists():
        logger.error("normalized_all.jsonl not found. Run normalize.py first.")
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(NormalizedClaim.from_dict(json.loads(line)))
    return records


def _write_jsonl(records: list[NormalizedClaim], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_json() + "\n")
    return len(records)


def deduplicate(records: list[NormalizedClaim]) -> list[NormalizedClaim]:
    """Remove exact duplicates by claim text hash."""
    seen: set[str] = set()
    unique: list[NormalizedClaim] = []
    dupes = 0
    for r in records:
        key = hashlib.md5(r.claim.strip().encode("utf-8")).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(r)
        else:
            dupes += 1
    logger.info("Deduplication: %d total → %d unique (%d duplicates removed)",
                len(records), len(unique), dupes)
    return unique


def stratified_split(
    records: list[NormalizedClaim],
    ratios: dict[str, float] | None = None,
    seed: int = SEED,
) -> dict[str, list[NormalizedClaim]]:
    """
    Split records into train/val/test with stratification.

    Stratifies by (mapped_label, language) to maintain
    class and language distribution across all splits.
    """
    ratios = ratios or SPLIT_RATIOS
    rng = random.Random(seed)

    # Group by stratification key
    groups: dict[str, list[NormalizedClaim]] = {}
    for r in records:
        key = f"{r.mapped_label}_{r.language}"
        groups.setdefault(key, []).append(r)

    splits: dict[str, list[NormalizedClaim]] = {"train": [], "val": [], "test": []}

    for key, group in groups.items():
        rng.shuffle(group)
        n = len(group)
        n_train = int(n * ratios["train"])
        n_val = int(n * ratios["val"])

        splits["train"].extend(group[:n_train])
        splits["val"].extend(group[n_train:n_train + n_val])
        splits["test"].extend(group[n_train + n_val:])

    for name, recs in splits.items():
        rng.shuffle(recs)

    return splits


def check_leakage(splits: dict[str, list[NormalizedClaim]]) -> list[str]:
    """Verify zero claim overlap between splits. Returns error messages."""
    errors = []
    split_claims: dict[str, set[str]] = {}
    for name, records in splits.items():
        split_claims[name] = {r.claim.strip() for r in records}

    names = list(split_claims.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            overlap = split_claims[names[i]] & split_claims[names[j]]
            if overlap:
                errors.append(
                    f"LEAKAGE: {len(overlap)} claims overlap between "
                    f"{names[i]} and {names[j]}"
                )
    return errors


def create_language_subsets(
    splits: dict[str, list[NormalizedClaim]],
) -> dict[str, list[NormalizedClaim]]:
    """Create per-language evaluation subsets from the test split."""
    subsets = {}
    test_records = splits.get("test", [])
    for lang in TARGET_LANGUAGES:
        lang_records = [r for r in test_records if r.language == lang]
        if lang_records:
            subsets[lang] = lang_records
            logger.info("Language eval subset [%s]: %d records", lang, len(lang_records))
        else:
            logger.info("Language eval subset [%s]: 0 records (no data available)", lang)
    return subsets


def run_split() -> dict[str, int]:
    """Full split pipeline: load → deduplicate → split → check → save."""
    records = _load_all_normalized()
    if not records:
        return {}

    # Deduplicate
    records = deduplicate(records)

    # Split
    splits = stratified_split(records)

    # Leakage check
    leakage_errors = check_leakage(splits)
    if leakage_errors:
        for err in leakage_errors:
            logger.error(err)
    else:
        logger.info("Leakage check: PASSED (zero overlap between splits)")

    # Save splits
    counts = {}
    for name, recs in splits.items():
        n = _write_jsonl(recs, PROCESSED_DIR / f"{name}.jsonl")
        counts[name] = n
        logger.info("Split %s: %d records", name, n)

    # Language subsets
    lang_subsets = create_language_subsets(splits)
    for lang, recs in lang_subsets.items():
        n = _write_jsonl(recs, PROCESSED_DIR / f"eval_{lang}.jsonl")
        counts[f"eval_{lang}"] = n

    # Summary
    logger.info("Split Summary: %s", counts)

    # Distribution check
    for name, recs in splits.items():
        label_dist = Counter(r.mapped_label for r in recs)
        logger.info("  %s label distribution: %s", name, dict(label_dist))

    return counts


if __name__ == "__main__":
    run_split()
