# scripts/legacy/

One-off diagnostic and data-repair scripts written during data engineering
(Phases 1–2). They target ad-hoc states of the raw `Datasets/` files and the
MongoDB collections at various points in the pipeline build.

**They are not part of the running application** and are not needed to set up,
run, or evaluate Switchback. They are kept only so the data-cleaning history is
auditable. Most expect `Datasets/` present locally and a live `MONGODB_URI`.

The maintained pipeline entry point is `backend/app/data_pipeline/run_pipeline.py`.
