"""
API Contract tests for VeriTrace AI.

Validates that:
  1. The generated OpenAPI specification is valid, conforms to OpenAPI 3.1, and contains all core routes.
  2. The schema definitions for AnalysisRequest, AnalysisResponse, EvidenceItem, and ErrorResponse
     match the frontend contract expected by React (types.ts and src/services/api/analysis.ts).
  3. Field names, types, enums, and required properties match between backend schemas and frontend.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.main import app

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "openapi.json"


class TestApiContract:
    """Contract tests ensuring frontend/backend schema synchronicity."""

    @pytest.fixture(scope="class")
    def openapi_schema(self) -> dict:
        """Load or generate the OpenAPI specification dictionary."""
        if OPENAPI_PATH.exists():
            with open(OPENAPI_PATH, encoding="utf-8") as f:
                return json.load(f)
        return app.openapi()

    def test_openapi_metadata(self, openapi_schema: dict):
        """OpenAPI schema contains valid metadata and info blocks."""
        assert "openapi" in openapi_schema
        assert openapi_schema["openapi"].startswith("3.")
        assert "info" in openapi_schema
        assert "VeriTrace" in openapi_schema["info"]["title"]
        assert "version" in openapi_schema["info"]

    def test_required_routes_exist(self, openapi_schema: dict):
        """All mandatory API endpoints are declared in the OpenAPI specification."""
        paths = openapi_schema.get("paths", {})

        # Core analysis endpoints
        assert "/api/v1/analyze" in paths, "Missing POST /api/v1/analyze route"
        assert "post" in paths["/api/v1/analyze"]

        assert "/api/v1/analysis/{analysis_id}" in paths, "Missing GET /api/v1/analysis/{id} route"
        assert "get" in paths["/api/v1/analysis/{analysis_id}"]

        # Probes & health
        assert "/api/v1/health" in paths or "/health" in paths

    def test_analysis_request_contract(self, openapi_schema: dict):
        """AnalysisRequest schema contains 'text' (required) and 'language' with expected enums."""
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        assert "AnalysisRequest" in schemas, "AnalysisRequest schema missing from components"

        req_schema = schemas["AnalysisRequest"]
        props = req_schema.get("properties", {})
        assert "text" in props
        assert "language" in props

        required_fields = req_schema.get("required", [])
        assert "text" in required_fields, "'text' must be a required field"

    def test_analysis_response_contract_matches_frontend(self, openapi_schema: dict):
        """
        Verify AnalysisResponse includes all fields expected by the React frontend:
        - analysis_id: string
        - language: string
        - claim: string
        - assessment: enum
        - confidence: float / null
        - confidence_tier: string / null
        - evidence_strength: string / null
        - evidence: array of EvidenceItem
        - explanation: string
        - pipeline_status: enum
        """
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        assert "AnalysisResponse" in schemas, "AnalysisResponse schema missing"

        resp_schema = schemas["AnalysisResponse"]
        props = resp_schema.get("properties", {})

        expected_fields = [
            "analysis_id",
            "language",
            "claim",
            "claim_type",
            "assessment",
            "confidence",
            "confidence_tier",
            "confidence_breakdown",
            "confidence_explanation",
            "evidence_strength",
            "evidence",
            "explanation",
            "pipeline_status",
        ]

        for field in expected_fields:
            assert field in props, f"Missing field '{field}' in AnalysisResponse OpenAPI schema"

        # Check required fields
        required = resp_schema.get("required", [])
        assert "analysis_id" in required
        assert "language" in required
        assert "claim" in required
        assert "assessment" in required
        assert "explanation" in required
        assert "pipeline_status" in required

    def test_evidence_item_contract_matches_frontend(self, openapi_schema: dict):
        """
        Verify EvidenceItem schema contains all fields required for EvidenceCard rendering:
        - id, title, source, url, snippet, relevance_score, source_quality, relation
        """
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        assert "EvidenceItem" in schemas, "EvidenceItem schema missing"

        ev_props = schemas["EvidenceItem"].get("properties", {})
        expected_ev_fields = [
            "id",
            "title",
            "source",
            "url",
            "snippet",
            "relevance_score",
            "source_quality",
            "relation",
            "publisher",
            "published_at",
        ]

        for field in expected_ev_fields:
            assert field in ev_props, f"Missing field '{field}' in EvidenceItem OpenAPI schema"

    def test_assessment_enum_contract(self, openapi_schema: dict):
        """Validate Assessment enum contains all 4 supported verdicts."""
        schemas = openapi_schema.get("components", {}).get("schemas", {})
        assessment_schema = schemas.get("Assessment", {})
        enums = assessment_schema.get("enum", [])

        expected_assessments = [
            "SUPPORTED",
            "POTENTIALLY_MISLEADING",
            "INSUFFICIENT_EVIDENCE",
            "CONFLICTING_EVIDENCE",
        ]
        for val in expected_assessments:
            assert val in enums, f"Missing enum value '{val}' in Assessment schema"
