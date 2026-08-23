import sys
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from collections import Counter
from pymongo.database import Database

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.data_pipeline.skill_matcher import SkillMatcher

def build_skill_edges() -> List[Dict[str, Any]]:
    """
    Constructs merged directed weighted skill-skill transition edges combining:
    1. ESCO taxonomy skill-skill relations (esco_skill_skill_relations)
    2. Empirical co-occurrence across jobs.skills_matched and courses.skills_matched
    Returns list of edge dicts: [{"source": str, "target": str, "weight": float, "source_type": str}]
    """
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)

    print("[Skill Edges] Building taxonomy skill-skill edges from ESCO...")
    # Fast map ESCO skill URI -> canonical skill using direct match
    esco_uri_to_canonical: Dict[str, str] = {}
    for doc in db.esco_skills.find({}, {"conceptUri": 1, "preferredLabel": 1}):
        uri = doc.get("conceptUri")
        label = doc.get("preferredLabel")
        if uri and label:
            d = matcher.match_direct(label)
            if d:
                esco_uri_to_canonical[uri] = d.skill

    tax_edges: Dict[Tuple[str, str], float] = {}

    for doc in db.esco_skill_skill_relations.find({}, {"originalSkillUri": 1, "relatedSkillUri": 1, "relationType": 1}):
        u_uri = doc.get("originalSkillUri")
        v_uri = doc.get("relatedSkillUri")
        rel_type = doc.get("relationType", "optional")

        u_skill = esco_uri_to_canonical.get(u_uri)
        v_skill = esco_uri_to_canonical.get(v_uri)

        if u_skill and v_skill and u_skill != v_skill:
            weight = 0.5 if rel_type == "essential" else 1.0
            pair = (u_skill, v_skill)
            if pair not in tax_edges or weight < tax_edges[pair]:
                tax_edges[pair] = weight

    print(f"[Skill Edges] Mapped {len(tax_edges)} taxonomy skill-skill edges.")

    print("[Skill Edges] Computing empirical co-occurrence edges across jobs and courses...")
    co_occurrences: Counter = Counter()

    for job in db.jobs.find({}, {"skills_matched": 1}):
        skills = sorted(list(set(job.get("skills_matched", []))))
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                co_occurrences[(skills[i], skills[j])] += 1
                co_occurrences[(skills[j], skills[i])] += 1

    for course in db.courses.find({}, {"skills_matched": 1}):
        skills = sorted(list(set(course.get("skills_matched", []))))
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                co_occurrences[(skills[i], skills[j])] += 1
                co_occurrences[(skills[j], skills[i])] += 1

    # Filter by minimum co-occurrence threshold >= 5
    emp_edges: Dict[Tuple[str, str], float] = {}
    valid_pairs = {pair: count for pair, count in co_occurrences.items() if count >= 5}

    if valid_pairs:
        max_count = max(valid_pairs.values())
        log_max = math.log(max_count) if max_count > 1 else 1.0

        for (u, v), count in valid_pairs.items():
            # Normalized cost weight: higher co-occurrence -> lower transition cost (min 0.2, max 1.0)
            cost_weight = max(0.2, round(1.0 - (math.log(count) / log_max), 4))
            emp_edges[(u, v)] = cost_weight

    print(f"[Skill Edges] Extracted {len(emp_edges)} empirical skill-skill edges.")

    # Merge edge sets: take minimum (easier) transition weight
    merged_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    all_pairs = set(tax_edges.keys()).union(set(emp_edges.keys()))

    for pair in all_pairs:
        u, v = pair
        w_tax = tax_edges.get(pair)
        w_emp = emp_edges.get(pair)

        if w_tax is not None and w_emp is not None:
            final_weight = min(w_tax, w_emp)
            source_type = "hybrid"
        elif w_tax is not None:
            final_weight = w_tax
            source_type = "taxonomy"
        else:
            final_weight = w_emp
            source_type = "empirical"

        merged_map[pair] = {
            "source": u,
            "target": v,
            "weight": final_weight,
            "source_type": source_type
        }

    merged_edges = list(merged_map.values())
    return merged_edges

if __name__ == "__main__":
    edges = build_skill_edges()
    print(f"[Skill Edges] Generated {len(edges)} total skill-skill edges.")
