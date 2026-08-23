import sys
from pathlib import Path
from collections import Counter

backend_dir = Path(__file__).resolve().parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.nlp.parse_resume import parse_resume
from app.data_pipeline.skill_matcher import SkillMatcher

def diagnose():
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)
    docs = list(db.resume_ner_training.find({}))
    
    fp_counter = Counter()
    for doc in docs:
        content = doc.get("content", "")
        annotations = doc.get("annotation", [])
        gt_skills = set()
        for a in annotations:
            if "Skills" in a.get("label", []):
                for p in a.get("points", []):
                    span_text = p.get("text", "").strip()
                    if span_text:
                        d = matcher.match_direct(span_text)
                        if d:
                            gt_skills.add(d.skill)
                        else:
                            extracted = matcher.extract_skills(span_text)
                            for m in extracted:
                                gt_skills.add(m.skill)
                                
        profile = parse_resume(content.encode("utf-8"), file_type="text", matcher=matcher)
        pred_skills = set(se.skill for se in profile.extracted_skills)
        for s in (pred_skills - gt_skills):
            fp_counter[s] += 1
            
    print("======================================================================")
    print("TOP 15 FALSE-POSITIVE SKILLS ACROSS ALL 220 VALIDATION RESUMES:")
    for i, (s, count) in enumerate(fp_counter.most_common(15), 1):
        print(f"  {i:2d}. {s:<32} : {count:3d} FPs")
    print("======================================================================")

if __name__ == "__main__":
    diagnose()
