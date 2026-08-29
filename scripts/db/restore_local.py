"""Restore `data/mongo_snapshot/` into a MongoDB instance using only pymongo —
no `mongorestore` binary required.

    python scripts/db/restore_local.py                       # -> mongodb://localhost:27017
    python scripts/db/restore_local.py mongodb://host:27017

Use this if you have a local `mongod` running but not the MongoDB Database Tools.
`docker compose up` does the same thing with `mongorestore` inside the container.
"""
import sys
from pathlib import Path

import bson
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
SNAP = ROOT / "data" / "mongo_snapshot"


def main() -> None:
    uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb://localhost:27017"
    dbs = [p for p in SNAP.iterdir() if p.is_dir()] if SNAP.exists() else []
    if not dbs:
        print(f"No snapshot under {SNAP}. Run scripts/db/dump_switchback.py first.", file=sys.stderr)
        sys.exit(1)

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")

    for db_dir in dbs:
        db = client[db_dir.name]
        for bson_file in sorted(db_dir.glob("*.bson")):
            coll_name = bson_file.stem
            docs = list(bson.decode_file_iter(bson_file.open("rb")))
            db[coll_name].drop()
            if docs:
                db[coll_name].insert_many(docs, ordered=False)
            print(f"  {db_dir.name}.{coll_name:28s} {len(docs):>8,d} docs")

    print("Restore complete.")


if __name__ == "__main__":
    main()
