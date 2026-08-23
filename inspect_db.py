import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'd:\switchback\backend')
os.chdir(r'd:\switchback\backend')

from app.db.mongo_client import get_db
db = get_db()

# Check youtube_allowlist structure
print("=== youtube_allowlist sample doc ===")
doc = db.youtube_allowlist.find_one({})
if doc:
    doc.pop("_id", None)
    print(doc)
else:
    print("EMPTY - no documents in youtube_allowlist!")
print()

# Count allowlist
count = db.youtube_allowlist.count_documents({})
print(f"youtube_allowlist count: {count}")
print()

# Check combined_required_skills for Data Scientists  
print("=== Data Scientists combined_required_skills ===")
occ = db.occupations_enriched.find_one({"title": "Data Scientists"})
if occ:
    crs = occ.get("combined_required_skills", [])
    print(f"count: {len(crs)}, sample: {crs[:15]}")
else:
    print("NOT FOUND")
print()

# Sample occupations with combined_required_skills
print("=== Sample occupations with combined_required_skills ===")
sample = list(db.occupations_enriched.find({"combined_required_skills": {"$exists": True, "$ne": []}}).limit(5))
for s in sample:
    crs = s.get("combined_required_skills", [])
    print(f"  {s.get('title')}: {crs[:5]}")

# Total count with non-empty combined_required_skills
no_skills = db.occupations_enriched.count_documents({"combined_required_skills": {"$exists": True, "$ne": []}})
total = db.occupations_enriched.count_documents({})
print(f"\nTotal: {total}, With non-empty combined_required_skills: {no_skills}")
