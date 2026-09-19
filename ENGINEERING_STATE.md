# ENGINEERING STATE

## CURRENT STEP
Step 10: Production-Minded Security and Resilience — COMPLETE

## COMPLETED STEPS
- Step 1: Frontend hardening (ESLint, Vitest, API client, mock fallback)
- Step 2: FastAPI backend + PostgreSQL persistence (SQLAlchemy 2.x, Alembic, 5 ORM models)
- Step 3: NLP dataset pipeline (X-Fact, FEVER, AVeriTeC download/normalize/split)
- Step 4: Real input understanding (language detection, text normalization, claim extraction)
- Step 5: Real multilingual NLP inference (XLM-RoBERTa classifier, tokenizer wrapper, model loader with controlled ML_UNAVAILABLE, model registry, hosted/test abstractions, fine_tune.py, evaluate.py)
- Step 6: Real evidence retrieval (EvidenceProvider abstraction, Google Fact Check Tools API client, LocalEvidenceProvider offline fallback with English/Hindi/Telugu fixtures, thread-safe TTL cache, prompt-injection defense, independent verdict preservation, end-to-end database persistence)
- Step 7: Evidence ranking and claim/evidence verification (Multilingual character/word n-gram TF-IDF semantic similarity, entity overlap, recency decay, composite relevance scoring, publisher/domain source-grouping to prevent syndication distortion, NLI language coverage validator for EN/HI/TE, MultilingualDeterministicNLI + LocalHuggingFace + HostedNLI backends, configurable thresholds & min relevance gate, synthesis across all edge cases, and end-to-end DB pipeline event recording)
- Step 8: Decision fusion and uncertainty-aware output (DecisionEngine, confidence tier calculation with bounds and caps, human-readable explanations, temperature scaling calibration with ECE and Brier score evaluation, versioned calibration registry, strict separation of model confidence vs evidence strength vs truth probability, and end-to-end DB pipeline event recording)
- Step 9: FastAPI backend and React frontend integration (Removed mock verification from production verification path, created typed `api/client.ts` and `api/analysis.ts`, updated `Pipeline.tsx` to 9 real backend states with zero artificial stalls, enhanced `Result.tsx` with calibrated confidence tiers, evidence cards with publishers and dates, uncertainty warnings, 'AI-assisted assessment' disclaimer, 'Run another analysis' flow, and 'Copy result' clipboard action)
- Step 10: Production-minded security and resilience (Input length limits, sliding-window request rate limiting with `X-RateLimit-*` & `Retry-After` headers, strict CORS, zero frontend API keys, structured JSON server logging with stage/latency observability, privacy-first text redaction in DB by default with configurable retention purging, ORM parameterized SQL injection defense, strict URL validation & SSRF protection blocking loopback/private/link-local/cloud-metadata networks, prompt injection defense, health probes `/health`, `/readiness`, `/model-health`, and graceful 503/400 failure mode degradation)

## CURRENT ARCHITECTURE
```
React SPA (Vite) → services/api/client.ts → RateLimitMiddleware → FastAPI (/api/v1/analyze)
                 → services/api/analysis.ts
                 → Pipeline.tsx (9 real backend stages)
                 → Result.tsx (measured confidence, tier, uncertainty, evidence trail)
                 → FastAPI Backend
                      ↳ Security & Rate Limiter (sliding window per IP)
                      ↳ Language Detection (langdetect: en/hi/te with ASCII English disambiguation)
                      ↳ Text Normalization (regex + unicodedata NFC)
                      ↳ Claim Extraction (spaCy en + regex hi/te)
                      ↳ Evidence Retrieval (Google Fact Check / Local fixtures + SSRF & prompt-injection defense + TTL cache)
                      ↳ Evidence Ranking (TF-IDF 3-5 gram + entity overlap + recency decay)
                      ↳ NLI & Verification (MultilingualDeterministicNLI / HF / Hosted)
                      ↳ ML Sequence Classification (XLM-RoBERTa / Hosted / Mock)
                      ↳ Post-Hoc Probability Calibration (temperature scaling T)
                      ↳ Uncertainty-Aware Decision Fusion (fused policy rules)
                      ↳ Privacy Layer (configurable input text redaction & retention purging)
                      ↳ Observability & Logging (JSON formatter, stage latencies, error masking)
                      ↳ Persistence (PostgreSQL / SQLite: Analysis, Claim, Evidence, ModelRun, Events)
```

## IMPORTANT FILES
| File | Purpose |
|------|---------|
| `src/services/api/client.ts` | Robust typed fetch client with base URL resolution, 15s timeout, AbortController, and error hierarchy (`BackendUnavailableError`, `TimeoutError`, `UnsupportedLanguageError`, `ValidationError`, `ApiError`) |
| `src/services/api/analysis.ts` | Backend request/response contracts, response mapping (`BackendAnalysisResponse` → `VerificationResult`), `analyzeClaim`, and `getAnalysisById` |
| `src/services/verificationService.ts` | Production verification entry point executing real backend calls and progressing through the 9 stages without artificial delays |
| `src/components/Pipeline.tsx` | Visual progress tracker reflecting the 9 actual backend pipeline stages |
| `src/components/Result.tsx` | Verification display with measured confidence, calibrated tier pill, publisher & date on evidence cards, uncertainty callout, AI disclaimer, "Run another analysis" flow, and "Copy result" clipboard action |
| `src/App.tsx` | Main application coordinating verification lifecycle, language dropdown passing, error handling banners with retry, and view routing |
| `src/__tests__/apiClient.test.ts` | 11 unit tests for API client headers, timeouts, error classification, response mapping, and health check |
| `src/__tests__/verificationFlow.test.ts` | 6 integration tests for real verification flow, stages, conflicting evidence, no evidence, timeout, and network errors |
| `src/mock/demoClaims.ts` | Explicitly marked development and test fixtures only |
| `src/services/mockVerificationService.ts` | Explicitly marked development and test fixture only |

## ENVIRONMENT VARIABLES
| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL for frontend requests |
| `VITE_API_URL` | `http://localhost:8000` | Fallback legacy API base URL |
| `DATABASE_URL` | `sqlite+aiosqlite:///./veritrace_dev.db` | DB connection |
| `APP_ENV` | `development` | Environment mode (`development` \| `production`) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `MAX_INPUT_LENGTH` | `10000` | Input text limit |
| `GOOGLE_FACTCHECK_API_KEY` | `None` | Google Fact Check Tools API key (server-side only) |
| `EVIDENCE_PROVIDER` | `google_factcheck` | Active provider (`google_factcheck` \| `local`) |
| `EVIDENCE_CACHE_TTL_SECONDS` | `3600` | In-memory TTL cache duration |
| `EVIDENCE_TIMEOUT_SECONDS` | `10.0` | HTTP request timeout |
| `EVIDENCE_MAX_RETRIES` | `2` | Retry attempts on 429/5xx |
| `EVIDENCE_MAX_RESULTS` | `10` | Max evidence results per search |
| `EVIDENCE_ENABLE_OFFLINE_FALLBACK` | `false` | Fallback to local fixtures if API key missing |
| `NLI_MODEL_NAME` | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | NLI sequence classification model identifier |
| `NLI_BACKEND` | `deterministic` | NLI backend (`deterministic`, `local`, `hosted`) |
| `NLI_ENDPOINT_URL` | `None` | Endpoint URL for hosted NLI inference |
| `NLI_API_KEY` | `None` | API key for hosted NLI inference |
| `NLI_ENTAILMENT_THRESHOLD` | `0.65` | Probability threshold for `SUPPORTS` relation |
| `NLI_CONTRADICTION_THRESHOLD` | `0.65` | Probability threshold for `CONTRADICTS` relation |
| `NLI_NEUTRAL_THRESHOLD` | `0.50` | Probability threshold for `NOT_ENOUGH_INFORMATION` |
| `EVIDENCE_MIN_RELEVANCE_THRESHOLD` | `0.30` | Minimum composite relevance score required for verification |
| `EVIDENCE_TOP_K` | `5` | Maximum number of top-ranked evidence candidates to verify |
| `RANKING_WEIGHT_SIMILARITY` | `0.60` | Weight for semantic/textual similarity in ranking |
| `RANKING_WEIGHT_ENTITY` | `0.25` | Weight for exact entity/keyword overlap in ranking |
| `RANKING_WEIGHT_RECENCY` | `0.15` | Weight for article recency decay in ranking |
| `CALIBRATION_TEMPERATURE` | `1.25` | Temperature parameter for post-hoc scaling of fine-tuned ML probabilities |
| `CALIBRATION_DATA_PATH` | `None` | Path to calibration registry JSON file |
| `CONFIDENCE_THRESHOLD_HIGH` | `0.80` | Minimum overall confidence score for `HIGH CONFIDENCE` tier |
| `CONFIDENCE_THRESHOLD_MODERATE` | `0.55` | Minimum overall confidence score for `MODERATE CONFIDENCE` tier |
| `CONFLICT_PENALTY_WEIGHT` | `0.30` | Penalty deducted from overall confidence score when conflict exists |
| `DECISION_MIN_INDEPENDENT_SOURCES_FOR_STRONG` | `2` | Minimum independent publisher count for strong evidence strength |
| `MODEL_NAME` | `FacebookAI/xlm-roberta-base` | Base model identifier |
| `MODEL_DEVICE` | `auto` | Execution device (`auto`, `cuda`, `mps`, `cpu`) |
| `MODEL_MAX_LENGTH` | `256` | Sequence truncation length |
| `MODEL_LOAD_ON_STARTUP` | `false` | Load model during lifespan startup |
| `MODEL_BACKEND` | `local` | `local` \| `hosted` \| `mock` |

## LAST TEST STATUS
```
Backend:  213/213 passed (23.19s)
ML:       34/34   passed (0.30s)
Frontend: 22/22   passed (1.87s)
Build:    0 errors, 0 warnings (tsc -b && vite build)
Total:    269 tests passed
```

## NEXT STEP
Production-minded security and resilience completed. Ready for demo / deployment.

