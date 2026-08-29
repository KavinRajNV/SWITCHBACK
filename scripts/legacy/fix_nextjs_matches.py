import sys
from pathlib import Path
from pymongo import UpdateOne

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.data_pipeline.skill_matcher import SkillMatcher

def fix_nextjs_matches():
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)
    
    print("[Next.js Cleanup] Cleaning false-positive Next.js course matches via bulk write...")
    courses = list(db.courses.find({"skills_matched": "Next.js"}, {"_id": 1, "title": 1, "category": 1}))
    print(f"[Next.js Cleanup] Found {len(courses)} courses tagged with Next.js")
    
    ops = []
    real_next_cnt = 0
    
    for c in courses:
        text = f"{c.get('title', '')} {c.get('category', '')}"
        matches = matcher.extract_skills(text)
        new_skills = list(dict.fromkeys([m.skill for m in matches]))
        if "Next.js" in new_skills:
            real_next_cnt += 1
        ops.append(UpdateOne({"_id": c["_id"]}, {"$set": {"skills_matched": new_skills}}))

    if ops:
        db.courses.bulk_write(ops)

    print(f"[Next.js Cleanup] Completed courses! Real Next.js courses: {real_next_cnt} / {len(courses)} (dropped {len(courses) - real_next_cnt} false positives)")

    print("[Next.js Cleanup] Cleaning false-positive Next.js job matches via bulk write...")
    jobs = list(db.jobs.find({"skills_matched": "Next.js"}, {"_id": 1, "job_title": 1, "key_skills": 1}))
    print(f"[Next.js Cleanup] Found {len(jobs)} jobs tagged with Next.js")
    
    job_ops = []
    real_next_jobs = 0
    for j in jobs:
        text = f"{j.get('job_title', '')} {j.get('key_skills', '')}"
        matches = matcher.extract_skills(text)
        new_skills = list(dict.fromkeys([m.skill for m in matches]))
        if "Next.js" in new_skills:
            real_next_jobs += 1
        job_ops.append(UpdateOne({"_id": j["_id"]}, {"$set": {"skills_matched": new_skills}}))
        
    if job_ops:
        db.jobs.bulk_write(job_ops)

    print(f"[Next.js Cleanup] Completed jobs! Real Next.js jobs: {real_next_jobs} / {len(jobs)}")

if __name__ == "__main__":
    fix_nextjs_matches()
