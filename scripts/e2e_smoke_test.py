#!/usr/bin/env python3
"""
VeriTrace AI — End-to-End Deployment Smoke Test

Validates complete system integrity across:
1. API Liveness Probe (/health)
2. Database Readiness Probe (/readiness)
3. Model Inference Health (/model-health)
4. Frontend Delivery (http://localhost:5173/)
5. Multilingual Claim Analysis (English, Hindi, Telugu via POST /api/v1/analyze)
6. Analysis Retrieval by ID (GET /api/v1/analysis/{id})

Usage:
    python3 scripts/e2e_smoke_test.py [--backend http://localhost:8000] [--frontend http://localhost:5173]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def http_get(url: str, timeout: float = 10.0) -> tuple[int, dict | str]:
    """Execute HTTP GET request and return status code and body."""
    req = urllib.request.Request(url, headers={"User-Agent": "VeriTrace-SmokeTest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            content = response.read().decode("utf-8")
            try:
                data = json.loads(content)
            except Exception:
                data = content
            return status_code, data
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            data = json.loads(content)
        except Exception:
            data = content
        return e.code, data
    except Exception as e:
        return 0, str(e)


def http_post_json(url: str, payload: dict, timeout: float = 20.0) -> tuple[int, dict | str]:
    """Execute HTTP POST request with JSON payload."""
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "VeriTrace-SmokeTest/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            content = response.read().decode("utf-8")
            try:
                data = json.loads(content)
            except Exception:
                data = content
            return status_code, data
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            data = json.loads(content)
        except Exception:
            data = content
        return e.code, data
    except Exception as e:
        return 0, str(e)


def run_smoke_tests(backend_url: str, frontend_url: str) -> bool:
    print("=" * 70)
    print(" VeriTrace AI — End-to-End Deployment Smoke Test")
    print("=" * 70)
    print(f"Backend Target  : {backend_url}")
    print(f"Frontend Target : {frontend_url}")
    print("-" * 70)

    all_passed = True
    test_results = []

    def log_result(name: str, passed: bool, details: str = ""):
        nonlocal all_passed
        if not passed:
            all_passed = False
        status_str = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
        test_results.append((name, passed, details))
        print(f"[{status_str}] {name} {('- ' + details) if details else ''}")

    # 1. API Liveness Check
    code, data = http_get(f"{backend_url}/health")
    if code == 200 and isinstance(data, dict) and data.get("status") in ["ok", "degraded"]:
        db_status = data.get("database", "unknown")
        log_result("1. Backend Liveness (/health)", True, f"status={data.get('status')}, db={db_status}")
    else:
        log_result("1. Backend Liveness (/health)", False, f"code={code}, response={data}")

    # 2. Database Readiness Probe
    code, data = http_get(f"{backend_url}/readiness")
    if code == 200 and isinstance(data, dict) and data.get("ready") is True:
        log_result("2. Database Readiness (/readiness)", True, "Database connected & accepting traffic")
    else:
        log_result("2. Database Readiness (/readiness)", False, f"code={code}, response={data}")

    # 3. Model Inference Health Probe
    code, data = http_get(f"{backend_url}/model-health")
    if code == 200 and isinstance(data, dict) and "model_name" in data:
        log_result("3. Model Health (/model-health)", True, f"model={data.get('model_name')}, backend={data.get('model_backend')}")
    else:
        log_result("3. Model Health (/model-health)", False, f"code={code}, response={data}")

    # 4. Frontend Asset Delivery
    code, data = http_get(frontend_url)
    if code == 200 and isinstance(data, str) and ("<title>" in data or "<div id=\"root\">" in data):
        log_result("4. Frontend UI Delivery (HTTP 200)", True, "Nginx SPA index.html served correctly")
    else:
        log_result("4. Frontend UI Delivery (HTTP 200)", False, f"code={code}, preview={str(data)[:100]}")

    # 5. Multilingual End-to-End Claim Verification
    claims = [
        ("English", "Reserve Bank of India maintained policy repo rate at 6.5 percent.", "en"),
        ("Hindi", "भारतीय रिजर्व बैंक ने रेपो रेट 6.5% पर बरकरार रखा।", "hi"),
        ("Telugu", "రిజర్వ్ బ్యాంక్ ఆఫ్ ఇండియా రెపో రేటును 6.5 శాతంగా కొనసాగించింది.", "te"),
    ]

    last_analysis_id = None
    for lang_name, text, expected_lang in claims:
        payload = {"text": text, "language": "auto"}
        code, data = http_post_json(f"{backend_url}/api/v1/analyze", payload)
        if code == 200 and isinstance(data, dict) and "analysis_id" in data:
            analysis_id = data.get("analysis_id")
            detected_lang = data.get("language")
            verdict = data.get("assessment")
            conf = data.get("confidence")
            last_analysis_id = analysis_id
            log_result(
                f"5. Analyze ({lang_name})",
                detected_lang == expected_lang,
                f"id={analysis_id}, lang={detected_lang}, verdict={verdict}, conf={conf}",
            )
        else:
            log_result(f"5. Analyze ({lang_name})", False, f"code={code}, error={data}")

    # 6. Retrieve Analysis Record by ID
    if last_analysis_id:
        code, data = http_get(f"{backend_url}/api/v1/analysis/{last_analysis_id}")
        if code == 200 and isinstance(data, dict) and data.get("analysis_id") == last_analysis_id:
            log_result("6. Analysis Retrieval (/api/v1/analysis/{id})", True, f"Retrieved persistent record {last_analysis_id}")
        else:
            log_result("6. Analysis Retrieval (/api/v1/analysis/{id})", False, f"code={code}, response={data}")
    else:
        log_result("6. Analysis Retrieval (/api/v1/analysis/{id})", False, "Skipped due to prior analyze failure")

    print("-" * 70)
    if all_passed:
        print("\033[92m[SUCCESS] All VeriTrace AI smoke tests passed successfully!\033[0m")
    else:
        print("\033[91m[FAILURE] One or more smoke tests failed. Inspect details above.\033[0m")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VeriTrace AI E2E Deployment Smoke Test")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--frontend", default="http://localhost:5173", help="Frontend base URL")
    args = parser.parse_args()

    success = run_smoke_tests(args.backend, args.frontend)
    sys.exit(0 if success else 1)
