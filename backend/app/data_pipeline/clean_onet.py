from pathlib import Path
from typing import Dict, Any
import pandas as pd
from pymongo.database import Database
from pymongo import ASCENDING

from app.config import settings

def load_onet_datasets(db: Database) -> Dict[str, Any]:
    """
    Loads specified O*NET CSV files into MongoDB collections prefixed with 'onet_'.
    """
    onet_dir = settings.DATA_RAW_DIR / "Data7" / "db_30_3_csv"
    if not onet_dir.exists():
        print(f"[O*NET Loader Warning] O*NET directory not found at: {onet_dir}")
        return {"loaded_collections": {}, "total_records": 0}

    onet_mapping = {
        "occupation_data.csv": "onet_occupations",
        "software_skills.csv": "onet_software_skills",
        "essential_skills.csv": "onet_essential_skills",
        "knowledge.csv": "onet_knowledge",
        "job_titles.csv": "onet_job_titles",
        "job_zones.csv": "onet_job_zones",
        "related_occupations.csv": "onet_related_occupations",
    }

    stats: Dict[str, Any] = {
        "loaded_collections": {},
        "total_records": 0
    }

    for csv_name, coll_name in onet_mapping.items():
        file_path = onet_dir / csv_name
        if not file_path.exists():
            print(f"[O*NET Loader Warning] File not found: {file_path}")
            continue

        print(f"[O*NET Loader] Reading {csv_name} -> Collection '{coll_name}'...")
        df = pd.read_csv(file_path)
        records = df.to_dict(orient="records")
        # Strip any transient _id fields attached by PyMongo in previous runs
        for r in records:
            r.pop("_id", None)
        
        coll = db[coll_name]
        coll.delete_many({})
        
        if records:
            chunk_size = 5000
            for i in range(0, len(records), chunk_size):
                chunk = [dict(r) for r in records[i : i + chunk_size]]
                coll.insert_many(chunk)
                
            # Create index on 'O*NET-SOC Code' if column exists
            if "O*NET-SOC Code" in df.columns:
                coll.create_index([("O*NET-SOC Code", ASCENDING)])

        count = len(records)
        stats["loaded_collections"][coll_name] = count
        stats["total_records"] += count
        print(f"[O*NET Loader] Loaded {count} records into '{coll_name}'.")

    return stats
