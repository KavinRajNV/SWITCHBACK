"""Diagnose skills in jobs collection for specific roles."""
import sys, re
from collections import Counter
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

def normalize_title(raw):
    if not raw: return ""
    t = raw.lower().strip()
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\s*[-|/].*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

# Spot check Full Stack Developer jobs
print("=== Full Stack Developer job skill samples ===")
fsd_jobs = list(db.jobs.find(
    {"source_quality": "primary", "job_title": {"$regex": "full.?stack", "$options": "i"}},
    {"job_title": 1, "skills_raw": 1, "skills_matched": 1}
).limit(10))
skill_counter = Counter()
for j in fsd_jobs:
    print(f"  [{j.get('job_title','?')[:60]}]")
    print(f"    skills_raw: {j.get('skills_raw','')[:100] if j.get('skills_raw') else 'None'}")
    print(f"    skills_matched: {j.get('skills_matched', [])}")
    for sk in (j.get('skills_matched') or []):
        skill_counter[sk] += 1
    print()
print(f"Top skills across all FSD jobs: {skill_counter.most_common(10)}")

print()
print("=== Count of Full Stack Developer jobs ===")
count = db.jobs.count_documents({"source_quality": "primary", "job_title": {"$regex": "full.?stack", "$options": "i"}})
print(f"  Total: {count}")

print()
print("=== Sample jobs with skills_raw vs skills_matched ===")
# Check coverage of skills_raw field
has_raw = db.jobs.count_documents({"source_quality": "primary", "skills_raw": {"$exists": True, "$ne": None, "$ne": ""}})
has_matched = db.jobs.count_documents({"source_quality": "primary", "skills_matched": {"$exists": True, "$ne": [], "$ne": None}})
total_primary = db.jobs.count_documents({"source_quality": "primary"})
print(f"  Total primary: {total_primary}")
print(f"  Has skills_raw (non-null): {has_raw}")
print(f"  Has skills_matched (non-empty): {has_matched}")

# Sample the skills_raw for full stack jobs to see raw content
sample = db.jobs.find_one({"source_quality": "primary", "job_title": {"$regex": "full.?stack", "$options": "i"}, "skills_raw": {"$ne": None}})
if sample:
    print(f"\n  Sample full-stack job with skills_raw:")
    print(f"    title: {sample.get('job_title')}")
    print(f"    skills_raw: {sample.get('skills_raw')}")
    print(f"    skills_matched: {sample.get('skills_matched')}")
