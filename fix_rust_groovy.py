"""
Fix Rust filter false negatives — restore legitimate Rust courses.
Also fix Groovy to restore legitimate courses.
"""
import sys, re
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

def restore_and_refilter(skill, title_patterns, body_patterns, description):
    """
    1. Find docs with skill in title (by title_patterns) but NOT tagged with skill.
    2. Restore the tag.
    3. Re-apply corrected body_patterns filter to drop genuinely irrelevant ones.
    """
    print(f"\n--- {skill} ({description}) ---")
    
    # Step 1: Restore by title match
    total_restored = 0
    for tp in title_patterns:
        cursor = db.courses.find(
            {"title": {"$regex": tp, "$options": "i"}, "skills_matched": {"$ne": skill}},
            {"_id": 1, "title": 1}
        )
        ids = [d["_id"] for d in cursor]
        if ids:
            db.courses.update_many({"_id": {"$in": ids}}, {"$addToSet": {"skills_matched": skill}})
            total_restored += len(ids)
    print(f"  Restored tag to {total_restored} courses by title match")

    # Step 2: Re-apply corrected body filter
    current_count = db.courses.count_documents({"skills_matched": skill})
    print(f"  Current tagged count: {current_count}")
    
    bad_ids = []
    samples = []
    for doc in db.courses.find({"skills_matched": skill}, {"_id": 1, "title": 1, "headline": 1}):
        combined = ((doc.get("title") or "") + " " + (doc.get("headline") or "")).lower()
        if not any(re.search(p, combined, re.IGNORECASE) for p in body_patterns):
            bad_ids.append(doc["_id"])
            if len(samples) < 3:
                samples.append(doc.get("title","")[:70])
    
    print(f"  Still spurious: {len(bad_ids)}")
    for s in samples:
        print(f"    BAD: [{s}]")
    
    if bad_ids:
        for i in range(0, len(bad_ids), 500):
            db.courses.update_many(
                {"_id": {"$in": bad_ids[i:i+500]}},
                {"$pull": {"skills_matched": skill}}
            )
    final = db.courses.count_documents({"skills_matched": skill})
    print(f"  Final {skill} count: {final}")

# ─── RUST ──────────────────────────────────────────────────────────────────────
restore_and_refilter(
    skill="Rust",
    title_patterns=[r"rust"],
    body_patterns=[
        r"\brust\b", r"rustlang", r"cargo.*crate", r"systems programming.*rust",
    ],
    description="Rust programming language"
)

# ─── GROOVY ────────────────────────────────────────────────────────────────────
restore_and_refilter(
    skill="Groovy",
    title_patterns=[r"groovy"],
    body_patterns=[
        r"\bgroovy\b", r"\bgradle\b", r"\bgrails\b", r"\bspock\b",
        r"jenkinsfile", r"jenkins.*pipeline",
    ],
    description="Groovy JVM language"
)

# ─── GO ────────────────────────────────────────────────────────────────────────
# Go has many edge cases - let's check what's in there now
go_sample = list(db.courses.find({"skills_matched": "Go"}, {"title": 1}).sort("rating", -1).limit(10))
print("\n--- Go sample (after previous fix) ---")
for c in go_sample:
    print(f"  {c.get('title','?')[:70]}")

# ─── APACHE SPARK ──────────────────────────────────────────────────────────────
# Check if 'Apache Spark' courses now look OK
print("\n--- Apache Spark sample (after fix) ---")
spark_sample = list(db.courses.find({"skills_matched": "Apache Spark"}, {"title": 1}).sort("rating", -1).limit(10))
for c in spark_sample:
    print(f"  {c.get('title','?')[:70]}")

print("\nDone.")
