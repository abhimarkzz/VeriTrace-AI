"""
Structured logging configuration.

Sets up a JSON-friendly logger with request-ID propagation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variable that holds the current request ID.
# Middleware sets this per-request; services can read it for tracing.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject the current request ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("-")  # type: ignore[attr-defined]
        return True


class StructuredJsonFormatter(logging.Formatter):
    """
    Format log records as structured JSON for log aggregators (Cloud Logging, Datadog).
    Never logs sensitive user input in plaintext.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_ctx.get("-")),
        }

        # Include custom structured fields if passed in record.__dict__
        for attr in ("analysis_id", "stage", "language", "model_version",
                     "retrieval_latency_ms", "nli_latency_ms", "total_latency_ms",
                     "status_code", "error"):
            val = getattr(record, attr, None)
            if val is not None:
                payload[attr] = val

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(*, level: str = "INFO", log_format: str = "standard") -> None:
    """Configure the root logger once at application startup."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if log_format == "json":
        handler.setFormatter(StructuredJsonFormatter())
    else:
        fmt = (
            "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"
        )
        handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on reload.
    root.handlers.clear()
    root.addHandler(handler)


def generate_request_id() -> str:
    """Create a short, unique request identifier."""
    return uuid.uuid4().hex[:12]


def mask_sensitive_input(text: Optional[str]) -> str:
    """
    Sanitize sensitive user input for logging.
    Replaces full raw text with length and SHA-256 fingerprint.
    """
    if not text:
        return "[empty]"
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"[text_length={len(text)}, sha256={sha}]"

