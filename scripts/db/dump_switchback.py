"""Export the runtime slice of the `switchback` MongoDB database to a
`mongorestore`-compatible snapshot committed under `data/mongo_snapshot/`.

Only the collections actually queried while serving requests are exported, so
the app runs fully offline from the snapshot with no Atlas credentials. Run this
whenever the source data changes:

    python scripts/db/dump_switchback.py            # uses MONGODB_URI from .env

The output is plain concatenated-BSON (`<coll>.bson` + `<coll>.metadata.json`),
the same layout `mongodump` writes, so `scripts/db/restore_local.*` (or
`docker compose up`) can load it with `mongorestore`.
"""
import json
import sys
from pathlib import Path

import bson
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import settings  # noqa: E402

# Collections read on the request path (see backend/app/api/*). Everything else
# in `switchback` is build-time only (pipeline / training) and is intentionally
# left out to keep the committed snapshot small.
RUNTIME_COLLECTIONS = [
    "occupations_enriched",
    "market_roles",
    "courses",
    "skill_vocabulary",
    "onet_related_occupations",
    "youtube_allowlist",
]

OUT_DIR = ROOT / "data" / "mongo_snapshot" / settings.MONGO_DB_NAME


def main() -> None:
    uri = settings.MONGODB_URI
    if not uri or uri.startswith("mongodb://localhost"):
        print("Set MONGODB_URI (Atlas) in .env before dumping.", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[settings.MONGO_DB_NAME]

    total_bytes = 0
    for name in RUNTIME_COLLECTIONS:
        coll = db[name]
        bson_path = OUT_DIR / f"{name}.bson"
        n = 0
        with open(bson_path, "wb") as fh:
            for doc in coll.find({}):
                fh.write(bson.encode(doc))
                n += 1
        size = bson_path.stat().st_size
        total_bytes += size
        (OUT_DIR / f"{name}.metadata.json").write_text(
            json.dumps({"options": {}, "indexes": [], "collectionName": name}, indent=2)
        )
        print(f"  {name:28s} {n:>8,d} docs  {size/1_048_576:8.2f} MB")

    print(f"\nSnapshot written to {OUT_DIR}  (total {total_bytes/1_048_576:.1f} MB)")


if __name__ == "__main__":
    main()
