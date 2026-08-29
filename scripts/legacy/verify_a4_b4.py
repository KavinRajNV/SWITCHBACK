"""
VERIFICATION SCRIPT — Parts A4, B4, C3
Tests the fixed course recommendations and role recommendations.

Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\verify_a4_b4.py
"""
import sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
import requests

BASE = "http://localhost:8000"

def p(label, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}")
    if detail:
        print(f"       {detail}")

# ─── Wait for server ──────────────────────────────────────────────────────────
print("Waiting for server...")
for _ in range(20):
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        if r.status_code == 200:
            print("[OK] Server healthy")
            break
    except:
        pass
    time.sleep(2)
else:
    print("[FATAL] Server not responding")
    sys.exit(1)

# ─── PART A4: Software Developer path — verify course relevance ───────────────
print("\n" + "=" * 70)
print("PART A4: Software Developer path course verification")
print("=" * 70)

# Create session with the resume-equivalent skill set
resume_skills = [
    {"skill": "Python", "confidence": 8},
    {"skill": "Java", "confidence": 7},
    {"skill": "JavaScript", "confidence": 8},
    {"skill": "AWS", "confidence": 7},
    {"skill": "Scikit-learn", "confidence": 6},
    {"skill": "Machine Learning", "confidence": 7},
    {"skill": "MongoDB", "confidence": 7},
    {"skill": "SQL", "confidence": 8},
    {"skill": "React", "confidence": 7},
    {"skill": "Node.js", "confidence": 7},
    {"skill": "Express.js", "confidence": 6},
    {"skill": "FastAPI", "confidence": 6},
    {"skill": "Git", "confidence": 8},
]

r = requests.post(f"{BASE}/api/profile/manual-skills", json={"skills": resume_skills}, timeout=20)
assert r.status_code == 200, f"manual-skills failed: {r.text}"
sid = r.json()["session_id"]
print(f"Session: {sid[:8]}...")
print(f"Skills stored: {r.json()['added_skills']}")

# Generate Software Developer path
rp = requests.post(f"{BASE}/api/path/generate",
                    json={"session_id": sid, "target_occupation_soc_code": "15-1252.00"},  # Software Developers
                    timeout=60)
assert rp.status_code == 200, f"path generate failed: {rp.text}"
pd = rp.json()

print(f"\nPath: {pd['target_occupation_title']} | {pd['path_length']} milestones")
print(f"Milestone skills: {[ms['skill'] for ms in pd['milestones']]}")

# Check the specifically problematic ones
problem_skills = {"Apache Spark", "C#", "Groovy", "Software Development", "C++", "COBOL"}
bad_courses = []
honest_empty = []

for ms in pd["milestones"]:
    skill = ms["skill"]
    free = ms.get("free_courses", [])
    paid = ms.get("paid_courses", [])
    all_courses = free + paid
    
    for c in all_courses:
        title = c.get("title", "").lower()
        url = c.get("url", "")
        source = c.get("source", "")
        
        # Skip YouTube (separate check)
        if "youtube" in url.lower():
            continue
        
        # Check for obviously irrelevant content
        bad_keywords = ["piano", "guitar", "meditation", "yoga", "spiritual", 
                       "self-heal", "manifest love", "happiness journal", 
                       "cardio boost", "chopin", "music of", "musician",
                       "soul:", "healing", "tantra", "law of attraction",
                       "groovy latin piano", "non dual"]
        
        is_bad = any(kw in title for kw in bad_keywords)
        if is_bad:
            bad_courses.append(f"  {skill}: [{c.get('title','?')[:60]}] ({source})")
    
    # Check skills in problem set with 0 courses
    if skill in problem_skills and len(all_courses) == 0:
        honest_empty.append(f"  {skill}: 0 courses (honest empty)")

p("No piano/yoga/meditation courses in path", len(bad_courses) == 0,
   "\n".join(bad_courses) if bad_courses else "none found")

if honest_empty:
    print("  Honest empty milestones (acceptable):")
    for e in honest_empty:
        print(e)

# Spot-check specific skills
print("\nDetailed check of problem skills in path:")
for ms in pd["milestones"]:
    if ms["skill"] in problem_skills:
        all_c = ms.get("free_courses", []) + ms.get("paid_courses", [])
        non_yt = [c for c in all_c if "youtube" not in c.get("url","")]
        print(f"  {ms['skill']}: {len(all_c)} total courses ({len(non_yt)} non-YouTube)")
        for c in non_yt[:3]:
            print(f"    - [{c.get('title','?')[:60]}] ({c.get('source','?')})")

# ─── PART B4: Role recommendations for resume skill set ──────────────────────
print("\n" + "=" * 70)
print("PART B4: Role recommendations — IDF-weighted verification")
print("=" * 70)

rr = requests.get(f"{BASE}/api/roles/recommended", params={"session_id": sid}, timeout=20)
assert rr.status_code == 200, f"recommended roles failed: {rr.text}"
rd = rr.json()

recs = rd.get("recommendations", [])
print(f"Skill count: {rd['skill_count']}, Floor: {rd['min_overlap_floor']}, Results: {len(recs)}")
print(f"\nTop 8 recommendations:")
for i, rec in enumerate(recs[:8]):
    print(f"  {i+1}. {rec['title']:<50} idf={rec['idf_weighted_score']:.4f} "
          f"overlap={rec['overlap_count']} matched={rec['matched_skills'][:5]}")

# Validation: top 5 should be tech/data/software related
tech_keywords = ["software", "data", "computer", "information", "web", "network",
                 "analyst", "engineer", "developer", "scientist", "systems",
                 "database", "security", "cloud", "machine"]
top5_titles = [rec["title"].lower() for rec in recs[:5]]
tech_hits = sum(1 for t in top5_titles if any(kw in t for kw in tech_keywords))

p("At least 4 of top 5 are tech/data/software roles", tech_hits >= 4,
   f"tech hits={tech_hits}/5, titles={[rec['title'] for rec in recs[:5]]}")

# Robotics Technician & Transportation Engineer should NOT be in top 5
bad_recs = [rec["title"] for rec in recs[:5]
            if any(x in rec["title"] for x in ["Robotics", "Transportation Engineer", "Materials Scientist"])]
p("Robotics/Transportation/Materials NOT in top 5", len(bad_recs) == 0,
   f"bad recs found: {bad_recs}")

# ─── PART C3: YouTube verification ────────────────────────────────────────────
print("\n" + "=" * 70)
print("PART C3: YouTube course verification")
print("=" * 70)

yt_per_skill = {}
for ms in pd["milestones"]:
    yt = [c for c in ms.get("free_courses", []) if "youtube" in c.get("url","").lower()]
    yt_per_skill[ms["skill"]] = yt

yt_total = sum(len(v) for v in yt_per_skill.values())
print(f"Total YouTube results across path: {yt_total}")
if yt_total > 0:
    for skill, vids in yt_per_skill.items():
        if vids:
            print(f"  {skill}: {len(vids)} YT videos, e.g. {vids[0].get('url','')[:60]}")
    p("YouTube videos present", True)
else:
    p("YouTube videos present", False, "None found — check API key quota")

print("\n=== VERIFICATION COMPLETE ===")
