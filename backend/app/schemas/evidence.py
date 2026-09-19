"""
Evidence schemas.

Mirrors the EvidenceItem interface from the frontend types.ts.
"""

from __future__ import annotations

from enum import Enum

from typing import Optional

from pydantic import BaseModel, Field


class Relation(str, Enum):
    """How a piece of evidence relates to the claim."""

    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    INSUFFICIENT = "INSUFFICIENT"


class EvidenceItem(BaseModel):
    """A single piece of retrieved evidence with its evaluation."""

    id: str = Field(..., description="Unique identifier for this evidence item")
    title: str = Field(..., description="Article or page title")
    source: str = Field(..., description="Publication or website name")
    url: str = Field(..., description="Direct URL to the source")
    snippet: str = Field(..., description="Relevant excerpt from the source")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="How relevant this source is to the claim"
    )
    source_quality: float = Field(
        ..., ge=0.0, le=1.0, description="Assessed quality/reliability of the source"
    )
    relation: Relation = Field(
        ..., description="Whether this evidence supports, contradicts, or is insufficient"
    )
    publisher: Optional[str] = Field(
        default=None, description="Publisher or media outlet name if available"
    )
    published_at: Optional[str] = Field(
        default=None, description="Publication timestamp or date string if available"
    )

    model_config = {"json_schema_extra": {"example": {
        "id": "example-001",
        "title": "Example Article Title",
        "source": "Example News",
        "url": "https://example.com/article",
        "snippet": "The relevant excerpt from the article...",
        "relevance_score": 0.85,
        "source_quality": 0.78,
        "relation": "SUPPORT",
    }}}
