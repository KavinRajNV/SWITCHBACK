"""Diagnose combined_required_skills for the bad recommendations."""
import sys, math
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

bad_roles = [
    "Photographic Process Workers and Processing Machine Operators",
    "Robotics Technicians",
    "Security Management Specialists",
    "Materials Scientists",
    "Geoscientists, Except Hydrologists and Geographers",
    "Desktop Publishers",
]

good_roles = [
    "Data Scientists",
    "Software Developers",
    "Web Developers",
    "Database Architects",
    "Computer Systems Analysts",
    "Information Security Analysts",
    "Machine Learning Engineers",
    "Cloud Engineers",
]

print("=== BAD ROLES - combined_required_skills ===\n")
for title in bad_roles:
    occ = db.occupations_enriched.find_one({"title": title})
    if occ:
        crs = occ.get("combined_required_skills", [])
        print(f"  {title}:")
        print(f"    count={len(crs)}, skills={crs}")
        print(f"    posting_count={occ.get('market_posting_count')}, salary={occ.get('market_median_salary_lpa')}")
    else:
        print(f"  NOT FOUND: {title}")
    print()

print("=== GOOD ROLES - combined_required_skills ===\n")
for title in good_roles:
    occ = db.occupations_enriched.find_one({"title": title})
    if occ:
        crs = occ.get("combined_required_skills", [])
        print(f"  {title}:")
        print(f"    count={len(crs)}, skills={crs}")
        print(f"    posting_count={occ.get('market_posting_count')}, salary={occ.get('market_median_salary_lpa')}")
    else:
        print(f"  NOT FOUND: {title}")
    print()

# Check: how many occupations have Express.js / FastAPI / Scikit-learn in combined_required_skills
print("=== Rarity check for key skills ===")
for skill in ["Express.js", "FastAPI", "Scikit-learn", "MongoDB", "React", "Node.js", 
              "Git", "AWS", "Python", "JavaScript", "SQL"]:
    count = db.occupations_enriched.count_documents({"combined_required_skills": skill})
    print(f"  '{skill}': present in {count} occupations")
    if count <= 5:
        # Who are these occupations?
        occupations = list(db.occupations_enriched.find(
            {"combined_required_skills": skill}, {"title": 1}
        ).limit(10))
        for o in occupations:
            print(f"    -> {o.get('title')}")
