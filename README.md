# Switchback — Personalized Learning-Path Recommender

> **HCLTech AMPlified 2026 Prototype**  
> *Core Competitive Bet*: **Zero LLM API calls anywhere in the product.** Every recommendation traces back to a real cleaned dataset, a real trained ML model, or a real graph computation.

---

## 🌟 Overview

**Switchback** is an end-to-end, personalized learning-path recommender that maps a learner's acquired skill baseline directly to target career roles cataloged across **1,016 O*NET occupations**. It calculates the minimum-friction learning sequence using a 21,000+ edge directed skill graph, predicts step-by-step salary elevation trajectories using a 323-feature `GradientBoostingRegressor`, and adapts dynamically as learners complete milestones.

---

## 🚀 Key Features

1. **Zero LLM Differentiator**: 100% deterministic skill extraction, layout-aware PDF sectioning, goal prompt parsing, templated SHAP explanations, and constrained Q&A.
2. **Deterministic Skill Graph**: Directed skill/occupation graph with 1,281 nodes and 21,137 edges. Path sequencing uses Dijkstra minimum-cost fringe expansion to produce focused 8–12 milestone paths.
3. **ML Salary & SHAP Elevation Model**: Trained on primary job postings with disclosed salaries. Evaluates cumulative LPA salary growth step-by-step.
4. **Live Integrations**: Real-time GitHub REST API skill verification (boosting confidence to Tier 9) and live Adzuna India job search integration with 30-minute MongoDB TTL caching.
5. **Monte Carlo Timeline Simulation**: 2,000-trial stochastic lognormal simulation outputting P10 (optimistic), P50 (realistic), and P90 (conservative) completion timelines in weeks.
6. **Interactive What-If Simulator**: 300ms debounced scenario simulator recalculating Dijkstra path deltas when learners toggle hypothetical skills.
7. **Learner Frontier Dashboard & Celebration**: Visualized salary trajectory split (solid completed vs dashed projected), milestone completion logging with ISO timestamps, and real O*NET primary-short stretch goals.

---

## 🏗️ Architecture & Technology Stack

- **Frontend**: Vite + React 18 + TypeScript + Tailwind CSS v4. Self-hosted fonts (`Space Grotesk`, `Inter`).
- **Backend API**: FastAPI (Python 3.10) with lifespan startup artifact caching.
- **Database**: MongoDB (Database: `switchback`, 16 collections, 517,071 documents).
- **ML / Graph Engines**: `scikit-learn` (`GradientBoostingRegressor`), `shap` (`TreeExplainer`), `NetworkX` (`DiGraph`), `rapidfuzz`.
- **NLP / Document Processing**: `pdfplumber`, `python-docx`, layout-aware section classifier.

---

## 🛠️ Local Development Setup

See **[SETUP.md](SETUP.md)** for the full offline walkthrough. Quick version:

### 1. Prerequisites
- **Python 3.11** (exact minor — the pinned `scikit-learn`/`numpy`/`scipy` have no wheels for 3.12+; `backend/.python-version` pins it)
- **Node.js 18+**
- **[uv](https://docs.astral.sh/uv/)** for the Python environment
- A MongoDB instance — either the bundled offline snapshot (`docker compose up -d`, no keys needed) or your own `MONGODB_URI` in `.env`

### 2. One command

```bash
cp .env.example .env          # optional: add ADZUNA / GITHUB / NVIDIA keys
./scripts/dev.sh              # macOS/Linux/Git-Bash
#  ── or ──
pwsh scripts/dev.ps1          # Windows PowerShell
```

This creates `backend/.venv` (Python 3.11), installs both dependency sets, starts the API on `http://127.0.0.1:8011` (Swagger at `/docs`) and the frontend on `http://127.0.0.1:5173`.

### 3. Manual (if you prefer)

```bash
uv venv backend/.venv --python 3.11
uv pip install --python backend/.venv -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8011 --reload

npm --prefix frontend install
npm --prefix frontend run dev
```

**Optional keys** (`.env`, all server-side, all with graceful fallbacks): `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` (live job strip), `GITHUB_TOKEN` (higher GitHub rate limit), `YOUTUBE_API_KEY` (free video suggestions), `NVIDIA_API_KEY` (nicer goal / assistant phrasing — never used for facts). Frontend: `frontend/.env` sets `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8011`).

---

## 🌐 Live Public Deployment URLs

- **Frontend Application**: `https://switchback-pathfinder.vercel.app`
- **Backend API Service**: `https://switchback-api.onrender.com`

---

## 🧪 Running Automated Tests

```bash
# Run backend Pytest suite (50+ unit/integration tests)
cd backend
python -m pytest

# Run production Vite build verification
cd frontend
npm run build

# Run Master End-to-End User Journey Test Script
python scripts/e2e_phase8_full_journey.py
```

---

## 📜 License

Built for HCLTech AMPlified 2026. All rights reserved.
