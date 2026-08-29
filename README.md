# Switchback — AI-Powered Personalized Learning-Path Recommender

Switchback turns a learner's goal, described in plain language, into a **structured,
explainable roadmap**: the exact sequence of skills to acquire, the courses and
projects for each, a predicted salary trajectory, and an assistant that answers
"why this?" at every step — then re-plans as milestones are completed.

Every recommendation traces back to real data: a cleaned dataset, a trained ML
model, or a graph computation. A language model is used only, and optionally, to
phrase and route the conversational layer — never as a source of facts.

---

## What it does — mapped to the brief

| Required capability | Where it lives |
|---|---|
| **Conversational interface** — describe goals in natural language | `/start` "Express Your Goal" → `POST /api/profile/from-goal-text` (deterministic parser + optional NVIDIA skill extraction, with a one-question clarification loop when the role is ambiguous) |
| **Learner profiling engine** — interests, level, completed courses, objectives | `POST /api/profile/from-resume` (layout-aware PDF/DOCX sectioning + confidence scoring), `/api/profile/manual-skills`, `POST /api/live/github-verify` (repo-language evidence → Tier-9 confidence) |
| **Recommendation engine** — courses, projects, resources | `GET /api/roles/recommended` (IDF-weighted skill-overlap role fit), per-milestone course ranking over 105k Udemy/Coursera courses + a curated YouTube allowlist, free/paid split |
| **Learning-path generator** — prerequisites & milestones | `POST /api/path/generate` — Dijkstra-style minimum-cost fringe expansion over a 1,281-node / 21,137-edge skill graph, capped to the 12 most reachable milestones, each with a gap explanation |
| **AI assistant** — explains recommendations, answers queries | `POST /api/assistant/chat` — free text → intent classification onto 8 grounded functions (+ a status summary), each reply carries a one-line rationale and structured payload; `/api/qa/ask` is the structured backend |
| **Progress dashboard** — progress, skills, milestones, next actions | `GET /api/dashboard` + `/dashboard` screen: real skill count, model-predicted salary, % complete, next action, and a completed-vs-projected salary trajectory chart; completing a milestone re-runs the planner |

---

## Architecture

```
┌────────────────────────────┐        ┌──────────────────────────────────────────┐
│  React 19 + Vite + TW v4   │  HTTP  │  FastAPI (Python 3.11)                    │
│  7 screens + Trail         │ ─────► │  lifespan-cached: SkillMatcher, salary    │
│  Assistant chat panel      │ ◄───── │  model, SHAP explainer, skill graph,      │
└────────────────────────────┘  JSON  │  occupation catalog, IDF weights          │
                                      │                                          │
                                      │  nlp/  assistant · goal_parser · resume   │
                                      │  ml/   path_sequencer · features · explain│
                                      │  api/  profile path qa progress dashboard │
                                      │        live assistant                    │
                                      └───────────────┬──────────────────────────┘
                                                      │  pymongo
                                      ┌───────────────▼──────────────────────────┐
                                      │  MongoDB  (bundled offline snapshot, or  │
                                      │  your own): occupations_enriched,        │
                                      │  courses, market_roles, skill_vocabulary,│
                                      │  onet_related_occupations, youtube_...    │
                                      └──────────────────────────────────────────┘
```

Model artifacts (`backend/app/artifacts/`): `salary_model.joblib`
(GradientBoostingRegressor, 323 features), `skill_graph.pkl` (NetworkX DiGraph),
`feature_manifest.json`. The SHAP `TreeExplainer` is rebuilt from the model at
startup (its pickled form is interpreter-bound and not portable).

---

## AI / ML techniques

- **Skill graph + shortest path.** A directed graph of skill→skill and
  occupation→skill relations from O\*NET and ESCO. The planner does greedy
  minimum-cost fringe expansion (Dijkstra-style) from the learner's owned skills
  to the target role's required set, yielding an ordered milestone list with
  per-edge transition costs.
- **Salary trajectory model.** `GradientBoostingRegressor` trained on Indian job
  postings with disclosed salaries — 323 one-hot skill / seniority / location /
  company features. The dashboard plots cumulative predicted LPA as each
  milestone skill is added.
- **SHAP explanations.** `TreeExplainer` over the salary model gives per-skill
  LPA contribution, surfaced in milestone and "why this skill" answers.
- **Deterministic NLP.** Layout-aware resume sectioning (`pdfplumber` font
  coordinates), `rapidfuzz` skill/role matching against a 265-skill vocabulary
  and 1,016 O\*NET titles, regex timeframe/seniority parsing.
- **Intent classification** for the assistant: keyword + fuzzy scoring maps free
  text onto 8 grounded functions; an optional NVIDIA NIM call disambiguates only
  when that classifier is unsure, and only chooses an intent — never writes facts.
- **Adaptive re-planning.** Completing a milestone updates the skill frontier and
  re-runs the planner; the "what-if" simulator recomputes path deltas live.

---

## Run it

See **[SETUP.md](SETUP.md)**. Short version:

```bash
cp .env.example .env
docker compose up -d          # bundled offline MongoDB (no keys needed)
./scripts/dev.sh              # or: pwsh scripts/dev.ps1
# API  → http://127.0.0.1:8011/docs
# Web  → http://127.0.0.1:5173
```

Optional keys in `.env` (all degrade gracefully): `ADZUNA_*` (live job strip),
`GITHUB_TOKEN` (rate limit), `YOUTUBE_API_KEY` (video suggestions),
`NVIDIA_API_KEY` (assistant/goal phrasing).

---

## Tests

```bash
cd backend && ../backend/.venv/bin/python -m pytest -q          # 67 unit/integration tests
SWITCHBACK_API_BASE=http://127.0.0.1:8011 \
  backend/.venv/bin/python scripts/e2e_phase8_full_journey.py   # full user journey
npm --prefix frontend run build                                 # typecheck + prod build
```

---

## Challenges faced

- **Portable ML artifacts.** The SHAP explainer pickle embedded interpreter-bound
  numba code objects and crashed on any other machine — resolved by rebuilding it
  from the model at startup.
- **Dependency pinning vs. Python version.** The trained model requires
  `scikit-learn 1.2.2`; that constrains the backend to Python 3.11. Pinned
  explicitly and documented rather than forcing a fragile retrain.
- **Offline reproducibility.** The engine needs ~56 MB of MongoDB data. Rather
  than depend on a shared cluster at evaluation time, the request-path collections
  are snapshotted into the repo and restored by `docker compose`.
- **Grounding the conversation.** Keeping a natural-language assistant useful
  *without* letting an LLM invent salaries or courses: the LLM only classifies
  intent; all figures come from the model, graph, and database.
- **Noisy salary signal.** Disclosed-salary postings are sparse and noisy; the
  model is used for *relative* trajectory shape, not absolute precision.

---

## Repository layout

```
backend/            FastAPI app, ML/NLP modules, pipeline, tests, model artifacts
frontend/           React app (7 screens + assistant panel)
data/mongo_snapshot/ committed offline DB snapshot (restored by docker compose)
scripts/            dev.sh / dev.ps1, db dump/restore, e2e journey, legacy/
docs/               design + implementation plan
```

## License

[MIT](LICENSE).
