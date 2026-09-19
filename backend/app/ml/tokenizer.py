"""
Tokenizer wrapper for VeriTrace models.

Wraps AutoTokenizer with VeriTrace-specific configuration:
max length, truncation, padding behavior.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VeriTraceTokenizer:
    """Wrapper around HuggingFace tokenizer with VeriTrace defaults."""

    def __init__(self, tokenizer: Any, max_length: int = 256):
        self._tokenizer = tokenizer
        self._max_length = max_length

    @classmethod
    def from_pretrained(
        cls,
        model_name_or_path: str = "FacebookAI/xlm-roberta-base",
        max_length: int = 256,
    ) -> VeriTraceTokenizer:
        """Instantiate from a HuggingFace model name or local directory."""
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_name_or_path)
        return cls(tok, max_length=max_length)

    @property
    def max_length(self) -> int:
        return self._max_length

    @property
    def vocab_size(self) -> int:
        return self._tokenizer.vocab_size if self._tokenizer else 0

    def tokenize(
        self,
        text: str,
        return_tensors: Optional[str] = None,
        truncation: bool = True,
        padding: bool | str = True,
    ) -> dict:
        """Tokenize text with VeriTrace defaults."""
        kwargs: dict[str, Any] = {
            "truncation": truncation,
            "max_length": self._max_length,
            "padding": padding,
        }
        if return_tensors:
            kwargs["return_tensors"] = return_tensors
        return self._tokenizer(text, **kwargs)

    def tokenize_batch(
        self,
        texts: list[str],
        return_tensors: Optional[str] = None,
        truncation: bool = True,
        padding: bool | str = True,
    ) -> dict:
        """Tokenize a batch of texts."""
        kwargs: dict[str, Any] = {
            "truncation": truncation,
            "max_length": self._max_length,
            "padding": padding,
        }
        if return_tensors:
            kwargs["return_tensors"] = return_tensors
        return self._tokenizer(texts, **kwargs)

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._tokenizer.encode(
            text,
            add_special_tokens=True,
            truncation=True,
            max_length=self._max_length,
        )

    def decode(self, token_ids) -> str:
        """Decode token IDs back to text."""
        return self._tokenizer.decode(token_ids, skip_special_tokens=True)

    def get_token_count(self, text: str) -> int:
        """Count tokens without truncation."""
        tokens = self._tokenizer.encode(text, add_special_tokens=True, truncation=False)
        return len(tokens)

    def would_truncate(self, text: str) -> bool:
        """Check if text would exceed max_length."""
        return self.get_token_count(text) > self._max_length

