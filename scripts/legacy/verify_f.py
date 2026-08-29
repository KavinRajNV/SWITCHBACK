"""
PART F: Verification of full system.
Tests the complete test resume through the fixed endpoint.
Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\verify_f.py
"""
import sys, time, json
sys.stdout.reconfigure(encoding='utf-8')
import requests

BASE = "http://localhost:8000"

print("Waiting for server...")
for _ in range(25):
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        if r.status_code == 200:
            hd = r.json()
            print(f"[OK] Server healthy: {hd}")
            break
    except:
        pass
    time.sleep(3)
else:
    print("[FATAL] Server not responding after 75s")
    sys.exit(1)

# Full test resume skill set
resume_skills = [
    {"skill": "Python", "confidence": 9},
    {"skill": "Java", "confidence": 7},
    {"skill": "JavaScript", "confidence": 8},
    {"skill": "AWS", "confidence": 8},
    {"skill": "Scikit-learn", "confidence": 7},
    {"skill": "Machine Learning", "confidence": 8},
    {"skill": "LLMs", "confidence": 7},
    {"skill": "RAG", "confidence": 7},
    {"skill": "Vector Databases", "confidence": 6},
    {"skill": "MongoDB", "confidence": 7},
    {"skill": "SQL", "confidence": 8},
    {"skill": "React", "confidence": 7},
    {"skill": "Node.js", "confidence": 7},
    {"skill": "Express.js", "confidence": 6},
    {"skill": "FastAPI", "confidence": 7},
    {"skill": "Git", "confidence": 8},
]

r = requests.post(f"{BASE}/api/profile/manual-skills", json={"skills": resume_skills}, timeout=20)
assert r.status_code == 200, f"manual-skills failed: {r.text}"
resp = r.json()
sid = resp["session_id"]
print(f"\nSession: {sid[:8]}...")
print(f"Skills canonicalized: {resp['added_skills']}")
print(f"Total stored: {resp['total_current_skills']}")

# Test role recommendations
print("\n" + "=" * 70)
print("PART F: Role recommendations for full test resume")
print("=" * 70)
rr = requests.get(f"{BASE}/api/roles/recommended", params={"session_id": sid}, timeout=20)
assert rr.status_code == 200, f"recommended failed: {rr.text}"
rd = rr.json()

print(f"Skill count: {rd['skill_count']}, Catalog size: {rd.get('catalog_size','?')}")
print(f"Min overlap floor: {rd['min_overlap_floor']}, Results: {len(rd['recommendations'])}")
print()
print("Top 8 recommendations:")
for i, rec in enumerate(rd["recommendations"][:8]):
    src = rec.get("catalog_source", "?")
    print(f"  {i+1}. [{src}] {rec['title']}")
    print(f"     composite={rec['composite_score']:.4f} idf={rec['idf_weighted_score']:.4f} "
          f"overlap={rec['overlap_count']} postings={rec.get('market_posting_count',0)}")
    print(f"     matched: {rec['matched_skills'][:8]}")

# Evaluate quality
tech_keywords = ["software", "data", "machine", "learning", "developer", "engineer",
                 "scientist", "analyst", "backend", "frontend", "full", "stack",
                 "cloud", "information", "computer", "web", "security", "platform"]
top5_titles = [rec["title"].lower() for rec in rd["recommendations"][:5]]
tech_hits = sum(1 for t in top5_titles if any(kw in t for kw in tech_keywords))
print(f"\nTech relevance: {tech_hits}/5 top results are tech/data roles")

# Check overlap improvement vs baseline (was 3 skills, 10% Jaccard)
max_overlap = max((rec["overlap_count"] for rec in rd["recommendations"]), default=0)
print(f"Best overlap: {max_overlap} skills (baseline was 3)")
if max_overlap > 3:
    print("[IMPROVEMENT] Overlap count exceeded baseline of 3")
elif max_overlap == 3:
    print("[SAME] Overlap count same as baseline (data constraint)")

# Test path generation for top 2 market-native results
print("\n" + "=" * 70)
print("PART F: Path generation for top market-native roles")
print("=" * 70)
market_recs = [r for r in rd["recommendations"] if r.get("catalog_source") == "market"][:2]
if not market_recs:
    print("[WARN] No market-native recommendations found — check market_roles_dict loading")
else:
    for rec in market_recs:
        role_id = rec.get("role_id", "")
        title = rec["title"]
        soc = rec.get("onet_soc_code")
        
        print(f"\nGenerating path for: {title} (soc={soc})")
        path_req = {"session_id": sid}
        if soc:
            path_req["target_occupation_soc_code"] = soc
        
        rp = requests.post(f"{BASE}/api/path/generate", json=path_req, timeout=60)
        if rp.status_code == 200:
            pd = rp.json()
            milestones = [ms["skill"] for ms in pd["milestones"]]
            print(f"  Path: {pd['target_occupation_title']} | {pd['path_length']} milestones")
            print(f"  Milestone skills: {milestones}")
            # Check first milestone has courses
            if pd["milestones"]:
                ms0 = pd["milestones"][0]
                nc = len(ms0.get("free_courses", [])) + len(ms0.get("paid_courses", []))
                print(f"  First milestone '{ms0['skill']}': {nc} courses")
        else:
            print(f"  [FAIL] Status {rp.status_code}: {rp.text[:200]}")

# Part D: YouTube Excel check
print("\n" + "=" * 70)
print("PART D: YouTube Excel check (should NOT be Azure content)")
print("=" * 70)
import sys
sys.path.insert(0, r'd:\switchback\backend')
from app.db.mongo_client import get_db
db = get_db()
excel_cache = db.youtube_cache.find_one({"skill_key": "microsoft excel"})
if excel_cache:
    vids = excel_cache.get("videos", [])
    print(f"Cached videos for Excel: {len(vids)}")
    for v in vids:
        print(f"  [{v.get('channel_title','?')}] {v.get('title','?')[:70]}")
        print(f"    url: {v.get('url','')[:60]}")
else:
    print("No Excel cache yet (will be populated on next path generation)")

print("\n=== VERIFICATION COMPLETE ===")
