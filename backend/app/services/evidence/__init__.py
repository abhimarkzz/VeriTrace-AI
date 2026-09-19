"""
VeriTrace Evidence Retrieval Subsystem.

Provides dynamic fact-check and evidence retrieval from Google Fact Check Tools API
and local offline fixtures with TTL caching and prompt-injection defense.
"""

from app.services.evidence.base import (
    EvidenceProvider,
    EvidenceRetrievalResult,
    NormalizedEvidence,
    sanitize_evidence_text,
    sanitize_evidence_url,
)
from app.services.evidence.google_factcheck import GoogleFactCheckProvider
from app.services.evidence.local_provider import LocalEvidenceProvider
from app.services.evidence.retrieval import (
    EvidenceCache,
    evidence_cache,
    map_external_rating_to_relation,
    normalize_to_evidence_item,
    retrieve_evidence,
)

from app.services.evidence.ranking import (
    RankedEvidence,
    SourceMetadata,
    group_and_rank_evidence,
)
from app.services.evidence.nli import (
    LanguageCoverageValidator,
    MultilingualDeterministicNLI,
    NLIModel,
    NLIOutput,
    get_nli_model,
)
from app.services.evidence.verifier import (
    ClaimEvidenceRelation,
    VerificationSynthesisResult,
    VerifiedEvidenceItem,
    rank_and_verify_evidence,
    synthesize_evidence_verdict,
    verify_evidence,
)

__all__ = [
    "ClaimEvidenceRelation",
    "EvidenceCache",
    "EvidenceProvider",
    "EvidenceRetrievalResult",
    "GoogleFactCheckProvider",
    "LanguageCoverageValidator",
    "LocalEvidenceProvider",
    "MultilingualDeterministicNLI",
    "NLIModel",
    "NLIOutput",
    "NormalizedEvidence",
    "RankedEvidence",
    "SourceMetadata",
    "VerificationSynthesisResult",
    "VerifiedEvidenceItem",
    "evidence_cache",
    "get_nli_model",
    "group_and_rank_evidence",
    "map_external_rating_to_relation",
    "normalize_to_evidence_item",
    "rank_and_verify_evidence",
    "retrieve_evidence",
    "sanitize_evidence_text",
    "sanitize_evidence_url",
    "synthesize_evidence_verdict",
    "verify_evidence",
]

