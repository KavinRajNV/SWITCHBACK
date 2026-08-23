from pathlib import Path
from typing import Dict, Any
import pandas as pd
from pymongo.database import Database
from pymongo import ASCENDING

from app.config import settings

def load_esco_datasets(db: Database) -> Dict[str, Any]:
    """
    Loads specified ESCO CSV files into MongoDB collections prefixed with 'esco_'.
    """
    esco_dir = settings.DATA_RAW_DIR / "Data8"
    if not esco_dir.exists():
        print(f"[ESCO Loader Warning] ESCO directory not found at: {esco_dir}")
        return {"loaded_collections": {}, "total_records": 0}

    esco_mapping = {
        "skills_en.csv": ("esco_skills", ["conceptUri"]),
        "occupations_en.csv": ("esco_occupations", ["conceptUri"]),
        "occupationSkillRelations_en.csv": ("esco_occupation_skill_relations", ["occupationUri", "skillUri"]),
        "skillsHierarchy_en.csv": ("esco_skills_hierarchy", ["Level 0 URI"]),
        "skillSkillRelations_en.csv": ("esco_skill_skill_relations", ["originalSkillUri", "relatedSkillUri"])
    }

    stats: Dict[str, Any] = {
        "loaded_collections": {},
        "total_records": 0
    }

    for csv_name, (coll_name, index_fields) in esco_mapping.items():
        file_path = esco_dir / csv_name
        if not file_path.exists():
            print(f"[ESCO Loader Warning] File not found: {file_path}")
            continue

        print(f"[ESCO Loader] Reading {csv_name} -> Collection '{coll_name}'...")
        df = pd.read_csv(file_path)
        records = df.to_dict(orient="records")
        for r in records:
            r.pop("_id", None)
            
        coll = db[coll_name]
        coll.delete_many({})
        
        if records:
            chunk_size = 5000
            for i in range(0, len(records), chunk_size):
                chunk = [dict(r) for r in records[i : i + chunk_size]]
                for r in chunk:
                    r.pop("_id", None)
                coll.insert_many(chunk)
                
            for field in index_fields:
                if field in df.columns:
                    coll.create_index([(field, ASCENDING)])

        count = len(records)
        stats["loaded_collections"][coll_name] = count
        stats["total_records"] += count
        print(f"[ESCO Loader] Loaded {count} records into '{coll_name}'.")

    return stats
