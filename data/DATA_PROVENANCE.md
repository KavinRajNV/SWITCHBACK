# Data provenance

Switchback's engine runs entirely off **MongoDB** at request time. The raw source
files below are only inputs to the offline data pipeline
(`backend/app/data_pipeline/`) that populated that database. They are **not**
tracked in git (`Datasets/` is `.gitignore`d) and are **not** required to run or
evaluate the app — `data/mongo_snapshot/` (committed) already contains the
processed collections the app queries.

| Source | Used for | Origin |
|---|---|---|
| Naukri job postings (Data1–2) | `jobs`, `market_roles`, salary model training | Public Kaggle Naukri.com job-listing datasets |
| Udemy course catalog (Data3–4) | `courses` (paid + free) | Public Kaggle Udemy course datasets |
| Coursera course catalog (Data5) | `courses` | Public Kaggle Coursera dataset |
| O\*NET 30.0 database (Data7) | `occupations_enriched`, `onet_related_occupations`, skill graph | U.S. Dept. of Labor O\*NET, public domain |
| ESCO taxonomy (Data6/8) | skill graph edges, skill vocabulary | European Commission ESCO, open licence |
| Curated skill vocabulary | `skill_vocabulary` (SkillMatcher) | Hand-curated seed list, `Datasets/curated_data/` |
| YouTube channel allowlist | `youtube_allowlist` | Hand-curated |

## Regenerating the snapshot

```bash
# with a populated Atlas / self-hosted switchback DB reachable via MONGODB_URI
python scripts/db/dump_switchback.py
```

## Rebuilding the database from raw files

Restore `Datasets/` locally, then:

```bash
python -m app.data_pipeline.run_pipeline      # from backend/, with the venv active
python -m app.ml.build_graph
python -m app.ml.build_occupations
python -m app.ml.train_salary_model
```
