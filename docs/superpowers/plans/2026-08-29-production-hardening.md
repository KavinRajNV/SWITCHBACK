# Switchback Production-Hardening & Conversational Assistant — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Execute tier-by-tier; run the smoke test after each tier.

**Goal:** Make Switchback boot from a clean clone with zero external dependencies, remove every hardcoded/fake value, add a real conversational assistant, and package the repo for hackathon submission.

**Architecture:** FastAPI backend (Python 3.11, MongoDB) + Vite/React 19 frontend. The recommendation engine stays 100% deterministic and data-grounded (skill graph + GradientBoosting salary model + SHAP). A thin conversational layer classifies free-text learner questions onto existing deterministic functions; an LLM (NVIDIA NIM, optional) is used only for intent parsing and phrasing, never for facts.

**Tech Stack:** FastAPI, uvicorn, pymongo, scikit-learn 1.2.2, shap, networkx, rapidfuzz · React 19, react-router 7, Tailwind v4, Vite 8 · Docker Compose + mongodump for the offline DB.

**Spec:** this document (brainstorm-approved 2026-08-29; deadline 31 Aug 2026, "maximise judging score", local-only delivery).

## Global Constraints

- **Python 3.11 only** for the backend. `scikit-learn==1.2.2`, `numpy<2.0`, `scipy<1.11` — do not bump (the joblib artifacts are version-bound). Enforce with `backend/.python-version` + uv.
- **No LLM in the fact path.** Skill graph, salary model, SHAP, and Mongo are the only sources of numbers/recommendations. NVIDIA NIM calls are optional, behind `NVIDIA_API_KEY`, and must degrade silently.
- **Offline-first.** The app must run with `docker compose up` + Atlas URI *unset*, using the bundled Mongo snapshot. Atlas stays as an optional override.
- **No secrets in git.** `.env` stays ignored; only `.env.example` is committed.
- **Drop the "Zero LLM API calls anywhere" headline** everywhere it appears (README, DEMO_SCRIPT, in-app copy). Replace with "deterministic, data-grounded engine + lightweight conversational assistant".
- Commit in small increments with meaningful messages so history reflects the work.
- Every commit message ends with the Co-Authored-By + Claude-Session trailers.

## File Map

### Backend — created
- `backend/.python-version` — pins `3.11`.
- `backend/app/ml/explainer_boot.py` — builds a fresh `shap.TreeExplainer(model)` at startup (replaces the broken pickle).
- `backend/app/nlp/assistant.py` — intent classification + free-text router over the 8 deterministic Q&A functions.
- `backend/app/api/assistant.py` — `POST /api/assistant/chat` router.
- `backend/tests/test_assistant.py` — intent-routing tests.
- `docker-compose.yml` (repo root) — `mongo:7` + restore-on-first-run.
- `scripts/db/dump_switchback.py` — one-off: export Atlas `switchback` → `data/mongo_snapshot/` (BSON).
- `scripts/db/restore_local.sh` / `.ps1` — `mongorestore` into the compose Mongo.
- `scripts/dev.ps1` / `scripts/dev.sh` — start backend + frontend together.
- `SETUP.md` — 5-minute offline setup.
- `LICENSE` — MIT.

### Backend — modified
- `backend/app/main.py` — build explainer via `explainer_boot`; pass `app.state.matcher` where the sequencer needs it; tighten CORS; scrub the global exception handler; mount the assistant router.
- `backend/app/ml/path_sequencer.py` — accept an injected `matcher`; stop calling `SkillMatcher.from_mongo` per request; cap path length to 12.
- `backend/app/api/path.py`, `progress.py`, `qa.py` — pass `request.app.state.matcher` into `generate_path`; remove silent param defaults in `qa.py` (raise 422 with a clear message instead of inventing `"AWS"`/`"Python"`).
- `backend/app/config.py` — add `ALLOWED_ORIGINS`, `APP_ENV`.
- `backend/requirements.txt` — add explicit `numba` pin that matches the shap build (verify), keep everything else.

### Frontend — modified
- `frontend/src/lib/api.ts` — add `sendAssistantMessage`; `API_BASE_URL` from `VITE_API_BASE_URL` (default `http://127.0.0.1:8011`); add `getHealth` typing.
- `frontend/src/pages/DashboardScreen.tsx` — render exclusively from the `/api/dashboard` payload; delete `+4`, `12.5`, `16.5`, `'Data Scientists'`, `'15-2051.00'`.
- `frontend/src/components/QAPanel.tsx` — chat transcript + free-text input; the 8 buttons become suggested prompts calling the same endpoint.
- `frontend/src/components/WhatIfSlider.tsx` — read `new_path`/`milestones_saved` correctly.
- `frontend/src/components/AppNavbar.tsx` (or `App.tsx`) — global "backend unreachable" banner from a `/health` poll.
- `frontend/.env.example` — `VITE_API_BASE_URL=http://127.0.0.1:8011`.
- `frontend/src/pages/StartScreen.tsx`, `TargetRoleScreen.tsx`, `PathScreen.tsx` — replace `|| 'Data Scientists'` fallbacks with redirect-to-`/start` guards.

### Repo hygiene — removed / moved
- Delete tracked `.pnpm-store/**`, `Assets_zip.zip`, stray `app/artifacts/**` (root copy, unused).
- Move `Datasets/**` → keep locally, `git rm --cached`, add `data/DATA_PROVENANCE.md`.
- Move root `diag_*.py fix_*.py check_*.py verify_*.py rebuild_*.py build_market_roles.py inspect_db.py optimize_assets.py` → `scripts/legacy/`.
- `.gitignore` — add `.pnpm-store/`, `Datasets/`, `.venv/`, `.uv-cache/`, `node_modules/`, `data/mongo_snapshot/` stays committed (it IS the deliverable DB).

---

## Tier 1 — Boots clean, no fiction

### Task 1.1: Fix startup (SHAP explainer) + pin Python

**Files:** Create `backend/app/ml/explainer_boot.py`, `backend/.python-version`; Modify `backend/app/main.py:47-52`.

- [ ] Create `backend/.python-version` containing `3.11`.
- [ ] Create `backend/app/ml/explainer_boot.py`:
  ```python
  """Build a fresh SHAP TreeExplainer at startup.

  The committed shap_explainer.joblib embeds numba code objects bound to the
  exact interpreter it was created with and fails to unpickle elsewhere
  (`TypeError: code() argument 13 must be str, not int`). A TreeExplainer over
  a fitted GradientBoostingRegressor rebuilds in ~0.02s with identical
  tree_path_dependent semantics, so we always build it live.
  """
  import shap

  def build_startup_explainer(salary_model):
      return shap.TreeExplainer(salary_model)
  ```
- [ ] In `backend/app/main.py`, replace the `shap_explainer = joblib.load(explainer_path)` block (and its `FileNotFoundError` guard) with:
  ```python
  from app.ml.explainer_boot import build_startup_explainer
  ...
  app.state.shap_explainer = build_startup_explainer(salary_model)
  print("  SHAP TreeExplainer built from salary model (fresh, no pickle).")
  ```
- [ ] Delete `backend/app/artifacts/shap_explainer.joblib` (it is gitignored; also remove from `app/` root copy in Task 3.1).
- [ ] Run: `cd backend && .venv/Scripts/python -m uvicorn app.main:app --port 8011` → expect `Application startup complete`, then `curl 127.0.0.1:8011/health` → `"status":"healthy"`.
- [ ] Commit: `fix(backend): build SHAP explainer at startup instead of loading broken pickle`.

### Task 1.2: Backend perf + safety (matcher reuse, path cap, CORS, errors)

**Files:** Modify `backend/app/ml/path_sequencer.py`, `backend/app/api/path.py`, `backend/app/api/progress.py`, `backend/app/nlp/qa_engine.py` (`answer_what_if_i_already_know_x`), `backend/app/main.py`, `backend/app/config.py`.

- [ ] `path_sequencer.generate_path(...)` — add `matcher=None` param; use it when provided, else fall back to `SkillMatcher.from_mongo(get_db())`. Remove the unconditional per-call `SkillMatcher.from_mongo`.
- [ ] Add `MAX_MILESTONES = 12`; after building `milestones`, if `len(milestones) > MAX_MILESTONES`, keep the first 12 (they are already cost-ordered) and log the truncation count.
- [ ] `path.py` / `progress.py` / `qa.py` call sites → pass `matcher=request.app.state.matcher`.
- [ ] `qa.py::ask_question` — for `what_if_i_already_know_x`, `why_this_skill`, `show_free_alternatives`, `explain_confidence_score`: if the needed `params.skill` (or `extra_skill`) is missing AND no stored path exists to infer from, `raise HTTPException(422, "This question needs a skill — select one first.")`. No more `"AWS"`/`"Python"` literals.
- [ ] `config.py` — add `APP_ENV = os.getenv("APP_ENV", "development")` and `ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")`.
- [ ] `main.py` CORS — `allow_origins=settings.ALLOWED_ORIGINS`, `allow_credentials=False` (no cookies used), keep methods/headers `*`.
- [ ] `main.py` global handler — in non-development, return `{"error":"InternalServerError","path":...}` without `str(exc)`; always `print` the full trace server-side.
- [ ] Run backend smoke: `python scripts/e2e_phase8_full_journey.py` (point it at `:8011`) → 100% pass.
- [ ] Commit: `perf(backend): reuse cached SkillMatcher, cap path at 12, harden CORS/errors`.

### Task 1.3: Dashboard renders real data (kill hardcoded values)

**Files:** Modify `frontend/src/pages/DashboardScreen.tsx`, `frontend/src/lib/api.ts` (add `DashboardResponse` type).

- [ ] Add a typed `DashboardResponse` to `api.ts` matching `backend/app/api/dashboard.py`'s return (`profile_summary`, `target_role`, `progress`, `next_action_milestone`, `elevation_profile`, `recent_activities`).
- [ ] `DashboardScreen` — store the full `getDashboardData` result in state; derive every stat from it:
  - "Acquired Baseline Skills" → `dash.profile_summary.total_acquired_skills` (delete `completedCount + 4`).
  - "Achieved LPA Elevation" → `dash.elevation_profile[min(completed, len-1)].cumulative_predicted_salary_lpa` (delete `|| 12.5`).
  - Target role / SOC → `dash.target_role.title` / `.onet_soc_code` (delete `|| 'Data Scientists'` / `|| '15-2051.00'`).
  - Progress % → `dash.progress.progress_percentage`.
  - Next action → `dash.next_action_milestone`.
- [ ] Adzuna-offline banner — remove the literal "₹16.5 LPA Median"; show `dash.target_role.market_median_salary_lpa` when present, else "market benchmark unavailable".
- [ ] If `getDashboardData` throws (session gone) → `navigate('/start')`.
- [ ] Manual check: run full journey in the browser; confirm dashboard numbers match the API `/docs` responses.
- [ ] Commit: `fix(frontend): dashboard renders live /api/dashboard payload, remove hardcoded values`.

### Task 1.4: Fix WhatIfSlider + session guards + frontend env

**Files:** Modify `frontend/src/components/WhatIfSlider.tsx`, `frontend/src/pages/{StartScreen,TargetRoleScreen,PathScreen}.tsx`, create `frontend/.env.example`, modify `frontend/src/lib/api.ts`.

- [ ] `WhatIfSlider` — the QA payload keys are `original_path_length`, `new_path_length`, `milestones_saved`, `new_path` (array of milestone dicts). Replace `payload.removed_milestones?.join(', ')` with a computed diff: skills in old stored path not in `payload.new_path`. "Milestones Removed" shows that list or "None".
- [ ] `api.ts` — `const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8011'`.
- [ ] Create `frontend/.env.example` → `VITE_API_BASE_URL=http://127.0.0.1:8011`.
- [ ] `PathScreen` / `TargetRoleScreen` / `DashboardScreen` — top-of-component guard: `if (!sessionId) return <Navigate to="/start" replace />`. Remove `|| 'Data Scientists'` display fallbacks (show the real value or a skeleton).
- [ ] Run: `cd frontend && npm run build` → passes; `npm run dev` → journey works.
- [ ] Commit: `fix(frontend): correct WhatIf payload keys, add session guards, VITE_API_BASE_URL`.

### Task 1.5: One-command startup + README/SETUP truth pass (interim)

**Files:** Create `scripts/dev.ps1`, `scripts/dev.sh`; Modify `README.md` "Local Development Setup" only.

- [ ] `scripts/dev.ps1` — create `.venv` via `uv venv --python 3.11` if missing, `uv pip install -r backend/requirements.txt`, start uvicorn on 8011, `npm --prefix frontend install`, `npm --prefix frontend run dev`. `dev.sh` mirrors it.
- [ ] README setup section — replace the `python -m venv venv` / `pip install` steps with the uv + Python 3.11 flow and port `8011`. (Full README rewrite is Task 3.3.)
- [ ] Commit: `chore: add dev.ps1/dev.sh one-command startup, fix setup docs`.

**Tier 1 exit check:** clean shell → `scripts/dev.ps1` → both servers up → full browser journey (resume/manual/goal → skills → role → path → dashboard → celebration) with zero console errors and no placeholder numbers.

---

## Tier 2 — Conversational assistant

### Task 2.1: Intent router (`assistant.py`)

**Files:** Create `backend/app/nlp/assistant.py`, `backend/tests/test_assistant.py`.

- [ ] Define `INTENTS`: the 8 existing `question_id`s + `general`. Each has trigger keywords/phrases and a required-param spec.
  ```python
  INTENTS = {
    "how_long_will_this_take": ["how long", "time", "weeks", "months", "duration", "finish"],
    "why_this_skill":          ["why", "this skill", "why do i need", "reason for"],
    "what_if_i_already_know_x": ["what if i know", "already know", "if i learn", "skip"],
    "show_free_alternatives":   ["free", "no cost", "without paying", "cheaper"],
    "why_this_role":            ["why this role", "why should i", "worth it", "salary of"],
    "am_i_qualified_already":   ["am i qualified", "ready for", "can i apply", "gap"],
    "what_skills_do_i_already_have": ["my skills", "what do i have", "current skills"],
    "explain_confidence_score": ["confidence", "score", "how is my", "rating"],
  }
  ```
- [ ] `classify_intent(text: str) -> tuple[str, dict]` — lowercase, score each intent by keyword hits + `rapidfuzz.partial_ratio`, extract a candidate skill by matching tokens against the passed skill vocabulary. Return `(intent_id, {"skill": ...})` or `("general", {})`.
- [ ] `route(text, session, db, graph, matcher, salary_model, shap_explainer) -> QAResponse` — call `classify_intent`, then dispatch to the matching `qa_engine.answer_*` (reuse them verbatim). For `general`, return a grounded summary: target role, path length, next milestone, current predicted salary — all from session + model. Prefix every answer with a one-line "read as: <intent>" rationale for explainability.
- [ ] Optional NVIDIA assist: if `settings.NVIDIA_API_KEY`, send `text` + the intent list and let the model pick the intent + skill (JSON-only, same hardening as `nvidia_goal.py`); on any failure fall back to `classify_intent`. Never let it produce the answer text's facts.
- [ ] Tests: 12+ cases mapping representative phrasings → expected intent; one test that `general` returns without raising; one that NVIDIA-absent path works.
- [ ] Run: `pytest backend/tests/test_assistant.py -v` → pass.
- [ ] Commit: `feat(backend): conversational intent router over deterministic Q&A`.

### Task 2.2: `POST /api/assistant/chat`

**Files:** Create `backend/app/api/assistant.py`; Modify `backend/app/main.py` (mount router).

- [ ] Request: `{ session_id, message, history?: [{role, content}] }`. Response: `{ reply, intent, rationale, structured_payload, suggestions: string[] }`.
- [ ] Load session; 404 if missing. Call `assistant.route(...)`. `suggestions` = 3 intent labels not yet used in `history`.
- [ ] Mount in `main.py`: `app.include_router(assistant.router)`.
- [ ] Manual: `curl -X POST :8011/api/assistant/chat -d '{"session_id":"<id>","message":"how many weeks will this take?"}'` → correct intent + grounded answer.
- [ ] Commit: `feat(backend): /api/assistant/chat endpoint`.

### Task 2.3: Chat UI

**Files:** Modify `frontend/src/components/QAPanel.tsx`, `frontend/src/lib/api.ts`.

- [ ] `api.ts` — `sendAssistantMessage(session_id, message, history)` → typed `AssistantReply`.
- [ ] `QAPanel` — transcript of user/assistant bubbles; text `<input>` + send; render `rationale` as a subtle line above each assistant reply; render `suggestions` as clickable chips that send that prompt. Keep the structured-payload mini-cards for `what_if` / `free_alternatives`. Keep the drawer + FAB.
- [ ] Header copy → "Trail Assistant" / "Grounded, explainable answers" (drop "Constrained Deterministic Q&A Engine").
- [ ] Run: `npm run build`; manual chat test in browser.
- [ ] Commit: `feat(frontend): conversational assistant panel with suggested prompts`.

### Task 2.4: Conversational goal clarification + "Why this?" affordances

**Files:** Modify `frontend/src/pages/StartScreen.tsx`, `TargetRoleScreen.tsx`, `PathScreen.tsx`.

- [ ] StartScreen "Express Your Goal" — after `parseGoalText`, if `goal_profile.needs_clarification` or missing timeframe/hours, show an inline assistant prompt ("I didn't catch a target role / timeframe — which role are you aiming for?") with a one-field reply that re-calls `parseGoalText` with the combined text, instead of proceeding on a guess.
- [ ] PathScreen milestone cards + TargetRoleScreen recommended-role cards — add a "Why this?" link that opens the assistant drawer pre-seeded with `why_this_skill` (skill=milestone.skill) / `why_this_role`.
- [ ] Run: `npm run build`; manual test both flows.
- [ ] Commit: `feat(frontend): conversational goal clarification + "Why this?" links`.

**Tier 2 exit check:** free-text questions ("will I be ready for this role?", "cheaper way to learn Docker?", "how long?") return correct grounded answers with visible rationale; goal entry asks a follow-up instead of guessing.

---

## Tier 3 — Offline DB + packaging

### Task 3.1: Repo hygiene

- [ ] `git rm -r --cached .pnpm-store Assets_zip.zip app/artifacts` ; delete `.pnpm-store/`, `Assets_zip.zip`, `app/` (root artifacts copy) from disk.
- [ ] `mkdir scripts/legacy && git mv` the root `diag_*.py fix_*.py check_*.py verify_*.py rebuild_*.py build_market_roles.py inspect_db.py optimize_assets.py verify_output.txt` into it; add `scripts/legacy/README.md` ("one-off pipeline/debug scripts, kept for provenance, not part of runtime").
- [ ] `git rm -r --cached Datasets` ; add `data/DATA_PROVENANCE.md` listing each source (Naukri, Udemy, Coursera, O*NET db_30_3, ESCO) + "runtime reads MongoDB, not these files".
- [ ] `.gitignore` — add `.pnpm-store/`, `Datasets/`, `backend/.venv/`, `.uv-cache/`, `**/node_modules/`, `*.joblib` stays ignored, keep `data/mongo_snapshot/` tracked.
- [ ] Commit: `chore: remove build/store/dataset bloat from source tree`.

### Task 3.2: Offline MongoDB (snapshot + compose)

**Files:** Create `scripts/db/dump_switchback.py`, `docker-compose.yml`, `scripts/db/restore_local.ps1` + `.sh`, `data/mongo_snapshot/` (BSON output).

- [ ] `dump_switchback.py` — connect with the Atlas URI from `.env`, `mongodump` each of the 23 collections (or shell out to `mongodump --uri --db switchback --out data/mongo_snapshot`). Exclude `learner_sessions` (regenerated at runtime) and `*_cache`.
- [ ] Run it once; verify `data/mongo_snapshot/switchback/*.bson` totals a sane size; commit the snapshot (this is deliverable DB state — note size in the commit body).
- [ ] `docker-compose.yml` — `mongo:7` service, volume mount `./data/mongo_snapshot:/snapshot:ro`, plus a one-shot `mongo-restore` service running `mongorestore --drop /snapshot`.
- [ ] `restore_local.*` — for users with a native `mongod` instead of Docker.
- [ ] `config.py` / `mongo_client.py` — default `MONGODB_URI` to `mongodb://localhost:27017` when unset (instead of raising), so compose Mongo works with an empty `.env`.
- [ ] Run: `docker compose up -d` with `.env` MONGODB_URI blank → backend `/health` healthy → journey works fully offline.
- [ ] Commit: `feat: bundled MongoDB snapshot + docker-compose for fully offline runs`.

### Task 3.3: README + SETUP + LICENSE + copy pass

**Files:** Modify `README.md`, `DEMO_SCRIPT.md`; Create `SETUP.md`, `LICENSE`.

- [ ] `SETUP.md` — "Run offline in 5 minutes": prereqs (Docker OR Python 3.11 + Node 18 + local mongod), `docker compose up -d`, `scripts/dev.*`, URLs, troubleshooting.
- [ ] `README.md` full rewrite — overview; the 6 problem-statement features mapped to where each lives (conversational interface → StartScreen + `/api/assistant`; profiling → `/api/profile/*`; recommendation → `/api/roles/recommended`; path generator → `/api/path/generate`; explainer assistant → `/api/assistant/chat`; dashboard → `/api/dashboard`); architecture diagram (ASCII); AI/ML techniques (graph Dijkstra, GradientBoosting + SHAP, intent classification); challenges faced; local-run pointer to `SETUP.md`. Remove dead deploy URLs and the "Zero LLM" headline.
- [ ] `DEMO_SCRIPT.md` — strike "Zero LLM API calls anywhere"; reword to "deterministic grounded engine + explainable assistant".
- [ ] `LICENSE` — MIT, current year, team placeholder.
- [ ] Commit: `docs: rewrite README, add SETUP.md + LICENSE, drop Zero-LLM claim`.

### Task 3.4: Final verification

- [ ] Fresh clone into a temp dir; `.env` from `.env.example` with **no** Atlas URI; `docker compose up -d`; `scripts/dev.*`.
- [ ] Run `python scripts/e2e_phase8_full_journey.py` → 100% pass.
- [ ] Browser: all 7 screens, assistant chat, what-if, milestone completion, celebration — zero console errors, zero placeholder values.
- [ ] `npm --prefix frontend run build` clean; `pytest backend` green.
- [ ] Commit: `chore: final verification pass for submission`.

---

## Self-Review

- **Spec coverage:** boot fix (1.1) ✓ · hardcoded values (1.3, 1.4) ✓ · perf (1.2) ✓ · conversational interface (2.1–2.4) ✓ · explainer assistant (2.1–2.3) ✓ · profiling/recommendation/path/dashboard already exist, verified in 3.4 ✓ · offline DB (3.2) ✓ · repo/deliverables (3.1, 3.3) ✓ · reframe messaging (3.3, global constraint) ✓.
- **Deferred by decision:** cloud deploy, auth, model retraining, test-suite expansion, solution-doc/video.
- **Risk:** `mongodump`/`mongorestore` binaries may not be present → Task 3.2 falls back to a p(slower) pymongo JSON export + a Python restore script; still commit-able.
- **Risk:** committing the Mongo snapshot could be large. If `> ~80 MB`, drop `onet_knowledge`/`onet_job_titles` (unused at runtime — grep confirms only `onet_related_occupations`, `occupations_enriched`, `courses`, `market_roles`, `skill_vocabulary`, `*_cache` are queried live) and note the reduction.
