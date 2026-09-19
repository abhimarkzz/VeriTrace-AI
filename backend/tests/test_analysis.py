"""
Tests for POST /api/v1/analyze — including database persistence.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


# ── Valid requests ──────────────────────────────────────────────────────


def test_analyze_valid_claim(client: TestClient) -> None:
    """A well-formed request should return 200 with INSUFFICIENT_EVIDENCE."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "India has banned UPI payments.", "language": "en"},
    )
    assert response.status_code == 200
    body = response.json()

    assert "analysis_id" in body
    assert len(body["analysis_id"]) == 12
    assert body["language"] == "en"
    assert body["claim"] == "India has banned UPI payments."
    assert body["pipeline_status"] == "completed"

    # Honest values — no fakes
    assert body["assessment"] == "INSUFFICIENT_EVIDENCE"
    assert body["confidence"] is None
    assert body["confidence_breakdown"] is None
    assert isinstance(body["evidence"], list)
    assert len(body["evidence"]) >= 1
    assert body["evidence_strength"] in ("WEAK", "MODERATE", "STRONG")
    assert len(body["explanation"]) > 10


def test_analyze_claim_without_matching_evidence(client: TestClient) -> None:
    """A claim with no matching evidence should return an empty evidence list."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "Novel unique unrecorded statement 987654321.", "language": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["evidence"] == []
    assert body["evidence_strength"] is None


def test_analyze_persists_to_database(client: TestClient) -> None:
    """POST analyze should persist and be retrievable via GET."""
    # Create
    post_response = client.post(
        "/api/v1/analyze",
        json={"text": "A test claim for persistence.", "language": "en"},
    )
    assert post_response.status_code == 200
    analysis_id = post_response.json()["analysis_id"]

    # Retrieve
    get_response = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["analysis_id"] == analysis_id
    assert body["claim"] == "A test claim for persistence."
    assert body["language"] == "en"
    assert body["assessment"] == "INSUFFICIENT_EVIDENCE"


def test_analyze_auto_language(client: TestClient) -> None:
    """Language 'auto' should be accepted and a language code returned."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "Some claim text", "language": "auto"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] in ("en", "hi", "te")


def test_analyze_defaults_to_auto_language(client: TestClient) -> None:
    """Omitting language should default to auto-detection."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "Some claim text"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] in ("en", "hi", "te")


def test_analyze_hindi_language(client: TestClient) -> None:
    """Explicit Hindi language should be passed through."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "UPI से अरब लेनदेन", "language": "hi"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "hi"


def test_analyze_response_has_request_id(client: TestClient) -> None:
    """Every response must include the X-Request-ID header."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "A test claim."},
    )
    assert "X-Request-ID" in response.headers


# ── Retrieval endpoint ──────────────────────────────────────────────────


def test_get_analysis_not_found(client: TestClient) -> None:
    """Non-existent analysis ID should return 404."""
    response = client.get("/api/v1/analysis/nonexistent1")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"] == "not_found"


def test_get_analysis_returns_metadata(client: TestClient) -> None:
    """Retrieved analysis should include pipeline_status and explanation."""
    post_resp = client.post(
        "/api/v1/analyze",
        json={"text": "Metadata test claim."},
    )
    aid = post_resp.json()["analysis_id"]

    get_resp = client.get(f"/api/v1/analysis/{aid}")
    body = get_resp.json()
    assert body["pipeline_status"] == "completed"
    assert "explanation" in body
    assert len(body["explanation"]) > 0


# ── Invalid requests ────────────────────────────────────────────────────


def test_analyze_empty_body(client: TestClient) -> None:
    """Empty JSON body should fail validation (text is required)."""
    response = client.post("/api/v1/analyze", json={})
    assert response.status_code == 422


def test_analyze_blank_text(client: TestClient) -> None:
    """Whitespace-only text should be rejected."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "   "},
    )
    assert response.status_code == 422


def test_analyze_empty_string(client: TestClient) -> None:
    """Empty string text should be rejected."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": ""},
    )
    assert response.status_code == 422


def test_analyze_oversized_input(client: TestClient) -> None:
    """Input exceeding max length should be rejected with a 400."""
    oversized = "a" * 20_000
    response = client.post(
        "/api/v1/analyze",
        json={"text": oversized},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"] == "input_too_long"


def test_analyze_invalid_language(client: TestClient) -> None:
    """Unsupported language code should fail validation."""
    response = client.post(
        "/api/v1/analyze",
        json={"text": "A claim", "language": "fr"},
    )
    assert response.status_code == 422


def test_analyze_malformed_json(client: TestClient) -> None:
    """Non-JSON body should be rejected."""
    response = client.post(
        "/api/v1/analyze",
        content="this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


def test_analyze_wrong_content_type(client: TestClient) -> None:
    """Form-encoded body should be rejected."""
    response = client.post(
        "/api/v1/analyze",
        data={"text": "a claim"},
    )
    assert response.status_code == 422


def test_list_recent_analyses(client: TestClient) -> None:
    """GET /api/v1/analyses should return previously stored analyses summaries."""
    # First, submit an analysis
    resp1 = client.post(
        "/api/v1/analyze",
        json={"text": "Reserve Bank of India maintained policy repo rate at 6.5 percent.", "language": "en"},
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["analysis_id"]

    # Now call GET /api/v1/analyses
    list_resp = client.get("/api/v1/analyses")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1

    matching = [item for item in items if item["analysis_id"] == id1]
    assert len(matching) == 1
    summary = matching[0]
    assert summary["language"] == "en"
    assert "Reserve Bank" in summary["claim"]
    assert "assessment" in summary
    assert "created_at" in summary
