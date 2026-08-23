import csv
import shutil
from pathlib import Path
from typing import Dict, Any
from pymongo.database import Database

from app.config import settings

def load_curated_datasets(db: Database) -> Dict[str, Any]:
    """
    Loads skill vocabulary seed list into Mongo collection 'skill_vocabulary',
    YouTube channel allowlist into 'youtube_allowlist',
    and copies sample_resumes_for_parser_testing.txt to data/processed/.
    """
    curated_dir = settings.DATA_RAW_DIR / "curated_data"
    vocab_path = curated_dir / "skill_vocabulary_seed_list.csv"
    youtube_path = curated_dir / "youtube_channel_allowlist.csv"
    resume_fixture_path = curated_dir / "sample_resumes_for_parser_testing.txt"

    stats: Dict[str, Any] = {
        "vocabulary_count": 0,
        "youtube_channels_count": 0,
        "resume_fixture_copied": False
    }

    # 1. Skill Vocabulary Seed List -> 'skill_vocabulary'
    if vocab_path.exists():
        vocab_records = []
        with open(vocab_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vocab_records.append(row)

        coll_vocab = db["skill_vocabulary"]
        coll_vocab.delete_many({})
        if vocab_records:
            coll_vocab.insert_many(vocab_records)
            coll_vocab.create_index("canonical_skill", unique=True)
            coll_vocab.create_index("category")
        stats["vocabulary_count"] = len(vocab_records)
        print(f"[Curated Loader] Loaded {len(vocab_records)} vocabulary rows into 'skill_vocabulary'.")

    # 2. YouTube Allowlist -> 'youtube_allowlist'
    if youtube_path.exists():
        yt_records = []
        with open(youtube_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yt_records.append(row)

        coll_yt = db["youtube_allowlist"]
        coll_yt.delete_many({})
        if yt_records:
            coll_yt.insert_many(yt_records)
        stats["youtube_channels_count"] = len(yt_records)
        print(f"[Curated Loader] Loaded {len(yt_records)} YouTube allowlist rows into 'youtube_allowlist'.")

    # 3. Copy sample_resumes_for_parser_testing.txt to data/processed/
    if resume_fixture_path.exists():
        dest_path = settings.DATA_PROCESSED_DIR / "sample_resumes_for_parser_testing.txt"
        shutil.copy2(resume_fixture_path, dest_path)
        stats["resume_fixture_copied"] = True
        print(f"[Curated Loader] Copied sample resumes fixture to {dest_path}.")

    return stats
