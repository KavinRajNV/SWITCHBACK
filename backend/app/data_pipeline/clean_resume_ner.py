import json
from pathlib import Path
from typing import Dict, Any
from pymongo.database import Database

from app.config import settings

def load_resume_ner_dataset(db: Database) -> Dict[str, Any]:
    """
    Parses 'Entity Recognition in Resumes.json' line-by-line as JSONL
    and loads records into MongoDB collection 'resume_ner_training' tagged with split: 'validation'.
    """
    jsonl_path = settings.DATA_RAW_DIR / "Data6" / "Entity Recognition in Resumes.json"
    if not jsonl_path.exists():
        print(f"[Resume NER Loader Warning] File not found: {jsonl_path}")
        return {"records_loaded": 0}

    print(f"[Resume NER Loader] Parsing line-by-line JSONL from {jsonl_path.name}...")
    records = []
    with open(jsonl_path, mode="r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                obj = json.loads(line_str)
                obj["split"] = "validation"
                records.append(obj)

    collection = db["resume_ner_training"]
    collection.delete_many({})
    
    if records:
        collection.insert_many(records)

    count = len(records)
    print(f"[Resume NER Loader] Loaded {count} resume NER validation records into 'resume_ner_training'.")
    return {"records_loaded": count}
