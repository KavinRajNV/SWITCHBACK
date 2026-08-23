"""Repair historic ``is_paid`` values in the Switchback courses collection.

The first import used ``bool(csv_value)``.  Since ``bool('False')`` is True,
free Udemy courses were stored as paid and disappeared from Free Learning
Options.  This one-time repair only updates the *switchback.courses*
collection and never accesses any other database.

Run after deploying the ``parse_is_paid`` fix:
    $env:PYTHONPATH = 'D:/switchback/backend'
    python D:/switchback/scripts/repair_course_access_flags.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.data_pipeline.clean_courses import parse_is_paid
from app.db.mongo_client import get_db


def repair_file(path: Path, title_column: str) -> int:
    if not path.exists():
        print(f"Skipped missing dataset: {path}")
        return 0
    db = get_db()  # get_db explicitly refuses protected database names.
    changed = 0
    for row in pd.read_csv(path, usecols=lambda c: c in {title_column, "url", "is_paid"}).to_dict("records"):
        if "is_paid" not in row:
            continue
        title = str(row.get(title_column) or "").strip()
        url = str(row.get("url") or "").strip()
        if not title:
            continue
        query = {"title": title}
        if url and url.lower() != "nan":
            query["url"] = url
        result = db.courses.update_many(query, {"$set": {"is_paid": parse_is_paid(row["is_paid"])}})
        changed += result.modified_count
    return changed


if __name__ == "__main__":
    raw = settings.DATA_RAW_DIR
    count = repair_file(raw / "Data3" / "udemy_courses.csv", "title")
    count += repair_file(raw / "Data4" / "udemy_courses.csv", "course_title")
    print(f"Updated {count:,} course access flags in switchback.courses.")
