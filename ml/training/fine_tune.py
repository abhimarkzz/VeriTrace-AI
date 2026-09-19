"""
Fine-tuning script for XLM-RoBERTa sequence classifier.

Uses the VeriTrace dataset pipeline (STEP 3) to train a real
fact-verification classifier. Does NOT claim benchmark performance
until the model has actually been evaluated.

Usage:
    python -m ml.training.fine_tune \
        --dataset_dir data/processed \
        --output_dir models/veritrace-xlmr-v1 \
        --epochs 3 \
        --batch_size 16 \
        --learning_rate 2e-5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# VeriTrace label mapping — must match classifier.py
LABEL_NAMES = [
    "SUPPORTED",
    "POTENTIALLY_MISLEADING",
    "INSUFFICIENT_EVIDENCE",
    "CONFLICTING_EVIDENCE",
]
LABEL_TO_ID = {label: i for i, label in enumerate(LABEL_NAMES)}


def load_jsonl(path: str) -> list[dict]:
    """Load a JSONL file."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def map_label(record: dict) -> int | None:
    """Map a normalized record's mapped_label to an integer ID."""
    mapped = record.get("mapped_label", "")
    if mapped in LABEL_TO_ID:
        return LABEL_TO_ID[mapped]
    return None


def prepare_dataset(records: list[dict]) -> tuple[list[str], list[int], list[str]]:
    """Extract texts, labels, and language codes from normalized records."""
    texts = []
    labels = []
    languages = []
    skipped = 0
    for r in records:
        label_id = map_label(r)
        if label_id is None:
            skipped += 1
            continue
        claim = r.get("claim", "").strip()
        if not claim:
            skipped += 1
            continue
        texts.append(claim)
        labels.append(label_id)
        languages.append(r.get("language", "unknown"))
    if skipped:
        logger.info("Skipped %d records (unmappable label or empty claim)", skipped)
    return texts, labels, languages



def main():
    parser = argparse.ArgumentParser(description="Fine-tune XLM-RoBERTa for VeriTrace")
    parser.add_argument("--model_name", default="FacebookAI/xlm-roberta-base",
                        help="Base model name from HuggingFace")
    parser.add_argument("--dataset_dir", required=True,
                        help="Path to processed dataset directory with train.jsonl/val.jsonl")
    parser.add_argument("--output_dir", required=True,
                        help="Directory to save fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--warmup_ratio", type=float, default=0.1)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--freeze_encoder", action="store_true",
                        help="Freeze encoder layers (faster, less memory)")
    parser.add_argument("--dataset_version", default=None,
                        help="Dataset version identifier (reads from split_metadata.json if not provided)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # ── Check dependencies ───────────────────────────────────────────────
    try:
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            TrainingArguments,
            Trainer,
        )
        from sklearn.metrics import (
            precision_recall_fscore_support,
            accuracy_score,
            classification_report,
        )
        import numpy as np
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        logger.error("Install: pip install torch transformers scikit-learn numpy")
        sys.exit(1)

    # ── Set seed ─────────────────────────────────────────────────────────
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # ── Load data ────────────────────────────────────────────────────────
    dataset_dir = Path(args.dataset_dir)
    train_path = dataset_dir / "train.jsonl"
    val_path = dataset_dir / "val.jsonl"

    if not train_path.exists():
        logger.error("Training file not found: %s", train_path)
        sys.exit(1)
    if not val_path.exists():
        logger.error("Validation file not found: %s", val_path)
        sys.exit(1)

    # Detect dataset version
    dataset_version = args.dataset_version or "1.0.0"
    split_meta_path = dataset_dir / "split_metadata.json"
    if split_meta_path.exists() and not args.dataset_version:
        try:
            with open(split_meta_path, encoding="utf-8") as f:
                meta = json.load(f)
                dataset_version = meta.get("dataset_version", meta.get("version", "1.0.0"))
        except Exception:
            pass

    logger.info("Loading training data from %s (dataset version: %s)", train_path, dataset_version)
    train_records = load_jsonl(str(train_path))
    val_records = load_jsonl(str(val_path))

    train_texts, train_labels, train_langs = prepare_dataset(train_records)
    val_texts, val_labels, val_langs = prepare_dataset(val_records)

    logger.info("Training: %d samples, Validation: %d samples", len(train_texts), len(val_texts))


    # ── Label distribution ───────────────────────────────────────────────
    for label_name, label_id in LABEL_TO_ID.items():
        train_count = train_labels.count(label_id)
        val_count = val_labels.count(label_id)
        logger.info("  %s: train=%d val=%d", label_name, train_count, val_count)

    # ── Tokenizer ────────────────────────────────────────────────────────
    logger.info("Loading tokenizer: %s", args.model_name)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    # ── Dataset class ────────────────────────────────────────────────────
    class ClaimDataset(torch.utils.data.Dataset):
        def __init__(self, texts, labels):
            self.encodings = tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=args.max_length,
                return_tensors="pt",
            )
            self.labels = torch.tensor(labels, dtype=torch.long)

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            item = {k: v[idx] for k, v in self.encodings.items()}
            item["labels"] = self.labels[idx]
            return item

    train_dataset = ClaimDataset(train_texts, train_labels)
    val_dataset = ClaimDataset(val_texts, val_labels)

    # ── Model ────────────────────────────────────────────────────────────
    logger.info("Loading model: %s (num_labels=%d)", args.model_name, len(LABEL_NAMES))
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_NAMES),
        ignore_mismatched_sizes=True,
    )

    # Configure label names in model config
    model.config.label2id = LABEL_TO_ID
    model.config.id2label = {v: k for k, v in LABEL_TO_ID.items()}

    # Optionally freeze encoder
    if args.freeze_encoder:
        logger.info("Freezing encoder layers (only classifier head will train)")
        for param in model.base_model.parameters():
            param.requires_grad = False

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    logger.info("Using device: %s", device)

    # ── Metrics ──────────────────────────────────────────────────────────
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        preds = np.argmax(predictions, axis=-1)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average="macro", zero_division=0
        )
        acc = accuracy_score(labels, preds)
        return {
            "accuracy": round(acc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "macro_f1": round(f1, 4),
        }

    # ── Training ─────────────────────────────────────────────────────────
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_dir=str(output_dir / "logs"),
        logging_steps=50,
        seed=args.seed,
        report_to="none",
        fp16=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    logger.info("Starting training...")
    start_time = time.monotonic()
    train_result = trainer.train()
    elapsed = time.monotonic() - start_time

    # ── Evaluate ─────────────────────────────────────────────────────────
    logger.info("Evaluating on validation set...")
    eval_results = trainer.evaluate()

    # Per-class metrics
    val_preds = trainer.predict(val_dataset)
    pred_labels = np.argmax(val_preds.predictions, axis=-1)
    report = classification_report(
        val_labels, pred_labels,
        target_names=LABEL_NAMES,
        output_dict=True,
        zero_division=0,
    )

    # Per-language metrics on validation set
    val_labels_arr = np.array(val_labels)
    unique_langs = sorted(set(val_langs))
    per_language = {}
    for lang in unique_langs:
        mask = [i for i, l in enumerate(val_langs) if l == lang]
        if not mask:
            continue
        lang_labels = val_labels_arr[mask]
        lang_preds = pred_labels[mask]
        lp, lr, lf, _ = precision_recall_fscore_support(
            lang_labels, lang_preds, average="macro", zero_division=0
        )
        per_language[lang] = {
            "samples": len(mask),
            "precision": round(float(lp), 4),
            "recall": round(float(lr), 4),
            "macro_f1": round(float(lf), 4),
        }

    # ── Save ─────────────────────────────────────────────────────────────
    logger.info("Saving model to %s", output_dir)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    # Save metadata
    metadata = {
        "model_name": args.model_name,
        "model_version": f"veritrace-xlmr-v1-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "num_labels": len(LABEL_NAMES),
        "label_names": LABEL_NAMES,
        "label_to_id": LABEL_TO_ID,
        "training_config": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "max_length": args.max_length,
            "warmup_ratio": args.warmup_ratio,
            "weight_decay": args.weight_decay,
            "freeze_encoder": args.freeze_encoder,
            "seed": args.seed,
        },
        "dataset": {
            "dir": str(dataset_dir),
            "version": dataset_version,
            "train_samples": len(train_texts),
            "val_samples": len(val_texts),
        },
        "metrics": {
            "eval": eval_results,
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
        },
        "training_time_seconds": round(elapsed, 1),
        "device": device,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = output_dir / "model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Training complete!")
    logger.info("  Time: %.1fs", elapsed)
    logger.info("  Accuracy: %.4f", eval_results.get("eval_accuracy", 0))
    logger.info("  Macro F1: %.4f", eval_results.get("eval_macro_f1", 0))
    logger.info("  Model saved: %s", output_dir)
    logger.info("  Metadata: %s", metadata_path)


if __name__ == "__main__":
    main()
