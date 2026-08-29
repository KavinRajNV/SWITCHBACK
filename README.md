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

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB instance with populated `switchback` database
- NVIDIA API key from [build.nvidia.com](https://build.nvidia.com/) for the Express Your Goal AI extractor

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Unix:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8001
```
Backend API will run at `http://localhost:8001` with Swagger docs at `http://localhost:8001/docs`.

Before starting the backend, add the NVIDIA settings to the project `.env` file:
```bash
NVIDIA_API_KEY=your_build_nvidia_api_key
NVIDIA_MODEL=openai/gpt-oss-20b
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```
The key stays server-side. If it is omitted or NVIDIA is temporarily unavailable, Express Your Goal falls back to the existing deterministic parser.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend development server will run at `http://localhost:5173`.

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
