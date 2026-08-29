"""
Final targeted fixes for Apache Spark and Go filters.
Apache Spark: need to require "apache spark" or "pyspark" or "databricks" — 
just "spark" is too generic.
Go: The "From Developer to Entrepreneur" result has "Golang" in headline — check.
"""
import sys, re
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

# ─── APACHE SPARK: tighter filter ─────────────────────────────────────────────
print("=== Apache Spark tighter filter ===")
SPARK_PATTERNS = [
    r"apache spark", r"pyspark", r"databricks",
    r"spark.*streaming", r"spark.*sql", r"spark.*data",
    r"sparkr", r"sparkling water",
    r"rdd\b", r"hadoop.*spark", r"spark.*hadoop",
    r"big data.*spark", r"spark.*big data",
    r"structured streaming",
]

current = db.courses.count_documents({"skills_matched": "Apache Spark"})
print(f"  Current Apache Spark count: {current}")

bad_spark = []
samples = []
for doc in db.courses.find({"skills_matched": "Apache Spark"}, {"_id": 1, "title": 1, "headline": 1}):
    combined = ((doc.get("title") or "") + " " + (doc.get("headline") or "")).lower()
    if not any(re.search(p, combined, re.IGNORECASE) for p in SPARK_PATTERNS):
        bad_spark.append(doc["_id"])
        if len(samples) < 5:
            samples.append(doc.get("title", "")[:70])

print(f"  Spurious with tighter filter: {len(bad_spark)}")
for s in samples:
    print(f"    BAD: [{s}]")

if bad_spark:
    for i in range(0, len(bad_spark), 500):
        db.courses.update_many({"_id": {"$in": bad_spark[i:i+500]}}, {"$pull": {"skills_matched": "Apache Spark"}})

final_spark = db.courses.count_documents({"skills_matched": "Apache Spark"})
print(f"  Final Apache Spark count: {final_spark}")

print("\nApache Spark sample:")
for c in db.courses.find({"skills_matched": "Apache Spark"}, {"title": 1}).sort("rating", -1).limit(8):
    print(f"  {c.get('title','')[:70]}")

# ─── GO: check the "entrepreneur" result ───────────────────────────────────────
print("\n=== Go check ===")
doc = db.courses.find_one({"title": {"$regex": "entrepreneur.*case", "$options": "i"}})
if doc:
    print(f"  Title: {doc.get('title')}")
    print(f"  Headline: {(doc.get('headline') or '')[:100]}")
    print(f"  skills_matched: {doc.get('skills_matched')}")
    # Check if 'golang' or 'go' appears
    combined = ((doc.get("title") or "") + " " + (doc.get("headline") or "")).lower()
    go_word_pat = re.compile(r'\bgo\b')
    print(f"  'golang' in combined: {'golang' in combined}")
    print(f"  'go' as word: {bool(go_word_pat.search(combined))}")


# ─── FINAL SUMMARY ─────────────────────────────────────────────────────────────
print("\n=== Final course counts for all fixed skills ===")
for skill in ["Apache Spark", "C#", "Groovy", "Go", "R", "C", "F#", "Rust", "Julia"]:
    count = db.courses.count_documents({"skills_matched": skill})
    print(f"  {skill:<30} -> {count:>4}")

print("\nDone.")
