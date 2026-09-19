"""
VeriTrace AI Empirical Performance & Concurrency Benchmarking Script.

Measures genuine latencies and throughput across:
1. Individual Pipeline Sub-stages:
   - Text Normalization
   - Language Detection
   - Claim Extraction
   - Evidence Retrieval (Uncached vs Cached)
   - Multilingual NLI & Ranking
   - Uncertainty Calibration & Decision Fusion
2. End-to-End API (/api/v1/analyze):
   - Mean, Median (p50), p95, p99, Min, Max latencies
3. Concurrent Workload:
   - Concurrency level = 5 workers
   - 25 concurrent requests
   - Measured throughput (req/s), error rate (%), peak latency

Zero fabricated metrics — outputs empirically measured data to benchmark_results.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
import numpy as np

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.services.calibration import calibrate_probabilities
from app.services.claim_extraction import extract_claims
from app.services.decision_engine import DecisionInput, fuse_decision
from app.services.evidence.base import NormalizedEvidence
from app.services.evidence.nli import MultilingualDeterministicNLI
from app.services.evidence.ranking import group_and_rank_evidence
from app.services.evidence.retrieval import retrieve_evidence
from app.services.language_detection import detect_language
from app.services.text_normalization import normalize_text

logging.basicConfig(level=logging.WARNING)  # keep benchmark output clean

TEST_CLAIMS = [
    "Reserve Bank of India kept repo rate unchanged at 6.5 percent.",
    "India digital payments processed over 13 billion transactions monthly.",
    "WHO declared green tea as a cure for COVID-19 virus.",
    "भारत सरकार ने 500 रुपये के नोटों को बंद करने का आदेश नहीं दिया है।",
    "भारतीय रिज़र्व बैंक ने यूपीआई भुगतानों पर कोई नया शुल्क नहीं लगाया।",
    "తెలుగు రాష్ట్రాల్లో కొత్త పరిశ్రమల స్థాపనకు రాయితీలు ప్రకటించారు.",
    "రైల్వే టికెట్ రద్దు ఛార్జీలలో ఎటువంటి మార్పులు లేవు.",
    "The government has announced a massive 50 percent cut in corporate taxes.",
    "New education policy integrates regional languages into higher education.",
    "వాతావరణ మార్పుల వల్ల ఈ ఏడాది ఉష్ణోగ్రతలు రికార్డు స్థాయికి చేరాయి.",
]


async def benchmark_components() -> Dict[str, Any]:
    print("\n[1/3] Benchmarking individual pipeline components...")
    nli_verifier = MultilingualDeterministicNLI()
    dummy_evidence = [
        NormalizedEvidence(
            source_name="RBI Press Release",
            title="Monetary Policy Committee Decision",
            url="https://rbi.org.in/press",
            snippet="The Monetary Policy Committee decided to keep the repo rate unchanged at 6.5 percent.",
            published_at="2024-02-08T10:00:00Z",
            retrieved_at="2024-02-08T12:00:00Z",
            source_type="local_fixture",
        )
    ]

    norm_times, lang_times, extract_times = [], [], []
    retrieval_uncached_times, retrieval_cached_times = [], []
    nli_times, decision_times = [], []

    for text in TEST_CLAIMS * 3:  # 30 iterations
        # 1. Normalization
        t0 = time.perf_counter()
        normalized = normalize_text(text)
        norm_times.append((time.perf_counter() - t0) * 1000)

        # 2. Language Detection
        t0 = time.perf_counter()
        lang_res = detect_language(normalized)
        lang_times.append((time.perf_counter() - t0) * 1000)

        # 3. Claim Extraction
        t0 = time.perf_counter()
        claims = extract_claims(normalized, lang_res.language_code)
        extract_times.append((time.perf_counter() - t0) * 1000)

        # 4. Evidence Retrieval (Uncached vs Cached)
        query = normalized[:40]
        # skip_cache=True
        t0 = time.perf_counter()
        await retrieve_evidence(query, language=lang_res.language_code, skip_cache=True)
        retrieval_uncached_times.append((time.perf_counter() - t0) * 1000)

        # skip_cache=False (Cached)
        t0 = time.perf_counter()
        await retrieve_evidence(query, language=lang_res.language_code, skip_cache=False)
        retrieval_cached_times.append((time.perf_counter() - t0) * 1000)

        # 5. NLI Verification
        t0 = time.perf_counter()
        nli_verifier.predict(premise=dummy_evidence[0].snippet, hypothesis=normalized, language=lang_res.language_code)
        nli_times.append((time.perf_counter() - t0) * 1000)

        # 6. Decision Engine & Calibration
        t0 = time.perf_counter()
        calibrated = calibrate_probabilities({"SUPPORTED": 0.8, "POTENTIALLY_MISLEADING": 0.1, "INSUFFICIENT_EVIDENCE": 0.05, "CONFLICTING_EVIDENCE": 0.05}, temperature=1.2)
        dec_input = DecisionInput(
            classifier_prediction="SUPPORTED",
            classifier_probabilities=calibrated,
            classifier_probability=0.8,
            top_evidence_relevance=0.85,
            nli_verdict="SUPPORTS",
            source_diversity=1,
            evidence_availability=1,
            has_conflict=False,
            is_non_checkable=False,
        )
        fuse_decision(dec_input)
        decision_times.append((time.perf_counter() - t0) * 1000)

    def stats(arr: List[float]) -> Dict[str, float]:
        return {
            "mean_ms": round(float(np.mean(arr)), 3),
            "median_ms": round(float(np.median(arr)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
            "min_ms": round(float(np.min(arr)), 3),
            "max_ms": round(float(np.max(arr)), 3),
        }

    return {
        "text_normalization": stats(norm_times),
        "language_detection": stats(lang_times),
        "claim_extraction": stats(extract_times),
        "retrieval_uncached": stats(retrieval_uncached_times),
        "retrieval_cached": stats(retrieval_cached_times),
        "nli_verification": stats(nli_times),
        "decision_fusion": stats(decision_times),
    }


async def benchmark_api_latency() -> Dict[str, Any]:
    print("[2/3] Benchmarking End-to-End API (/api/v1/analyze)...")
    latencies = []
    status_codes = []

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Warmup
        await client.post("/api/v1/analyze", json={"text": "Warmup request."})

        for claim in TEST_CLAIMS * 3:  # 30 requests
            t0 = time.perf_counter()
            resp = await client.post("/api/v1/analyze", json={"text": claim})
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            status_codes.append(resp.status_code)

    success_rate = sum(1 for c in status_codes if c == 200) / len(status_codes) * 100

    return {
        "total_requests": len(latencies),
        "success_rate_percent": success_rate,
        "mean_ms": round(float(np.mean(latencies)), 2),
        "median_ms": round(float(np.median(latencies)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(latencies, 99)), 2),
        "min_ms": round(float(np.min(latencies)), 2),
        "max_ms": round(float(np.max(latencies)), 2),
    }


async def benchmark_concurrency() -> Dict[str, Any]:
    print("[3/3] Benchmarking Concurrency (5 concurrent workers, 25 requests)...")
    num_requests = 25
    concurrency_limit = 5
    claims = (TEST_CLAIMS * 3)[:num_requests]

    semaphore = asyncio.Semaphore(concurrency_limit)
    latencies = []
    status_codes = []

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        async def send_worker(claim_text: str):
            async with semaphore:
                t0 = time.perf_counter()
                resp = await client.post("/api/v1/analyze", json={"text": claim_text})
                elapsed = (time.perf_counter() - t0) * 1000
                latencies.append(elapsed)
                status_codes.append(resp.status_code)

        wall_start = time.perf_counter()
        tasks = [send_worker(claim) for claim in claims]
        await asyncio.gather(*tasks)
        wall_duration = time.perf_counter() - wall_start

    throughput = round(num_requests / wall_duration, 2)
    successful = sum(1 for c in status_codes if c == 200)
    failed = num_requests - successful
    error_rate = round((failed / num_requests) * 100, 2)

    return {
        "concurrency_level": concurrency_limit,
        "total_requests": num_requests,
        "total_duration_seconds": round(wall_duration, 3),
        "throughput_req_per_sec": throughput,
        "successful_requests": successful,
        "failed_requests": failed,
        "error_rate_percent": error_rate,
        "mean_latency_ms": round(float(np.mean(latencies)), 2),
        "median_latency_ms": round(float(np.median(latencies)), 2),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        "max_latency_ms": round(float(np.max(latencies)), 2),
    }


async def main():
    print("=" * 70)
    print("VERITRACE AI EMPIRICAL BENCHMARK SUITE")
    print("=" * 70)

    comp_results = await benchmark_components()
    api_results = await benchmark_api_latency()
    concurrency_results = await benchmark_concurrency()

    full_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": comp_results,
        "api_endpoint": api_results,
        "concurrency": concurrency_results,
    }

    out_file = SCRIPT_DIR / "benchmark_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print("\n" + "=" * 70)
    print("MEASURED PERFORMANCE SUMMARY")
    print("=" * 70)
    print("\n### Component Latency Breakdown (N = 30 samples)")
    print("| Subsystem / Pipeline Stage | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | Min (ms) | Max (ms) |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for name, s in comp_results.items():
        clean_name = name.replace("_", " ").title()
        print(f"| {clean_name:26s} | {s['mean_ms']:9.3f} | {s['median_ms']:11.3f} | {s['p95_ms']:8.3f} | {s['p99_ms']:8.3f} | {s['min_ms']:8.3f} | {s['max_ms']:8.3f} |")

    print("\n### End-to-End API Latency (/api/v1/analyze, Sequential, N = 30)")
    print(f"- Success Rate : {api_results['success_rate_percent']:.1f}%")
    print(f"- Mean Latency : {api_results['mean_ms']:.2f} ms")
    print(f"- Median (p50) : {api_results['median_ms']:.2f} ms")
    print(f"- p95 Latency  : {api_results['p95_ms']:.2f} ms")
    print(f"- p99 Latency  : {api_results['p99_ms']:.2f} ms")
    print(f"- Min / Max    : {api_results['min_ms']:.2f} ms / {api_results['max_ms']:.2f} ms")

    print(f"\n### Concurrency Benchmark ({concurrency_results['concurrency_level']} Workers, {concurrency_results['total_requests']} Requests)")
    print(f"- Total Wall Time   : {concurrency_results['total_duration_seconds']:.3f} s")
    print(f"- Throughput        : {concurrency_results['throughput_req_per_sec']:.2f} req/s")
    print(f"- Success / Fail    : {concurrency_results['successful_requests']} / {concurrency_results['failed_requests']}")
    print(f"- Error Rate        : {concurrency_results['error_rate_percent']:.2f}%")
    print(f"- Concurrent p95    : {concurrency_results['p95_latency_ms']:.2f} ms")
    print("=" * 70)
    print(f"Results saved to: {out_file}\n")


if __name__ == "__main__":
    asyncio.run(main())
