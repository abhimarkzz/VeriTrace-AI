<p align="center">
  <img src="public/veritrace-icon.png" width="90" alt="VeriTrace AI Icon" />
  <br />
  <img src="public/veritrace-logo.png" width="340" alt="VeriTrace AI Logo" />
</p>

<h3 align="center">Multilingual Evidence-Grounded Misinformation Detection and Verification Intelligence</h3>

<p align="center">
  <em>“Detect the claim. Trace the evidence.”</em>
</p>

<p align="center">
  <a href="#key-capabilities">Key Capabilities</a> •
  <a href="#2-architecture--pipeline-flow">Architecture</a> •
  <a href="#3-supported-languages">Languages</a> •
  <a href="#4-quick-start">Quick Start</a> •
  <a href="#5-model-evaluation--calibration">Evaluation</a> •
  <a href="#8-security--responsible-ai">Responsible AI</a>
</p>

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **In a world of endless information, what's the truth?**  
> VeriTrace AI cuts through the noise, verifies claims in English, Hindi, and Telugu, and provides a clear, calibrated, evidence-backed trail for every verdict.

---

## 1. Project Overview

VeriTrace AI is a production-minded, uncertainty-aware fact verification platform. Unlike simplistic chatbots or black-box classifiers that output ungrounded assertions, VeriTrace adheres to the core axiom:

$$\text{Model Confidence} \neq \text{Evidence Strength} \neq \text{Truth Probability}$$

### Key Capabilities:
- **Multilingual Verification**: Native processing for **English (`en`)**, **Hindi (`hi`)**, and **Telugu (`te`)** with Unicode NFC normalization and cross-lingual heuristics.
- **Explainable Claim Extraction**: Deconstructs forwarded messages, articles, and social media posts into verifiable factual propositions using dependency parsing and entity extraction.
- **Dynamic Evidence Retrieval**: Integrates with the **Google Fact Check Tools API** and maintains a verified offline fixture repository with Time-To-Live (TTL) caching and domain deduplication.
- **Cross-Lingual NLI Verification**: Verifies claim/evidence pairs using semantic entailment, numerical checking, date consistency, and explicit negation detection.
- **Uncertainty Calibration & Decision Fusion**: Uses Temperature Scaling ($T$) to correct deep learning overconfidence, routing unevidenced or conflicting claims into safety states (`INSUFFICIENT_EVIDENCE`, `CONFLICTING_EVIDENCE`).
- **Production Security & Privacy**: Sliding-window rate limiting, SSRF defense against internal networks and cloud metadata, prompt injection defanging, and configurable zero-retention policies.

---

## 2. Architecture & Pipeline Flow

```
                      [ User Input (Text / Forward / Claim) ]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 1. Text Normalization & Sanitization  │
                     │    - Unicode NFC, URL/mention strip   │
                     │    - Length check (≤ 10,000 chars)    │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 2. Language Detection                 │
                     │    - English (en), Hindi (hi), Telugu │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 3. Claim Extraction & Checkability    │
                     │    - Factual proposition segmentation │
                     │    - Filter opinions & predictions    │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 4. Sequence Classification (XLM-R)    │
                     │    - Multi-class prior probabilities  │
                     │    - Temperature scaling calibration  │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 5. Evidence Retrieval & Deduplication │
                     │    - Google Fact Check Tools API      │
                     │    - Offline verified fixtures cache  │
                     │    - Publisher / Domain grouping      │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 6. Ranking & Multilingual NLI         │
                     │    - Composite relevance scoring      │
                     │    - Entailment vs Contradiction      │
                     │    - Number & Date shift verification │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │ 7. Decision Engine & Uncertainty      │
                     │    - Evidence strength evaluation     │
                     │    - Contradiction & conflict checks  │
                     │    - Policy-guided verdict derivation │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
             [ Structured Verdict: Result.tsx + Confidence Breakdown ]
```

---

## 3. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite | Interactive UI, dynamic pipeline stages, confidence breakdown |
| **Styling** | Modern Vanilla CSS | Dark mode, glassmorphism, responsive mobile/desktop layouts |
| **Backend API** | FastAPI, Uvicorn, Python 3.12 | Asynchronous REST API, OpenAPI 3.1, structured logging |
| **NLP & ML** | HuggingFace Transformers, spaCy, Scikit-Learn | XLM-RoBERTa, dependency parsing, TF-IDF cosine similarity |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (Async), Alembic | Relational persistence, migrations, SQLite async fallback |
| **Orchestration** | Docker, Docker Compose, Nginx | Multi-stage reproducible containerization, health checks |
| **Testing** | PyTest, Vitest, Testing Library, HTTPX | Full test pyramid: unit, contract, security, E2E |

---

## 4. Local Development

### Prerequisites
- Python 3.11+ (Python 3.12 recommended)
- Node.js v18+ & npm v9+
- Git

### Step-by-Step Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/veritrace-ai/veritrace-ai.git
   cd veritrace-ai
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   cp ../.env.example .env
   alembic upgrade head
   uvicorn app.main:app --reload --port 8000
   ```

3. **Frontend Setup**:
   ```bash
   # From project root in a new terminal
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

## 5. Database Setup & Migrations

VeriTrace AI uses SQLAlchemy 2.0 Async with support for both SQLite (local development/tests) and PostgreSQL (production).

### Running Migrations:
```bash
cd backend
source venv/bin/activate

# Apply latest schema migrations
alembic upgrade head

# Create a new migration revision
alembic revision --autogenerate -m "describe_changes"

# Rollback one migration
alembic downgrade -1
```

### Supported Connection Strings:
- **PostgreSQL (Async Engine)**: `postgresql+asyncpg://user:pass@host:5432/dbname`
- **SQLite (Async Engine)**: `sqlite+aiosqlite:///./veritrace_dev.db`

---

## 6. Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./veritrace_dev.db` | SQLAlchemy async connection URI |
| `GOOGLE_FACTCHECK_API_KEY` | *(empty)* | API key for Google Fact Check Tools API |
| `MODEL_NAME` | `FacebookAI/xlm-roberta-base` | Multilingual NLP model direction |
| `MODEL_DEVICE` | `auto` | Execution device: `cpu`, `cuda`, `mps`, or `auto` |
| `MODEL_MAX_LENGTH` | `256` | Maximum token sequence length |
| `MODEL_LOAD_ON_STARTUP` | `false` | Load weights on boot (`true` for production GPU) |
| `MODEL_BACKEND` | `local` | `local`, `hosted`, or `mock` |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL for frontend client |
| `LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Allowed origin URLs for browser requests |
| `RATE_LIMIT_ENABLED` | `true` | Enable sliding-window rate throttling |
| `RATE_LIMIT_REQUESTS` | `60` | Maximum requests permitted per minute |
| `PERSIST_USER_INPUT_TEXT` | `false` | Redacts text to SHA-256 in DB for privacy |
| `DATA_RETENTION_DAYS` | `7` | Days to retain records before automatic purging |

---

## 7. Dataset Preparation

VeriTrace provides an end-to-end dataset pipeline supporting **X-Fact** (ACL 2021), **FEVER** (NAACL 2018), and **AVeriTeC** (NeurIPS 2024).

### Pipeline Execution:
```bash
# 1. Download source datasets into data/raw/
python -m ml.datasets.download --config ml/configs/dataset_config.yaml

# 2. Normalize disparate schemas to VeriTrace common format
python -m ml.datasets.normalize --input_dir data/raw --output_file data/processed/all.jsonl

# 3. Create stratified train/val/test splits (80/10/10)
python -m ml.datasets.split --input_file data/processed/all.jsonl --output_dir data/processed

# 4. Validate split integrity, schema, and label balance
python -m ml.datasets.validate --data_dir data/processed
```

---

## 8. Model Preparation & Calibration

### Fine-Tuning XLM-RoBERTa:
```bash
python -m ml.training.fine_tune \
  --train_file data/processed/train.jsonl \
  --val_file data/processed/val.jsonl \
  --output_dir models/veritrace-xlmr-v1 \
  --epochs 3 \
  --batch_size 16
```

### Running Model Evaluation & Temperature Scaling:
```bash
backend/venv/bin/python3 ml/evaluation/run_evaluation.py
```
This evaluates test claims, fits the optimal temperature scaling parameter ($T$), computes Expected Calibration Error (ECE) across 10 reliability bins, and saves output to `ml/evaluation/eval_results.json`.

---

## 9. API Documentation

When the backend is running, access the interactive OpenAPI documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

### Key Endpoints:

#### `POST /api/v1/analyze`
Submits a claim or message for complete verification.
```json
// Request
{
  "text": "Reserve Bank of India maintained policy repo rate at 6.5 percent.",
  "language": "auto"
}

// Response
{
  "analysis_id": "a1b2c3d4e5f6",
  "language": "en",
  "claim": "Reserve Bank of India maintained policy repo rate at 6.5 percent.",
  "claim_type": "Financial policy claim",
  "assessment": "SUPPORTED",
  "confidence": 0.92,
  "confidence_tier": "HIGH CONFIDENCE",
  "evidence_strength": "STRONG",
  "confidence_breakdown": {
    "evidence_agreement": 0.96,
    "evidence_relevance": 0.94,
    "source_quality": 0.92,
    "model_confidence": 0.88
  },
  "evidence": [
    {
      "id": "ev-001",
      "title": "RBI Monetary Policy Committee Statement",
      "source": "Reserve Bank of India",
      "publisher": "RBI Official",
      "url": "https://rbi.org.in/press/2024",
      "snippet": "The MPC decided to keep the policy repo rate unchanged at 6.50 percent.",
      "relevance_score": 0.97,
      "source_quality": 0.95,
      "relation": "SUPPORT"
    }
  ],
  "explanation": "Official Reserve Bank of India documentation validates the rate maintenance.",
  "pipeline_status": "completed"
}
```

#### `GET /api/v1/analysis/{analysis_id}`
Retrieves a previously computed verification result.

#### Health Probes:
- `GET /health` — Liveness check.
- `GET /readiness` — Readiness probe (validates database connection).
- `GET /model-health` — Model status, active device, and load time.

---

## 10. Testing

VeriTrace AI enforces a comprehensive test suite across unit, contract, integration, adversarial, and end-to-end smoke testing.

### 1. Frontend Test Suite (Vitest)
```bash
npm test -- --run
```
Executes 36 unit and component tests verifying UI views, landing page, real-time pipeline transitions, evidence cards, multi-turn analysis flows, and error recovery banners.

### 2. Backend Test Suite (PyTest)
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```
Executes 260 tests validating schema contracts, API endpoints, language detection, claim extraction, NLI ranking, temperature calibration, rate limiting, and security sanitization.

### 3. API Health Test
```bash
# Liveness probe
curl -f http://localhost:8000/health

# Readiness probe (verifies database connectivity)
curl -f http://localhost:8000/readiness

# Model inference health probe
curl -f http://localhost:8000/model-health
```

### 4. Database Migration Test
```bash
# Verify current schema migration revision against Alembic head
docker compose exec backend alembic current

# Run migrations explicitly (applied automatically by entrypoint on boot)
docker compose exec backend alembic upgrade head
```

### 5. End-to-End Deployment Smoke Test
```bash
python3 scripts/e2e_smoke_test.py
```
Validates system end-to-end against live containers, performing health checks, database readiness verification, multilingual claim analysis (English, Hindi, Telugu), and record persistence checks.

### 6. Performance & Concurrency Benchmarks
```bash
backend/venv/bin/python3 backend/scripts/benchmark_performance.py
```

---

## 11. Deployment

### Quickstart with Docker Compose

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env if you have a Google Fact Check API key or need custom port mappings
   ```

2. **Build Container Images**:
   ```bash
   docker compose build
   ```

3. **Launch All Services**:
   ```bash
   docker compose up -d
   ```

4. **Verify Container Health**:
   ```bash
   docker compose ps
   ```
   All three services (`veritrace-postgres`, `veritrace-backend`, `veritrace-frontend`) will report `(healthy)`.

5. **Run End-to-End Verification**:
   ```bash
   python3 scripts/e2e_smoke_test.py
   ```

6. **Access Applications**:
   - **Frontend UI**: `http://localhost:5173`
   - **Backend API**: `http://localhost:8000`
   - **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`
   - **ReDoc**: `http://localhost:8000/redoc`

7. **Stop Services**:
   ```bash
   docker compose down
   # To wipe persistent database volume:
   docker compose down -v
   ```

---

## 12. Known Limitations

In the spirit of honest and transparent AI engineering, the following limitations are documented:
1. **Offline Retrieval Mode**: When `GOOGLE_FACTCHECK_API_KEY` is not provided, VeriTrace uses local fixtures. For claims outside local fixtures, it returns 0 evidence items, correctly defaulting to `INSUFFICIENT_EVIDENCE`.
2. **Subject Substitution in Lexical NLI**: In deterministic offline mode, statements that share identical numbers and keywords but alter the named entity (e.g. *"Apple profits grew 20%"* vs *"Tesla profits grew 20%"*) require entity overlap checks to prevent false support.
3. **Regional Code-Switching**: While Hinglish and Tenglish are supported, heavy colloquial slang without standard root words may trigger lower language confidence.

---

## 13. Responsible-Use Statement

> **Notice**: VeriTrace AI is an assistive decision-support tool designed for media literacy, journalistic research, and public interest fact verification. It does not replace human editorial judgment.

- **Non-Defamatory Intent**: Verdicts reflect synthesized corroboration from public authoritative records, not absolute truth judgements about individuals or institutions.
- **Evidence Visibility**: Every assessment displays its primary sources, publisher attribution, and direct external links so users can inspect evidence independently.
- **Uncertainty Principle**: When evidence is incomplete or conflicting, VeriTrace explicitly declines to issue a confident verdict, presenting the conflicting viewpoints and transparent uncertainty sub-scores.
