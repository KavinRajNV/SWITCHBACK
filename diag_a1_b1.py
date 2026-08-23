"""
DIAGNOSTIC SCRIPT — Part A1, B1, C1
Run: $env:PYTHONIOENCODING='utf-8'; python diag_a1_b1.py
"""
import sys
import os
sys.path.insert(0, r'd:\switchback\backend')
os.chdir(r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')

from app.db.mongo_client import get_db
db = get_db()

# ─── PART A1: Course coverage counts ───────────────────────────────────────────
print("=" * 70)
print("PART A1: courses.skills_matched coverage for key milestone skills")
print("=" * 70)

test_skills = [
    "Apache Spark", "C#", "Groovy", "Software Development",
    "Data Analysis", "Microsoft Excel", "C++", "COBOL",
    "Python", "SQL", "Machine Learning", "AWS",
    "JavaScript", "Java", "React", "Node.js",
    "Scikit-learn", "MongoDB", "Git", "FastAPI",
    "Vector Databases", "LLMs", "RAG",
]

for skill in test_skills:
    count = db.courses.count_documents({"skills_matched": skill})
    print(f"  {skill:<30} -> {count:>4} courses")

print()

# ─── A1b: Sample courses for a "bad" skill to check content ───────────────────
print("=" * 70)
print("A1b: Sample course titles for C# (should be C# programming courses)")
print("=" * 70)
sample_csharp = list(db.courses.find(
    {"skills_matched": "C#"},
    {"title": 1, "source": 1, "skills_matched": 1, "rating": 1}
).sort("rating", -1).limit(10))
for c in sample_csharp:
    print(f"  [{c.get('source','?')}] {c.get('title','?')[:80]}  skills={c.get('skills_matched',[])[:5]}")

print()
print("=" * 70)
print("A1c: Sample course titles for Apache Spark")
print("=" * 70)
sample_spark = list(db.courses.find(
    {"skills_matched": "Apache Spark"},
    {"title": 1, "source": 1, "skills_matched": 1, "rating": 1}
).sort("rating", -1).limit(10))
for c in sample_spark:
    print(f"  [{c.get('source','?')}] {c.get('title','?')[:80]}  skills={c.get('skills_matched',[])[:5]}")

print()
print("=" * 70)
print("A1d: Sample course titles for Groovy")
print("=" * 70)
sample_groovy = list(db.courses.find(
    {"skills_matched": "Groovy"},
    {"title": 1, "source": 1, "skills_matched": 1, "rating": 1}
).sort("rating", -1).limit(10))
for c in sample_groovy:
    print(f"  [{c.get('source','?')}] {c.get('title','?')[:80]}  skills={c.get('skills_matched',[])[:5]}")

print()
print("=" * 70)
print("A1e: Total courses in DB; skills_matched field structure sample")
print("=" * 70)
total = db.courses.count_documents({})
print(f"  Total courses: {total}")
sample_any = db.courses.find_one({})
if sample_any:
    sample_any.pop("_id", None)
    print(f"  Sample doc keys: {list(sample_any.keys())}")
    print(f"  skills_matched value: {sample_any.get('skills_matched')}")
    print(f"  is_paid: {sample_any.get('is_paid')}, price: {sample_any.get('price')}")
    print(f"  rating: {sample_any.get('rating')}")

print()
print("=" * 70)
print("A1f: How many courses have NO skills_matched or empty skills_matched")
print("=" * 70)
no_skills = db.courses.count_documents({"skills_matched": {"$in": [None, [], ""]}})
missing = db.courses.count_documents({"skills_matched": {"$exists": False}})
print(f"  Empty/null skills_matched: {no_skills}")
print(f"  Missing skills_matched field: {missing}")

# ─── PART B1: Canonicalization check ──────────────────────────────────────────
print()
print("=" * 70)
print("PART B1: Role recommendation diagnosis")
print("=" * 70)

test_resume_skills = [
    "Python", "Java", "JavaScript", "AWS", "Scikit-learn",
    "Machine Learning", "MongoDB", "SQL", "React", "Node.js",
    "Express.js", "FastAPI", "Git",
]
print(f"Test resume skills (canonical names): {test_resume_skills}")
print()

def print_occupation_diagnosis(title):
    occ = db.occupations_enriched.find_one({"title": title})
    if not occ:
        print(f"  '{title}': NOT FOUND IN DB")
        return
    crs = occ.get("combined_required_skills", [])
    intersection = set(s.lower() for s in test_resume_skills) & set(s.lower() for s in crs)
    print(f"  '{title}':")
    print(f"    combined_required_skills ({len(crs)}): {crs[:15]}")
    print(f"    Intersection with test skills: {sorted(intersection)}")
    print(f"    Jaccard (approx): {len(intersection)}/{len(set(s.lower() for s in test_resume_skills) | set(s.lower() for s in crs)):.4f}")

for title in ["Data Scientists", "Software Developers", "Robotics Technicians",
              "Transportation Engineers", "Materials Scientists",
              "Web Developers", "Information Security Analysts"]:
    print_occupation_diagnosis(title)
    print()

# Check if combined_required_skills uses exact same case as canonical skill names
print("=" * 70)
print("B1b: Case/name alignment check for key skills")
print("=" * 70)
for skill in ["Python", "Machine Learning", "Scikit-learn", "Vector Databases", "RAG", "LLMs"]:
    # How many occupations have this skill (exact match)?
    exact = db.occupations_enriched.count_documents({"combined_required_skills": skill})
    # Case-insensitive?
    ci = db.occupations_enriched.count_documents({"combined_required_skills": {"$regex": f"^{skill}$", "$options": "i"}})
    print(f"  '{skill}': exact_match={exact}, case_insensitive={ci}")

print()
print("=" * 70)
print("B1c: What combined_required_skills values look like for Data Scientists")
print("=" * 70)
ds = db.occupations_enriched.find_one({"title": "Data Scientists"})
if ds:
    print(f"  {ds.get('combined_required_skills', [])}")

print()
print("=" * 70)
print("C1: Current youtube_service.py summary")
print("=" * 70)
yt_cache_count = db.youtube_cache.count_documents({})
print(f"  youtube_cache collection count: {yt_cache_count}")
yt_sample = db.youtube_cache.find_one({"skill_key": {"$exists": True}})
if yt_sample:
    yt_sample.pop("_id", None)
    print(f"  Sample cached entry: skill={yt_sample.get('skill')}, videos_count={len(yt_sample.get('videos',[]))}")
    if yt_sample.get("videos"):
        print(f"  First video: {yt_sample['videos'][0].get('url')}")

allowlist_count = db.youtube_allowlist.count_documents({})
print(f"  youtube_allowlist count: {allowlist_count}")
# Check if any channel_id fields were added by previous round
has_id = db.youtube_allowlist.count_documents({"channel_id": {"$exists": True}})
print(f"  youtube_allowlist docs with channel_id: {has_id}")

print()
print("DIAGNOSTIC COMPLETE")
