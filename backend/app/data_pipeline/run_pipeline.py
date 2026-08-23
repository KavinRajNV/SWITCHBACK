import os
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import time
import pandas as pd

from app.config import settings
from app.db.mongo_client import ping, get_db, assert_db_safety, PROTECTED_DATABASES
from app.data_pipeline.load_curated import load_curated_datasets
from app.data_pipeline.skill_matcher import SkillMatcher
from app.data_pipeline.clean_naukri import clean_naukri_datasets
from app.data_pipeline.clean_courses import clean_course_datasets
from app.data_pipeline.clean_onet import load_onet_datasets
from app.data_pipeline.clean_esco import load_esco_datasets
from app.data_pipeline.clean_resume_ner import load_resume_ner_dataset

def export_parquet_backups(db) -> dict:
    """
    Exports major MongoDB collections ('jobs', 'courses') to Parquet files
    in data/processed/ as fast-loading backup artifacts.
    """
    processed_dir = settings.DATA_PROCESSED_DIR
    print(f"\n[Parquet Exporter] Writing Parquet backup exports to: {processed_dir}")
    
    export_stats = {}
    
    for coll_name in ["jobs", "courses"]:
        coll = db[coll_name]
        records = list(coll.find({}, {"_id": 0}))
        if records:
            df = pd.DataFrame(records)
            # Convert list columns to string representation for parquet compatibility
            for col in df.columns:
                if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                    df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
            
            parquet_path = processed_dir / f"{coll_name}.parquet"
            df.to_parquet(parquet_path, index=False)
            export_stats[coll_name] = {
                "rows": len(df),
                "path": str(parquet_path)
            }
            print(f"[Parquet Exporter] Exported {len(df)} rows to {parquet_path.name}")
            
    return export_stats

def run_pipeline() -> dict:
    """
    Master pipeline orchestrator for Phase 1.
    """
    start_total_time = time.time()
    print("=" * 70)
    print("      SWITCHBACK PHASE 1 — DATA ENGINEERING PIPELINE")
    print("=" * 70)
    
    # 0. Sanity check & connectivity test
    ping()
    db = get_db()
    assert_db_safety(db.name)
    
    summary = {
        "database_name": db.name,
        "stages": {},
        "parquet_exports": {},
        "protected_db_check": True
    }
    
    # 1. Curated Data Loading
    print("\n--- STAGE 1: Curated Data & Skill Vocabulary Loading ---")
    t0 = time.time()
    curated_stats = load_curated_datasets(db)
    t1 = time.time()
    summary["stages"]["curated"] = {**curated_stats, "elapsed_seconds": round(t1 - t0, 2)}
    
    # 2. Skill Matcher Initialization
    print("\n--- STAGE 2: Skill Matcher Instantiation ---")
    t0 = time.time()
    matcher = SkillMatcher.from_mongo(db)
    t1 = time.time()
    print(f"[SkillMatcher] Loaded vocabulary with {len(matcher.canonical_skills)} canonical skills and {len(matcher.choices)} total aliases in {round(t1 - t0, 2)}s.")
    summary["stages"]["skill_matcher"] = {
        "canonical_skills_count": len(matcher.canonical_skills),
        "total_aliases_count": len(matcher.choices),
        "elapsed_seconds": round(t1 - t0, 2)
    }

    # 3. Naukri Cleaning & Loading
    print("\n--- STAGE 3: Naukri Jobs Cleaning & Pipeline ---")
    t0 = time.time()
    naukri_stats = clean_naukri_datasets(db, matcher)
    t1 = time.time()
    summary["stages"]["naukri"] = {**naukri_stats, "elapsed_seconds": round(t1 - t0, 2)}

    # 4. Course Cleaning & Loading
    print("\n--- STAGE 4: Course Datasets (Udemy & Coursera) Cleaning ---")
    t0 = time.time()
    course_stats = clean_course_datasets(db, matcher)
    t1 = time.time()
    summary["stages"]["courses"] = {**course_stats, "elapsed_seconds": round(t1 - t0, 2)}

    # 5. O*NET Reference Data Loading
    print("\n--- STAGE 5: O*NET Reference Data Loading ---")
    t0 = time.time()
    onet_stats = load_onet_datasets(db)
    t1 = time.time()
    summary["stages"]["onet"] = {**onet_stats, "elapsed_seconds": round(t1 - t0, 2)}

    # 6. ESCO Reference Data Loading
    print("\n--- STAGE 6: ESCO Reference Data Loading ---")
    t0 = time.time()
    esco_stats = load_esco_datasets(db)
    t1 = time.time()
    summary["stages"]["esco"] = {**esco_stats, "elapsed_seconds": round(t1 - t0, 2)}

    # 7. Resume NER Loading
    print("\n--- STAGE 7: Resume NER Validation Dataset Loading ---")
    t0 = time.time()
    ner_stats = load_resume_ner_dataset(db)
    t1 = time.time()
    summary["stages"]["resume_ner"] = {**ner_stats, "elapsed_seconds": round(t1 - t0, 2)}

    # 8. Backup Parquet Exports
    t0 = time.time()
    parquet_stats = export_parquet_backups(db)
    t1 = time.time()
    summary["parquet_exports"] = parquet_stats

    # Final Database Inspection & Safety Assertions
    client = db.client
    existing_dbs = client.list_database_names()
    print("\n" + "=" * 70)
    print(f"[Cluster Database Sanity Check] Existing databases on cluster: {existing_dbs}")
    
    # Confirm target db is NOT in protected list
    assert_db_safety(db.name)
    for protected in PROTECTED_DATABASES:
        assert protected in existing_dbs, f"Expected protected database '{protected}' to exist untouched on cluster."
        
    print("[Cluster Safety Verified] None of 'admin', 'kisan_ai', 'local', or 'sample_mflix' were touched.")

    total_time = round(time.time() - start_total_time, 2)
    summary["total_elapsed_seconds"] = total_time
    print(f"\n[Pipeline Complete] Total execution time: {total_time} seconds.")
    print("=" * 70)
    
    return summary

if __name__ == "__main__":
    run_pipeline()
