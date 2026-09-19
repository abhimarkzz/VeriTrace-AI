# VeriTrace AI — Release-Gate Verification & Test Plan

## 1. Executive Summary & Verification Objectives
VeriTrace AI is a safety-critical, uncertainty-aware multilingual verification platform designed to ingest news claims, forwarded messages, and statistical statements in English (`en`), Hindi (`hi`), and Telugu (`te`), verify them against authoritative sources, and produce calibrated, evidence-backed verdicts.

Because VeriTrace operates in the misinformation detection domain, verification cannot rely on surface heuristics or trivial happy-path tests. This test plan establishes a multi-dimensional release-gate verification strategy covering:
- **Frontend User Experience & Interactive Flow**: Landing page, composer validation, language selection, real-time stage progression, uncertainty rendering, evidence cards, error recovery, and responsive accessibility.
- **Backend API Contract & Resilience**: OpenAPI 3.1 schema adherence, input validation, strict HTTP error codes, database fault tolerance, and graceful degradation.
- **Model Evaluation & Uncertainty Calibration**: Macro F1, per-class F1, per-language F1, confusion matrices, Expected Calibration Error (ECE), Brier Score, and reliability diagrams.
- **Evidence Retrieval & Multilingual NLI Benchmarking**: Recall@K, Mean Reciprocal Rank (MRR), cross-lingual entailment, semantic contradiction, numerical/date alteration detection, and deduplication.
- **Security & Threat Model Hardening**: SSRF defense against cloud metadata/internal networks, prompt injection neutralization in untrusted evidence, rate limiting, SQL injection defense, and credential protection.
- **Empirical Performance & Concurrency**: Component latency profiling, sequential p50/p95/p99 API latencies, and 5-worker concurrent throughput.

---

## 2. Test Pyramid & Scope

```
                     ┌───────────────────────┐
                     │   E2E Multi-turn Flow  │ (Vitest + Integration)
                     ├───────────────────────┤
                     │ Security & Adversarial│ (SSRF, Injection, Typos)
                     ├───────────────────────┤
                     │ Retrieval & NLI Bench │ (Recall@K, MRR, Contradiction)
                     ├───────────────────────┤
                     │ API Contract & Schema │ (OpenAPI 3.1, PyTest Client)
                     ├───────────────────────┤
                     │ Unit & Component Tests│ (Normalization, Lang, Models)
                     └───────────────────────┘
```

| Layer | Framework / Tool | Test Files | Target Capabilities Verified |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | Vitest + React Testing Library | `src/__tests__/App.test.tsx`<br>`src/__tests__/e2eIntegration.test.tsx` | Landing page, multi-turn verification, confidence pills, evidence cards, error banners, reset flow |
| **Frontend Client** | Vitest | `src/__tests__/apiClient.test.ts`<br>`src/__tests__/verificationFlow.test.ts` | Fetch wrapper, timeout aborts, 4xx/5xx handling, stage callbacks, camelCase transformation |
| **API Contract** | PyTest + TestClient | `backend/tests/test_contract.py`<br>`backend/tests/test_api_comprehensive.py` | OpenAPI 3.1 specification, schema equivalence, parameter validation, HTTP status compliance |
| **Retrieval Bench** | PyTest + Mock Providers | `backend/tests/test_retrieval_benchmarks.py` | Recall@1/3/5, MRR, deduplication, pagination tokens, cache TTL, fallback handling |
| **Multilingual NLI** | PyTest + NLI Engines | `backend/tests/test_nli_multilingual_benchmark.py` | EN/HI/TE entailment, contradiction detection, numerical/date mismatch, adversarial false-support |
| **Security & Abuse** | PyTest + Attack Vectors | `backend/tests/test_security.py`<br>`backend/tests/test_adversarial_and_failure.py` | SSRF blocking, prompt injection defanging, SQLi/XSS, in-memory rate limiting, zero secret leaks |
| **Model Evaluation** | Python + Scikit-Learn | `ml/evaluation/run_evaluation.py` | Multi-class Macro F1, per-class F1, per-language F1, ECE, Brier score, temperature scaling |
| **Benchmarking** | Asyncio + HTTPX | `backend/scripts/benchmark_performance.py` | Component-level profiling, p50/p95/p99 latency, concurrent throughput |

---

## 3. Multilingual Quality & Coverage Matrix

VeriTrace explicitly evaluates linguistic competence across all three supported languages:

| Verification Stage | English (`en`) | Hindi (`hi`) | Telugu (`te`) | Code-Switched / Mixed |
| :--- | :--- | :--- | :--- | :--- |
| **Text Normalization** | URLs, mentions, camelCase hashtags, repeated chars | Devanagari Unicode NFC, zero-width joiners, currency (₹) | Telugu Unicode NFC, zero-width characters, punctuation | Hinglish / Tenglish transliteration preservation |
| **Language Detection** | Latin script, langdetect seed | Devanagari script range (`\u0900-\u097F`) | Telugu script range (`\u0C00-\u0C7F`) | Primary script dominant detection with candidate list |
| **Claim Extraction** | spaCy POS/Dependency parsing + statistical regex | Hindi keyword heuristics + Hindi statistical patterns | Telugu keyword heuristics + numerical patterns | Fallback to sentence extraction with length bounds |
| **Evidence Retrieval** | Google Fact Check `languageCode=en` + English fixtures | Google Fact Check `languageCode=hi` + Hindi fixtures | Google Fact Check `languageCode=te` + Telugu fixtures | English fallback search if regional query yields 0 results |
| **NLI Verification** | Semantic negation + numerical/date checking | Devanagari negation (`नहीं`, `झूठा`, `खारिज`) | Telugu negation (`లేదు`, `తప్పు`, `అబద్ధం`) | Cross-lingual numerical consistency checks |

---

## 4. Failure Mode & Resilience Test Matrix

| Failure Mode | Simulation Technique | Expected Behavior | Release Gate Threshold |
| :--- | :--- | :--- | :--- |
| **Database Connection Loss** | Mock `AsyncSession.execute` raising `OperationalError` | Return HTTP 503 with `service_unavailable`, zero stack trace leaked | Must not crash worker; clean 503 JSON |
| **ML Model Unavailable** | Register `UnavailableClassifier("Out of Memory")` | Fall back to evidence-led verification without model signal | Pipeline completes, confidence calibrated to evidence |
| **Fact Check API 500 / Down** | Mock `retrieve_evidence` raising `TimeoutError` | Fall back to offline local fixtures or `INSUFFICIENT_EVIDENCE` | Must return HTTP 200 with honest `INSUFFICIENT_EVIDENCE` |
| **Client Rate Limit Breach** | Send >3 requests within sliding window | Return HTTP 429 with `Retry-After` header | Limiter blocks 4th request, resets after window |
| **Oversized Input (>10,000 chars)**| Send 12,000 character block | Return HTTP 400 with `input_too_long` error | Fast-reject before normalization/model inference |
| **Unsupported Language** | Submit French text ("Le gouvernement a interdit...") | Return HTTP 400 with `unsupported_language` | Fast-reject without model execution |

---

## 5. Security & Threat Modeling Strategy

1. **Server-Side Request Forgery (SSRF)**:
   - Evaluates all URLs passed for evidence extraction or citation.
   - Strictly blocks: Loopback (`127.0.0.0/8`, `::1`), RFC 1918 Private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Cloud Metadata (`169.254.169.254`), and forbidden schemes (`file:`, `ftp:`, `javascript:`, `data:`).
2. **Untrusted Evidence Prompt Injection**:
   - Web snippets retrieved from external search engines are treated as untrusted adversarial text.
   - All text passes through `sanitize_evidence_text()`, which strips raw HTML/scripts, removes zero-width steganographic bytes, defangs markdown image exfiltration tokens (`![alt](...)`), and neutralizes system instruction overrides (`"Ignore previous instructions"`, `"System prompt override"`).
3. **Secret Masking & Zero-Leakage**:
   - Verification error handlers wrap all unhandled exceptions.
   - Inbound texts are logged only by text length and SHA-256 hash.
   - API keys and tokens are never included in HTTP response payloads or error details.

---

## 6. Model Evaluation & Calibration Strategy

- **Test Dataset**: Balanced 36-sample multilingual benchmark (`data/processed/test.jsonl`) spanning English, Hindi, and Telugu across all 4 canonical classes:
  - `SUPPORTED` (9 samples)
  - `POTENTIALLY_MISLEADING` (9 samples)
  - `INSUFFICIENT_EVIDENCE` (9 samples)
  - `CONFLICTING_EVIDENCE` (9 samples)
- **Metrics Evaluated**:
  - Accuracy, Macro Precision, Macro Recall, Macro F1, Weighted F1
  - Per-class F1 for all 4 states
  - Per-language F1 for English, Hindi, and Telugu
  - 4x4 Confusion Matrix
  - Multi-class Brier Score
  - Expected Calibration Error (ECE) across 10 equal-width bins with empirical gap analysis
  - Temperature Scaling ($T$) fitting using negative log-likelihood minimization

---

## 7. Release Gate Exit Criteria

For a build to be certified `PASS`:
1. **Frontend Tests**: 100% of Vitest suites must pass with 0 failures.
2. **Frontend Build**: `tsc -b && vite build` must compile cleanly with 0 TypeScript diagnostics.
3. **Backend Tests**: 100% of PyTest suites (including contract, security, retrieval, and NLI) must pass.
4. **Security Verification**: Zero SSRF bypasses, zero secret leaks, prompt injection successfully defanged.
5. **No Fabricated Numbers**: All evaluation tables and benchmark figures must reflect measured code executions.
