"""
Normalize raw dataset JSONL files into the common NormalizedClaim schema.

Reads from data/raw/{dataset}/*.jsonl, applies explicit label mappings,
and writes to data/processed/normalized_{dataset}.jsonl.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ml.schemas import NormalizedClaim, map_label

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_jsonl(records: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def normalize_dataset(dataset_name: str) -> list[NormalizedClaim]:
    """
    Normalize all splits of a dataset into NormalizedClaim records.

    Returns the list of normalized records. Also writes to
    data/processed/normalized_{dataset_name}.jsonl.
    """
    raw_dir = RAW_DIR / dataset_name
    if not raw_dir.exists():
        logger.warning("Raw data directory not found: %s", raw_dir)
        return []

    all_records: list[NormalizedClaim] = []
    skipped = 0

    for jsonl_file in sorted(raw_dir.glob("*.jsonl")):
        raw_records = _read_jsonl(jsonl_file)
        for raw in raw_records:
            claim_text = raw.get("claim", "").strip()
            original_label = raw.get("label", "").strip()
            language = raw.get("language", "").strip()
            record_id = raw.get("id", "")

            # Skip records with missing essential fields
            if not claim_text or not original_label:
                skipped += 1
                continue

            # Default language for monolingual datasets
            if not language:
                if dataset_name == "fever":
                    language = "en"
                elif dataset_name == "averitec":
                    language = "en"

            # Map label — skip if unknown
            try:
                mapped = map_label(dataset_name, original_label)
            except ValueError as e:
                logger.debug("Skipping record %s: %s", record_id, e)
                skipped += 1
                continue

            normalized = NormalizedClaim(
                id=record_id,
                claim=claim_text,
                label=original_label,
                mapped_label=mapped.value,
                language=language,
                evidence=raw.get("evidence", []),
                source=raw.get("source", ""),
                dataset=dataset_name,
            )
            all_records.append(normalized)

    # Write normalized output
    if all_records:
        out_path = PROCESSED_DIR / f"normalized_{dataset_name}.jsonl"
        _write_jsonl([r.to_dict() for r in all_records], out_path)
        logger.info(
            "Normalized %s: %d records written, %d skipped → %s",
            dataset_name, len(all_records), skipped, out_path,
        )
    else:
        logger.warning("No records normalized for %s (skipped: %d)", dataset_name, skipped)

    return all_records


def normalize_all() -> dict[str, list[NormalizedClaim]]:
    """Normalize all known datasets."""
    results = {}
    for ds in ["xfact", "fever", "averitec"]:
        results[ds] = normalize_dataset(ds)

    # Merge all into a single file
    all_records = []
    for records in results.values():
        all_records.extend(records)

    if all_records:
        out_path = PROCESSED_DIR / "normalized_all.jsonl"
        _write_jsonl([r.to_dict() for r in all_records], out_path)
        logger.info("Total normalized: %d records → %s", len(all_records), out_path)

    return results


if __name__ == "__main__":
    normalize_all()
