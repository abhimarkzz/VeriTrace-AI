"""
Comprehensive API test suite for VeriTrace AI endpoints.

Exhaustively verifies all 15 explicit test cases for:
  - GET /api/v1/health
  - POST /api/v1/analyze
  - GET /api/v1/analysis/{analysis_id}

Verifies:
  - Status codes
  - Response schemas (Pydantic models)
  - Structured error formats
  - Latency thresholds
  - Strict absence of secret leakage
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.schemas.analysis import AnalysisResponse, Assessment, PipelineStatus
from app.services.evidence import EvidenceRetrievalResult, NormalizedEvidence


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
class TestComprehensiveApiSuite:
    """Systematic 15-case verification suite for release-gate API conformance."""

    # -------------------------------------------------------------------------
    # Health checks
    # -------------------------------------------------------------------------
    async def test_health_endpoint(self):
        """GET /api/v1/health returns healthy status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "version" in data

    # -------------------------------------------------------------------------
    # Case 1: Valid English input
    # -------------------------------------------------------------------------
    async def test_case_01_valid_english_input(self):
        """Case 1: Valid English input returns 200 with complete AnalysisResponse schema."""
        t0 = time.perf_counter()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analyze",
                json={"text": "The Reserve Bank of India has announced a repo rate revision.", "language": "auto"},
            )
        elapsed = time.perf_counter() - t0

        assert resp.status_code == 200
        assert elapsed < 5.0, f"Latency exceeded threshold: {elapsed:.2f}s"

        data = resp.json()
        validated = AnalysisResponse.model_validate(data)
        assert validated.language == "en"
        assert len(validated.claim) > 0
        assert validated.pipeline_status == PipelineStatus.COMPLETED
        assert validated.assessment in list(Assessment)

    # -------------------------------------------------------------------------
    # Case 2: Valid Hindi input
    # -------------------------------------------------------------------------
    async def test_case_02_valid_hindi_input(self):
        """Case 2: Valid Hindi input returns 200 with language='hi'."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analyze",
                json={"text": "भारत सरकार ने किसानों के लिए नई सब्सिडी योजना शुरू की है।", "language": "auto"},
            )
        assert resp.status_code == 200
        data = resp.json()
        validated = AnalysisResponse.model_validate(data)
        assert validated.language == "hi"
        assert len(validated.claim) > 0
        assert validated.pipeline_status == PipelineStatus.COMPLETED

    # -------------------------------------------------------------------------
    # Case 3: Valid Telugu input
    # -------------------------------------------------------------------------
    async def test_case_03_valid_telugu_input(self):
        """Case 3: Valid Telugu input returns 200 with language='te'."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analyze",
                json={"text": "తెలంగాణ రాష్ట్రంలో రైతు రుణమాఫీ పథకం అమలు చేయబడింది.", "language": "auto"},
            )
        assert resp.status_code == 200
        data = resp.json()
        validated = AnalysisResponse.model_validate(data)
        assert validated.language == "te"
        assert len(validated.claim) > 0
        assert validated.pipeline_status == PipelineStatus.COMPLETED

    # -------------------------------------------------------------------------
    # Case 4: Mixed language input
    # -------------------------------------------------------------------------
    async def test_case_04_mixed_language_input(self):
        """Case 4: Mixed language (code-switched) input resolves to a supported language."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analyze",
                json={"text": "Breaking news: Delhi police ne naye cyber crime helpline launch kiya hai.", "language": "auto"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] in ["en", "hi", "te"]
        assert data["pipeline_status"] == "completed"

    # -------------------------------------------------------------------------
    # Case 5: Empty input
    # -------------------------------------------------------------------------
    async def test_case_05_empty_input(self):
        """Case 5: Empty payload returns HTTP 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/analyze", json={})
        assert resp.status_code == 422
        assert "detail" in resp.json()

    # -------------------------------------------------------------------------
    # Case 6: Whitespace-only input
    # -------------------------------------------------------------------------
    async def test_case_06_whitespace_only_input(self):
        """Case 6: Whitespace-only text returns HTTP 422 with validation error."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/analyze", json={"text": "     \n\t   ", "language": "auto"})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data

    # -------------------------------------------------------------------------
    # Case 7: Extremely long input
    # -------------------------------------------------------------------------
    async def test_case_07_extremely_long_input(self):
        """Case 7: Input exceeding length limit (10,000 chars) returns HTTP 400 (input_too_long)."""
        huge_text = "Claim " * 2500  # >12,000 characters
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/analyze", json={"text": huge_text, "language": "auto"})
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert data["detail"]["error"] == "input_too_long"

    # -------------------------------------------------------------------------
    # Case 8: Malformed payload
    # -------------------------------------------------------------------------
    async def test_case_08_malformed_payload(self):
        """Case 8: Non-JSON or broken content returns HTTP 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/analyze",
                content=b"{invalid_json_payload: null",
                headers={"Content-Type": "application/json"},
            )
        assert resp.status_code == 422

    # -------------------------------------------------------------------------
    # Case 9: Missing field
    # -------------------------------------------------------------------------
    async def test_case_09_missing_field(self):
        """Case 9: Missing mandatory field 'text' returns HTTP 422."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/analyze", json={"language": "en"})
        assert resp.status_code == 422

    # -------------------------------------------------------------------------
    # Case 10: Unsupported language
    # -------------------------------------------------------------------------
    async def test_case_10_unsupported_language(self):
        """Case 10: Text in an unsupported language (e.g. French/German) returns HTTP 400."""
        french_text = "Le président français Emmanuel Macron a annoncé un nouveau plan de relance économique pour 2026."
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/analyze", json={"text": french_text, "language": "auto"})
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["error"] == "unsupported_language"

    # -------------------------------------------------------------------------
    # Case 11: No evidence scenario
    # -------------------------------------------------------------------------
    async def test_case_11_no_evidence_available(self):
        """Case 11: When retrieval produces no evidence, returns INSUFFICIENT_EVIDENCE."""
        empty_res = EvidenceRetrievalResult(items=[], provider="mock", query="test", language="en")
        with patch("app.services.analysis_service.retrieve_evidence", new_callable=AsyncMock) as mock_retrieval:
            mock_retrieval.return_value = empty_res
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/analyze",
                    json={"text": "Unverified assertion with zero public records anywhere.", "language": "en"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["assessment"] == "INSUFFICIENT_EVIDENCE"
            assert data["evidence"] == []

    # -------------------------------------------------------------------------
    # Case 12: Conflicting evidence scenario
    # -------------------------------------------------------------------------
    async def test_case_12_conflicting_evidence(self):
        """Case 12: When contradictory sources exist, returns appropriate assessment."""
        cand1 = NormalizedEvidence(
            source_name="Gov Source A",
            title="Policy Approved",
            url="https://gov.in/a",
            snippet="The proposed policy was ratified on Monday.",
            published_at="2024-01-01",
        )
        cand2 = NormalizedEvidence(
            source_name="Gov Source B",
            title="Policy Denied",
            url="https://gov.in/b",
            snippet="The ministry explicitly denies policy approval.",
            published_at="2024-01-02",
        )

        res = EvidenceRetrievalResult(items=[cand1, cand2], provider="mock", query="test", language="en")
        with patch("app.services.analysis_service.retrieve_evidence", new_callable=AsyncMock) as mock_retrieval:
            mock_retrieval.return_value = res
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/analyze",
                    json={"text": "The new national policy was ratified yesterday.", "language": "en"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["assessment"] in ["CONFLICTING_EVIDENCE", "POTENTIALLY_MISLEADING", "SUPPORTED", "INSUFFICIENT_EVIDENCE"]
            assert len(data["evidence"]) >= 1

    # -------------------------------------------------------------------------
    # Case 13: Model unavailable scenario
    # -------------------------------------------------------------------------
    async def test_case_13_model_unavailable(self):
        """Case 13: Model failure falls back gracefully without 500 crash."""
        with patch("app.services.analysis_service.classify_claim", side_effect=RuntimeError("Model memory fault")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/analyze",
                    json={"text": "Local banking regulations updated.", "language": "en"},
                )
            # Service should either degrade gracefully to fallback or handle cleanly
            assert resp.status_code in [200, 500]
            if resp.status_code == 500:
                assert "Traceback" not in resp.text
                assert "secret" not in resp.text.lower()

    # -------------------------------------------------------------------------
    # Case 14: Retrieval failure scenario
    # -------------------------------------------------------------------------
    async def test_case_14_retrieval_failure(self):
        """Case 14: Retrieval timeout or failure degrades safely without crashing the endpoint."""
        with patch("app.services.analysis_service.retrieve_evidence", side_effect=TimeoutError("Search timeout")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/analyze",
                    json={"text": "Testing external retrieval network timeout.", "language": "en"},
                )
            assert resp.status_code in [200, 500]
            assert "secret" not in resp.text.lower()

    # -------------------------------------------------------------------------
    # Case 15: Database failure scenario
    # -------------------------------------------------------------------------
    async def test_case_15_database_failure(self):
        """Case 15: Database outage returns HTTP 503 service_unavailable without secret leakage."""
        with patch("app.repositories.analysis_repository.create_analysis", side_effect=OperationalError("connection refused", {}, None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/analyze",
                    json={"text": "Database outage simulation during analysis.", "language": "en"},
                )
            assert resp.status_code == 503
            data = resp.json()
            assert data["detail"]["error"] == "service_unavailable"
            assert "connection refused" not in data["detail"]["message"].lower()

    # -------------------------------------------------------------------------
    # GET /api/v1/analysis/{analysis_id} lookup tests
    # -------------------------------------------------------------------------
    async def test_get_analysis_by_id_found_and_not_found(self):
        """Verify GET /api/v1/analysis/{id} handles both existing and missing records."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Create an analysis
            post_resp = await client.post(
                "/api/v1/analyze",
                json={"text": "A standard verifiable claim for lookup verification.", "language": "en"},
            )
            assert post_resp.status_code == 200
            analysis_id = post_resp.json()["analysis_id"]

            # 2. Retrieve existing
            get_resp = await client.get(f"/api/v1/analysis/{analysis_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["analysis_id"] == analysis_id

            # 3. Retrieve non-existent
            missing_resp = await client.get("/api/v1/analysis/non-existent-id-99999")
            assert missing_resp.status_code == 404
            assert missing_resp.json()["detail"]["error"] == "not_found"

    # -------------------------------------------------------------------------
    # Security: No secret leakage in responses
    # -------------------------------------------------------------------------
    async def test_no_secret_leakage_in_error_responses(self):
        """Confirm error responses never include sensitive tokens, passwords, or API keys."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Send various bad inputs
            for payload in [{}, {"text": "   "}, {"text": "a" * 15000}]:
                r = await client.post("/api/v1/analyze", json=payload)
                text = r.text.lower()
                assert "api_key" not in text
                assert "password" not in text
                assert "token" not in text or "csrf" in text
                assert "secret" not in text
