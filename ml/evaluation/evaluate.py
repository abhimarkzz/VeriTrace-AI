"""
Evaluation script for VeriTrace models.

Computes: precision, recall, macro-F1, per-class F1, per-language F1.

Usage:
    python -m ml.evaluation.evaluate \
        --model_dir models/veritrace-xlmr-v1 \
        --test_file data/processed/test.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LABEL_NAMES = [
    "SUPPORTED",
    "POTENTIALLY_MISLEADING",
    "INSUFFICIENT_EVIDENCE",
    "CONFLICTING_EVIDENCE",
]
LABEL_TO_ID = {label: i for i, label in enumerate(LABEL_NAMES)}


def load_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    parser = argparse.ArgumentParser(description="Evaluate VeriTrace model")
    parser.add_argument("--model_dir", required=True, help="Path to saved model")
    parser.add_argument("--test_file", required=True, help="Path to test.jsonl")
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--output_file", default=None, help="Save results JSON")
    args = parser.parse_args()

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        from sklearn.metrics import (
            precision_recall_fscore_support,
            accuracy_score,
            classification_report,
            confusion_matrix,
        )
        import numpy as np
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        sys.exit(1)

    # ── Load model ───────────────────────────────────────────────────────
    model_dir = Path(args.model_dir)
    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        sys.exit(1)

    logger.info("Loading model from %s", model_dir)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    model.to(device)
    model.eval()

    # ── Load test data ───────────────────────────────────────────────────
    logger.info("Loading test data from %s", args.test_file)
    records = load_jsonl(args.test_file)

    texts = []
    labels = []
    languages = []
    for r in records:
        mapped = r.get("mapped_label", "")
        if mapped not in LABEL_TO_ID:
            continue
        claim = r.get("claim", "").strip()
        if not claim:
            continue
        texts.append(claim)
        labels.append(LABEL_TO_ID[mapped])
        languages.append(r.get("language", "unknown"))

    logger.info("Test samples: %d", len(texts))

    # ── Run inference ────────────────────────────────────────────────────
    all_preds = []
    start = time.monotonic()

    for i in range(0, len(texts), args.batch_size):
        batch_texts = texts[i:i + args.batch_size]
        inputs = tokenizer(
            batch_texts,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_length,
            padding=True,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            preds = torch.argmax(outputs.logits, dim=-1).cpu().tolist()
            all_preds.extend(preds)

    elapsed = time.monotonic() - start
    logger.info("Inference completed in %.1fs (%.1f samples/sec)", elapsed, len(texts) / elapsed)

    # ── Overall metrics ──────────────────────────────────────────────────
    labels_arr = np.array(labels)
    preds_arr = np.array(all_preds)

    accuracy = accuracy_score(labels_arr, preds_arr)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels_arr, preds_arr, average="macro", zero_division=0
    )

    logger.info("=== Overall Metrics ===")
    logger.info("  Accuracy:  %.4f", accuracy)
    logger.info("  Precision: %.4f", precision)
    logger.info("  Recall:    %.4f", recall)
    logger.info("  Macro F1:  %.4f", f1)

    # ── Per-class metrics ────────────────────────────────────────────────
    report = classification_report(
        labels_arr, preds_arr,
        target_names=LABEL_NAMES,
        output_dict=True,
        zero_division=0,
    )

    logger.info("\n=== Per-class Metrics ===")
    for name in LABEL_NAMES:
        if name in report:
            r = report[name]
            logger.info("  %s: P=%.4f R=%.4f F1=%.4f (n=%d)",
                        name, r["precision"], r["recall"], r["f1-score"], r["support"])

    # ── Per-language metrics ─────────────────────────────────────────────
    unique_langs = sorted(set(languages))
    per_language = {}
    logger.info("\n=== Per-language Metrics ===")
    for lang in unique_langs:
        mask = [i for i, l in enumerate(languages) if l == lang]
        if not mask:
            continue
        lang_labels = labels_arr[mask]
        lang_preds = preds_arr[mask]
        lp, lr, lf, _ = precision_recall_fscore_support(
            lang_labels, lang_preds, average="macro", zero_division=0
        )
        per_language[lang] = {
            "samples": len(mask),
            "precision": round(float(lp), 4),
            "recall": round(float(lr), 4),
            "macro_f1": round(float(lf), 4),
        }
        logger.info("  %s: P=%.4f R=%.4f F1=%.4f (n=%d)", lang, lp, lr, lf, len(mask))

    # ── Confusion matrix ─────────────────────────────────────────────────
    cm = confusion_matrix(labels_arr, preds_arr)
    logger.info("\n=== Confusion Matrix ===")
    logger.info("Labels: %s", LABEL_NAMES)
    for row in cm.tolist():
        logger.info("  %s", row)

    # ── Save results ─────────────────────────────────────────────────────
    results = {
        "model_dir": str(model_dir),
        "test_file": args.test_file,
        "total_samples": len(texts),
        "overall": {
            "accuracy": round(accuracy, 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "macro_f1": round(float(f1), 4),
        },
        "per_class": {
            name: {
                "precision": round(report[name]["precision"], 4),
                "recall": round(report[name]["recall"], 4),
                "f1": round(report[name]["f1-score"], 4),
                "support": report[name]["support"],
            }
            for name in LABEL_NAMES
            if name in report
        },
        "per_language": per_language,
        "confusion_matrix": cm.tolist(),
        "inference_time_seconds": round(elapsed, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    output_path = args.output_file or str(model_dir / "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Results saved to %s", output_path)


if __name__ == "__main__":
    main()
