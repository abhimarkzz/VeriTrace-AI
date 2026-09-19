"""
Reproducible dataset download script.

Downloads X-Fact, FEVER, and AVeriTeC to data/raw/{dataset}/ as JSONL.
Supports: HuggingFace datasets library and direct JSON download.
Falls back to local data/raw/ if already downloaded or network unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _save_jsonl(records: list[dict], path: Path) -> int:
    """Write records as JSONL. Returns count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def download_xfact(output_dir: Path | None = None) -> dict[str, int]:
    """Download X-Fact from HuggingFace: utahnlp/x-fact."""
    out = output_dir or RAW_DIR / "xfact"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}

    try:
        from datasets import load_dataset
        ds = load_dataset("utahnlp/x-fact", trust_remote_code=True)
    except Exception as e:
        logger.warning("X-Fact download failed: %s. Checking local cache.", e)
        for split_file in out.glob("*.jsonl"):
            name = split_file.stem
            with open(split_file) as f:
                counts[name] = sum(1 for _ in f)
        if counts:
            logger.info("Using cached X-Fact: %s", counts)
        return counts

    for split_name in ds:
        records = []
        for i, row in enumerate(ds[split_name]):
            records.append({
                "id": f"xfact_{split_name}_{i}",
                "claim": row.get("claim", ""),
                "label": row.get("label", ""),
                "language": row.get("language", ""),
                "evidence": [],
                "source": row.get("site", ""),
                "dataset": "xfact",
            })
        n = _save_jsonl(records, out / f"{split_name}.jsonl")
        counts[split_name] = n
        logger.info("X-Fact %s: %d records", split_name, n)
    return counts


def download_fever(output_dir: Path | None = None) -> dict[str, int]:
    """Download FEVER from HuggingFace: fever/fever (v1.0)."""
    out = output_dir or RAW_DIR / "fever"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}

    try:
        from datasets import load_dataset
        ds = load_dataset("fever", "v1.0", trust_remote_code=True)
    except Exception as e:
        logger.warning("FEVER download failed: %s. Checking local cache.", e)
        for split_file in out.glob("*.jsonl"):
            name = split_file.stem
            with open(split_file) as f:
                counts[name] = sum(1 for _ in f)
        if counts:
            logger.info("Using cached FEVER: %s", counts)
        return counts

    for split_name in ds:
        records = []
        for i, row in enumerate(ds[split_name]):
            # FEVER evidence is a list of annotation sets
            evidence = []
            if row.get("evidence_wiki_url"):
                evidence.append({
                    "title": row.get("evidence_wiki_url", ""),
                    "snippet": "",
                    "url": f"https://en.wikipedia.org/wiki/{row.get('evidence_wiki_url', '')}",
                })
            records.append({
                "id": f"fever_{row.get('id', i)}",
                "claim": row.get("claim", ""),
                "label": row.get("label", ""),
                "language": "en",
                "evidence": evidence,
                "source": "Wikipedia",
                "dataset": "fever",
            })
        n = _save_jsonl(records, out / f"{split_name}.jsonl")
        counts[split_name] = n
        logger.info("FEVER %s: %d records", split_name, n)
    return counts


def download_averitec(output_dir: Path | None = None) -> dict[str, int]:
    """Download AVeriTeC from HuggingFace model repo: chenxwh/AVeriTeC."""
    out = output_dir or RAW_DIR / "averitec"
    out.mkdir(parents=True, exist_ok=True)
    counts = {}

    # AVeriTeC is hosted as a model repo with JSON files, not a datasets repo
    try:
        from huggingface_hub import hf_hub_download
        for split_name in ["train", "dev", "test"]:
            local_path = hf_hub_download(
                repo_id="chenxwh/AVeriTeC",
                filename=f"data/{split_name}.json",
                repo_type="model",
            )
            with open(local_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            records = []
            for i, row in enumerate(raw_data):
                evidence = []
                for q in row.get("questions", []):
                    for a in q.get("answers", []):
                        evidence.append({
                            "title": q.get("question", ""),
                            "snippet": a.get("answer", ""),
                            "url": a.get("source_url", ""),
                        })
                records.append({
                    "id": f"averitec_{split_name}_{i}",
                    "claim": row.get("claim", ""),
                    "label": row.get("label", ""),
                    "language": "en",
                    "evidence": evidence,
                    "source": row.get("claim_url", ""),
                    "dataset": "averitec",
                })
            n = _save_jsonl(records, out / f"{split_name}.jsonl")
            counts[split_name] = n
            logger.info("AVeriTeC %s: %d records", split_name, n)
    except Exception as e:
        logger.warning("AVeriTeC download failed: %s. Checking local cache.", e)
        for split_file in out.glob("*.jsonl"):
            name = split_file.stem
            with open(split_file) as f:
                counts[name] = sum(1 for _ in f)
        if counts:
            logger.info("Using cached AVeriTeC: %s", counts)
    return counts


def download_all() -> dict[str, dict[str, int]]:
    """Download all datasets. Returns counts per dataset per split."""
    results = {}
    results["xfact"] = download_xfact()
    results["fever"] = download_fever()
    results["averitec"] = download_averitec()

    logger.info("=" * 50)
    logger.info("Download Summary:")
    for ds_name, splits in results.items():
        total = sum(splits.values())
        logger.info("  %s: %d total (%s)", ds_name, total, splits)
    return results


if __name__ == "__main__":
    download_all()
