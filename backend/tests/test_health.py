"""
Tests for GET /api/v1/health.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    """Health endpoint should return 200 with status 'ok'."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "service" in body


def test_health_includes_database_status(client: TestClient) -> None:
    """Health response should report database connectivity."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "connected"


def test_health_includes_request_id_header(client: TestClient) -> None:
    """Every response should include an X-Request-ID header."""
    response = client.get("/api/v1/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 12


def test_cors_preflight(client: TestClient) -> None:
    """OPTIONS request from allowed origin should get CORS headers."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_cors_blocked_origin(client: TestClient) -> None:
    """Request from a disallowed origin should not get CORS allow header."""
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin", "")
    assert "evil.example.com" not in allow_origin
