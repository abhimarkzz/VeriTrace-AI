"""
Analysis request and response schemas.

Mirrors and extends the VerificationResult interface from the frontend types.ts.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .evidence import EvidenceItem


# ── Enums ────────────────────────────────────────────────────────────────


class Language(str, Enum):
    """Supported analysis languages."""

    AUTO = "auto"
    EN = "en"
    HI = "hi"
    TE = "te"


class Assessment(str, Enum):
    """Possible verdict outcomes."""

    SUPPORTED = "SUPPORTED"
    POTENTIALLY_MISLEADING = "POTENTIALLY_MISLEADING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class EvidenceStrength(str, Enum):
    """Qualitative strength of the assembled evidence."""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


class PipelineStatus(str, Enum):
    """Overall status of the analysis pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request ──────────────────────────────────────────────────────────────


class AnalysisRequest(BaseModel):
    """Incoming analysis request from the frontend."""

    text: str = Field(
        ...,
        min_length=1,
        description="The text to analyze — a claim, article, social-media post, or message",
    )
    language: Language = Field(
        default=Language.AUTO,
        description="Language of the input text, or 'auto' for detection",
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Input text must not be blank")
        return stripped

    model_config = {"json_schema_extra": {"example": {
        "text": "India has banned UPI payments and the service has been shut down.",
        "language": "auto",
    }}}


# ── Confidence Breakdown ─────────────────────────────────────────────────


class ConfidenceBreakdown(BaseModel):
    """Granular confidence sub-scores (populated when real models run)."""

    evidence_agreement: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_quality: Optional[float] = Field(None, ge=0.0, le=1.0)
    model_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    probabilities: Optional[dict[str, float]] = Field(None, description="Per-class probability distribution")



# ── Response ─────────────────────────────────────────────────────────────


class AnalysisResponse(BaseModel):
    """Full analysis result returned to the frontend."""

    analysis_id: str = Field(
        ..., description="Unique identifier for this analysis run"
    )
    language: str = Field(
        ..., description="Detected or specified language code"
    )
    claim: str = Field(
        ..., description="The factual claim extracted from the input"
    )
    claim_type: Optional[str] = Field(
        None, description="Classification of the claim (e.g. 'Statistical claim')"
    )
    assessment: Assessment = Field(
        ..., description="Verdict of the analysis"
    )
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall confidence score (null until real models run)"
    )
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(
        None, description="Granular confidence sub-scores"
    )
    confidence_tier: Optional[str] = Field(
        None, description="Qualitative confidence label (HIGH CONFIDENCE, MODERATE CONFIDENCE, LOW CONFIDENCE)"
    )
    confidence_explanation: Optional[str] = Field(
        None, description="Transparent explanation of uncertainty and signal fusion"
    )
    evidence_strength: Optional[EvidenceStrength] = Field(
        None, description="Qualitative strength of assembled evidence"
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Evidence items traced for this claim"
    )
    explanation: str = Field(
        ..., description="Human-readable explanation of the assessment"
    )
    pipeline_status: PipelineStatus = Field(
        ..., description="Status of the analysis pipeline"
    )

    model_config = {"json_schema_extra": {"example": {
        "analysis_id": "a1b2c3d4e5f6",
        "language": "en",
        "claim": "India has banned UPI payments.",
        "claim_type": None,
        "assessment": "INSUFFICIENT_EVIDENCE",
        "confidence": None,
        "confidence_breakdown": None,
        "evidence_strength": None,
        "evidence": [],
        "explanation": "No AI model or evidence retrieval service is configured yet. "
                       "This is a placeholder response from the analysis pipeline.",
        "pipeline_status": "completed",
    }}}


# ── Summary ──────────────────────────────────────────────────────────────


class AnalysisSummary(BaseModel):
    """Compact summary of an analysis for listing in history."""

    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    language: str = Field(..., description="Language code")
    claim: str = Field(..., description="The primary claim text")
    claim_type: Optional[str] = Field(None, description="Classification of the claim")
    assessment: Assessment = Field(..., description="Verdict outcome")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence score")
    confidence_tier: Optional[str] = Field(None, description="Confidence tier label")
    evidence_strength: Optional[EvidenceStrength] = Field(None, description="Evidence strength")
    evidence_count: int = Field(0, description="Total evidence items traced")
    created_at: Optional[str] = Field(None, description="ISO timestamp of when the analysis was performed")


# ── Error ────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Structured error returned on validation or processing failure."""

    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    request_id: Optional[str] = Field(None, description="Request trace ID")
