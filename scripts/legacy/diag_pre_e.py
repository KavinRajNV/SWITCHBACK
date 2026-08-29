"""
DIAGNOSTIC — Part D + Pre-E
Examine jobs collection structure and YouTube Excel mismatch.
Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\diag_pre_e.py
"""
import sys
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

# ─── PART D: YouTube Excel mismatch ─────────────────────────────────────────
print("=" * 70)
print("PART D: YouTube cache entries for Microsoft Excel")
print("=" * 70)
excel_cache = db.youtube_cache.find_one({"skill_key": "microsoft excel"})
if excel_cache:
    print(f"Cached videos: {len(excel_cache.get('videos', []))}")
    for v in excel_cache.get("videos", []):
        print(f"  [{v.get('channel_title','?')}] {v.get('title','?')[:70]}")
        print(f"    url: {v.get('url','')}")
else:
    print("  No cache entry for 'microsoft excel'")

print()
print("Channel ID cache:")
ch_cache = db.youtube_cache.find_one({"cache_type": "channel_id_lookup_cache"})
if ch_cache:
    data = ch_cache.get("data", {})
    print(f"  Resolved {len(data)} channel names -> IDs")
    for name, cid in list(data.items())[:10]:
        print(f"    {name:<40} -> {cid}")
else:
    print("  No channel ID cache found")

print()
print("All youtube_cache entries:")
for doc in db.youtube_cache.find({}, {"skill_key": 1, "cache_type": 1, "skill": 1}):
    doc.pop("_id", None)
    print(f"  {doc}")

# ─── PRE-E: jobs collection structure ────────────────────────────────────────
print()
print("=" * 70)
print("PRE-E: jobs collection structure")
print("=" * 70)
total_jobs = db.jobs.count_documents({})
primary_jobs = db.jobs.count_documents({"source_quality": "primary"})
print(f"Total jobs: {total_jobs}")
print(f"Primary quality jobs: {primary_jobs}")

sample = db.jobs.find_one({"source_quality": "primary"})
if sample:
    sample.pop("_id", None)
    print(f"\nSample primary job keys: {list(sample.keys())}")
    print(f"  job_title: {sample.get('job_title')}")
    print(f"  skills_matched: {sample.get('skills_matched', [])[:10]}")
    print(f"  salary_lpa: {sample.get('salary_lpa')}")
    print(f"  min_salary_lpa: {sample.get('min_salary_lpa')}")
    print(f"  max_salary_lpa: {sample.get('max_salary_lpa')}")
    print(f"  source_quality: {sample.get('source_quality')}")
    print(f"  experience_min: {sample.get('experience_min')}")
    print(f"  company: {sample.get('company')}")

print()
# Count distinct job_title values
total_distinct = len(db.jobs.distinct("job_title", {"source_quality": "primary"}))
print(f"Distinct job_title values (primary only): {total_distinct}")

# Show top 30 most frequent job titles
print("\nTop 30 job titles by frequency:")
pipeline = [
    {"$match": {"source_quality": "primary"}},
    {"$group": {"_id": "$job_title", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 30},
]
for doc in db.jobs.aggregate(pipeline):
    print(f"  {doc['count']:>5}  {doc['_id']}")

# ─── Check salary fields ──────────────────────────────────────────────────────
print()
print("Salary field coverage (primary jobs):")
has_salary_lpa = db.jobs.count_documents({"source_quality": "primary", "salary_lpa": {"$exists": True, "$ne": None}})
has_min = db.jobs.count_documents({"source_quality": "primary", "min_salary_lpa": {"$exists": True, "$ne": None}})
has_max = db.jobs.count_documents({"source_quality": "primary", "max_salary_lpa": {"$exists": True, "$ne": None}})
print(f"  salary_lpa present: {has_salary_lpa}")
print(f"  min_salary_lpa present: {has_min}")
print(f"  max_salary_lpa present: {has_max}")

print()
print("DIAGNOSTIC COMPLETE")
