import sys
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

for title in ['Full Stack Developer', 'Software Engineer', 'Machine Learning Engineer',
              'Data Scientist', 'Backend Developer', 'Frontend Developer', 'Data Engineer',
              'Senior Data Scientist', 'NLP Engineer']:
    r = db.market_roles.find_one({'title': title})
    if r:
        skills = r.get('combined_required_skills', [])
        count = r.get('market_posting_count', 0)
        sal = r.get('market_median_salary_lpa')
        print(f"{title} ({count} postings, sal={sal}L):")
        print(f"  skills: {skills[:15]}")
    else:
        print(f"{title}: NOT FOUND")
    print()

# Invalidate stale YouTube Excel cache
result = db.youtube_cache.delete_one({'skill_key': 'microsoft excel'})
print(f"Deleted Excel YouTube cache: {result.deleted_count} docs")
result2 = db.youtube_cache.delete_one({'skill_key': 'microsoft powerpoint'})
print(f"Deleted PowerPoint YouTube cache: {result2.deleted_count} docs")
