# Running Switchback locally

Two ways to get the database: **A) bundled offline snapshot via Docker** (nothing
to sign up for) or **B) your own MongoDB**. Then start the app the same way for both.

---

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | creates the Python 3.11 env (it can fetch 3.11 itself) |
| Node.js | 18+ | frontend build/dev server |
| Docker Desktop | any recent | **only for option A** (offline MongoDB) |

> The backend **must** run on **Python 3.11** — the pinned `scikit-learn` /
> `numpy` / `scipy` (needed to load the trained model without a retrain) have no
> wheels for 3.12+. `backend/.python-version` pins it and `uv` handles the rest.

---

## 1. Get the code + config

```bash
git clone <repo-url> switchback && cd switchback
cp .env.example .env          # every value is optional; see comments in the file
```

## 2A. Database — bundled offline snapshot (recommended)

```bash
docker compose up -d          # starts MongoDB and restores data/mongo_snapshot/
```

Leave `MONGODB_URI` **blank** in `.env` — the app then talks to
`mongodb://localhost:27017`. First `up` takes ~30 s to restore ~56 MB.

_No Docker?_ If you have a local `mongod` running, load the snapshot with pymongo:

```bash
uv run --python 3.11 --with pymongo python scripts/db/restore_local.py
```

## 2B. Database — your own MongoDB

Set `MONGODB_URI` in `.env` to a MongoDB instance that already has the
`switchback` database populated (or run the pipeline in
[`data/DATA_PROVENANCE.md`](data/DATA_PROVENANCE.md)).

## 3. Start everything

```bash
./scripts/dev.sh              # macOS / Linux / Git-Bash
pwsh scripts/dev.ps1          # Windows PowerShell
```

This creates `backend/.venv` (Python 3.11) via uv, installs backend + frontend
dependencies, and starts:

- **API** → http://127.0.0.1:8011  (Swagger UI at `/docs`, health at `/health`)
- **Web** → http://127.0.0.1:5173

Open the web URL and click **Get Started**.

### Manual start (equivalent)

```bash
uv venv backend/.venv --python 3.11
uv pip install --python backend/.venv -r backend/requirements.txt
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --port 8011 --reload
#           ^ backend/.venv/Scripts/python.exe on Windows

npm --prefix frontend install
cp frontend/.env.example frontend/.env
npm --prefix frontend run dev
```

---

## Verify

```bash
curl http://127.0.0.1:8011/health
# {"status":"healthy", ...}

SWITCHBACK_API_BASE=http://127.0.0.1:8011 \
  backend/.venv/bin/python scripts/e2e_phase8_full_journey.py
# ... PHASE 8 MASTER E2E INTEGRATION TEST PASSED 100% ...

cd backend && ../backend/.venv/bin/python -m pytest -q
# 67 passed
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Cannot reach MongoDB at 'mongodb://localhost:27017'` | `docker compose up -d`, or set `MONGODB_URI` in `.env` |
| `code() argument 13 must be str` on startup | stale `backend/app/artifacts/shap_explainer.joblib` — delete it (it is rebuilt at boot) |
| backend install fails compiling scipy/scikit-learn | you are not on Python 3.11 — `uv venv backend/.venv --python 3.11` |
| browser calls blocked by CORS | add your web origin to `ALLOWED_ORIGINS` in `.env` |
| frontend can't reach API | set `VITE_API_BASE_URL` in `frontend/.env` |
