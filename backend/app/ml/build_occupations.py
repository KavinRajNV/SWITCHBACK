import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from typing import Dict, Any, List, Set, Optional
from collections import Counter
import pandas as pd
import numpy as np
from rapidfuzz import fuzz, process
from pymongo.database import Database
from pymongo import ASCENDING

from app.db.mongo_client import get_db
from app.data_pipeline.skill_matcher import SkillMatcher

MAX_REQUIRED_SKILLS = 12

def build_occupations_enriched() -> Dict[str, Any]:
    """
    Enriches all 1,016 O*NET occupations with 3 layers of evidence:
    1. Taxonomy skills (O*NET essential & software skills)
    2. ESCO skills (ESCO occupation title fuzzy-matching)
    3. Market verified skills & salary (Naukri job titles fuzzy-clustering)

    Computes composite importance scores per candidate skill and caps combined_required_skills to top 12 (MAX_REQUIRED_SKILLS = 12).
    Inserts enriched documents into Mongo collection 'occupations_enriched'.
    """
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)

    print("[Build Occupations] Loading O*NET occupations catalog...")
    onet_docs = list(db.onet_occupations.find({}))
    if not onet_docs:
        raise ValueError("No O*NET occupations found in 'onet_occupations' collection!")

    print(f"[Build Occupations] Found {len(onet_docs)} O*NET occupations.")

    # Pre-index O*NET essential skills and software skills by SOC Code
    essential_by_soc: Dict[str, List[dict]] = {}
    for doc in db.onet_essential_skills.find({}, {"O*NET-SOC Code": 1, "Element Name": 1, "Data Value": 1}):
        code = doc.get("O*NET-SOC Code")
        if code:
            essential_by_soc.setdefault(code, []).append(doc)

    software_by_soc: Dict[str, List[dict]] = {}
    for doc in db.onet_software_skills.find({}, {"O*NET-SOC Code": 1, "Workplace Example": 1}):
        code = doc.get("O*NET-SOC Code")
        if code:
            software_by_soc.setdefault(code, []).append(doc)

    # Pre-index ESCO occupations and skill relations
    print("[Build Occupations] Indexing ESCO taxonomy...")
    esco_occ_docs = list(db.esco_occupations.find({}, {"conceptUri": 1, "preferredLabel": 1}))
    esco_labels = [d.get("preferredLabel", "").strip() for d in esco_occ_docs if d.get("preferredLabel")]
    esco_label_to_uri = {d["preferredLabel"].strip().lower(): d["conceptUri"] for d in esco_occ_docs if d.get("preferredLabel")}

    esco_rel_by_uri: Dict[str, List[dict]] = {}
    for doc in db.esco_occupation_skill_relations.find({}, {"occupationUri": 1, "skillUri": 1, "relationType": 1}):
        uri = doc.get("occupationUri")
        if uri:
            esco_rel_by_uri.setdefault(uri, []).append(doc)

    esco_skill_by_uri: Dict[str, str] = {}
    for doc in db.esco_skills.find({}, {"conceptUri": 1, "preferredLabel": 1}):
        uri = doc.get("conceptUri")
        label = doc.get("preferredLabel")
        if uri and label:
            esco_skill_by_uri[uri] = label

    # Pre-cluster top 150 primary job titles from Naukri
    print("[Build Occupations] Clustering Naukri job titles...")
    job_docs = list(db.jobs.find(
        {"source_quality": "primary"},
        {
            "job_title": 1,
            "skills_matched": 1,
            "salary_min_lpa": 1,
            "salary_max_lpa": 1
        }
    ))

    title_counts = Counter(d.get("job_title", "").strip().title() for d in job_docs if d.get("job_title"))
    top_150_titles = [t for t, _ in title_counts.most_common(150)]

    # Group job docs by title cluster
    job_docs_by_title: Dict[str, List[dict]] = {}
    for d in job_docs:
        t = d.get("job_title", "").strip().title()
        if t in set(top_150_titles):
            job_docs_by_title.setdefault(t, []).append(d)

    print("[Build Occupations] Enriching O*NET occupations and computing composite top-12 required skills...")

    esco_matches_count = 0
    market_matches_count = 0
    enriched_docs = []

    for idx, onet in enumerate(onet_docs):
        if (idx + 1) % 300 == 0 or (idx + 1) == len(onet_docs):
            print(f"[Build Occupations Progress] Processed {idx + 1}/{len(onet_docs)} O*NET occupations...")

        soc_code = onet.get("O*NET-SOC Code")
        title = onet.get("Title", "").strip()
        description = onet.get("Description", "").strip()

        if not soc_code or not title:
            continue

        # 1. Taxonomy Skills
        taxonomy_skills = []
        tax_seen = set()

        for item in essential_by_soc.get(soc_code, []):
            elem_name = item.get("Element Name", "")
            val = float(item.get("Data Value", 3.0)) if item.get("Data Value") is not None else 3.0
            extracted = matcher.extract_skills(elem_name)
            for m in extracted:
                if m.skill not in tax_seen:
                    tax_seen.add(m.skill)
                    taxonomy_skills.append({"skill": m.skill, "importance": val, "source": "onet"})

        for item in software_by_soc.get(soc_code, []):
            ex_name = item.get("Workplace Example", "")
            extracted = matcher.extract_skills(ex_name)
            if not extracted:
                d = matcher.match_direct(ex_name)
                if d:
                    extracted = [d]
            for m in extracted:
                if m.skill not in tax_seen:
                    tax_seen.add(m.skill)
                    taxonomy_skills.append({"skill": m.skill, "importance": 4.0, "source": "onet"})

        # 2. ESCO Required Skills
        esco_skills = []
        esco_seen = set()
        best_esco = process.extractOne(title, esco_labels, scorer=fuzz.token_set_ratio, score_cutoff=80) if esco_labels else None

        if best_esco:
            esco_matches_count += 1
            matched_esco_label = best_esco[0].lower()
            matched_esco_uri = esco_label_to_uri.get(matched_esco_label)

            if matched_esco_uri:
                for rel in esco_rel_by_uri.get(matched_esco_uri, []):
                    s_uri = rel.get("skillUri")
                    r_type = rel.get("relationType", "essential")
                    s_label = esco_skill_by_uri.get(s_uri, "")
                    if s_label:
                        extracted = matcher.extract_skills(s_label)
                        if not extracted:
                            d = matcher.match_direct(s_label)
                            if d:
                                extracted = [d]
                        for m in extracted:
                            if m.skill not in esco_seen:
                                esco_seen.add(m.skill)
                                esco_skills.append({"skill": m.skill, "relation_type": r_type, "source": "esco"})

        # 3. Market Verified Skills & Salary
        market_posting_count = 0
        market_salaries = []
        market_skill_counter: Counter = Counter()

        # Match O*NET title against top 150 Naukri titles
        matched_job_titles = [
            jt for jt in top_150_titles
            if fuzz.token_set_ratio(title, jt) >= 75
        ]

        if matched_job_titles:
            market_matches_count += 1
            for jt in matched_job_titles:
                postings = job_docs_by_title.get(jt, [])
                market_posting_count += len(postings)
                for p in postings:
                    for s in p.get("skills_matched", []):
                        market_skill_counter[s] += 1

                    s_min = p.get("salary_min_lpa")
                    s_max = p.get("salary_max_lpa")
                    if s_min is not None and s_max is not None:
                        market_salaries.append((s_min + s_max) / 2.0)
                    elif s_min is not None:
                        market_salaries.append(s_min)
                    elif s_max is not None:
                        market_salaries.append(s_max)

        market_median_salary = float(np.median(market_salaries)) if market_salaries else None
        market_verified_skills = [
            {"skill": s, "frequency": count}
            for s, count in market_skill_counter.most_common(15)
        ]

        # 4. Composite Scoring & Top 12 Capping (Patch D)
        candidates_map: Dict[str, Dict[str, float]] = {}

        for ts in taxonomy_skills:
            sk = ts["skill"]
            imp = ts.get("importance", 3.0)
            candidates_map.setdefault(sk, {"onet_imp": 0.0, "esco_val": 0.0, "mkt_freq": 0.0})
            if imp > candidates_map[sk]["onet_imp"]:
                candidates_map[sk]["onet_imp"] = imp

        for es in esco_skills:
            sk = es["skill"]
            val = 0.4 if es.get("relation_type") == "essential" else 0.2
            candidates_map.setdefault(sk, {"onet_imp": 0.0, "esco_val": 0.0, "mkt_freq": 0.0})
            if val > candidates_map[sk]["esco_val"]:
                candidates_map[sk]["esco_val"] = val

        for ms in market_verified_skills:
            sk = ms["skill"]
            freq = float(ms.get("frequency", 0))
            candidates_map.setdefault(sk, {"onet_imp": 0.0, "esco_val": 0.0, "mkt_freq": 0.0})
            if freq > candidates_map[sk]["mkt_freq"]:
                candidates_map[sk]["mkt_freq"] = freq

        # Compute per-occupation min-max normalization
        all_onet = [c["onet_imp"] for c in candidates_map.values()]
        all_mkt = [c["mkt_freq"] for c in candidates_map.values()]

        min_onet, max_onet = (min(all_onet), max(all_onet)) if all_onet else (0.0, 0.0)
        min_mkt, max_mkt = (min(all_mkt), max(all_mkt)) if all_mkt else (0.0, 0.0)

        scored_candidates: List[Tuple[str, float]] = []

        for sk, vals in candidates_map.items():
            norm_onet = (vals["onet_imp"] - min_onet) / (max_onet - min_onet) if max_onet > min_onet else (1.0 if vals["onet_imp"] > 0 else 0.0)
            norm_mkt = (vals["mkt_freq"] - min_mkt) / (max_mkt - min_mkt) if max_mkt > min_mkt else (1.0 if vals["mkt_freq"] > 0 else 0.0)
            c_score = norm_onet + vals["esco_val"] + norm_mkt
            scored_candidates.append((sk, c_score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_12_required = [sk for sk, _ in scored_candidates[:MAX_REQUIRED_SKILLS]]

        doc = {
            "onet_soc_code": soc_code,
            "title": title,
            "description": description,
            "taxonomy_required_skills": taxonomy_skills,
            "esco_required_skills": esco_skills,
            "market_median_salary_lpa": market_median_salary,
            "market_posting_count": market_posting_count,
            "market_verified_skills": market_verified_skills,
            "combined_required_skills": top_12_required
        }
        enriched_docs.append(doc)

    # Insert into Mongo 'occupations_enriched'
    coll = db["occupations_enriched"]
    coll.delete_many({})
    if enriched_docs:
        coll.insert_many(enriched_docs)
        coll.create_index([("onet_soc_code", ASCENDING)])
        coll.create_index([("title", ASCENDING)])

    print("======================================================================")
    print(f"[Build Occupations] Enriched {len(enriched_docs)} total O*NET occupations (Capped at MAX_REQUIRED_SKILLS = {MAX_REQUIRED_SKILLS}).")
    print(f"  - ESCO match coverage: {esco_matches_count}/{len(enriched_docs)} ({round(esco_matches_count/len(enriched_docs)*100, 2)}%)")
    print(f"  - Market grounding coverage: {market_matches_count}/{len(enriched_docs)} ({round(market_matches_count/len(enriched_docs)*100, 2)}%)")
    print("======================================================================")

    return {
        "total_enriched": len(enriched_docs),
        "max_required_skills": MAX_REQUIRED_SKILLS,
        "esco_matches_count": esco_matches_count,
        "market_matches_count": market_matches_count
    }

if __name__ == "__main__":
    build_occupations_enriched()
