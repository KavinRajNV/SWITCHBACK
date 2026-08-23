import re
import json
from pathlib import Path
from typing import Set, List, Dict, Any, Union, Optional
from collections import Counter
import numpy as np
from pymongo.database import Database

from app.config import settings

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
MANIFEST_PATH = ARTIFACTS_DIR / "feature_manifest.json"

SENIORITY_PATTERNS = [
    (7, r'\b(vp|vice president|cxo|chief|president)\b'),
    (6, r'\b(director|head)\b'),
    (5, r'\b(manager)\b'),
    (4, r'\b(lead|principal|staff)\b'),
    (3, r'\b(senior|sr\.?)\b'),
    (1, r'\b(associate|junior)\b'),
    (0, r'\b(intern|trainee|fresher)\b'),
]

def parse_seniority(job_title: Optional[str]) -> float:
    """
    Parses job title string using regex keyword matching (case-insensitive) to produce ordinal seniority_level (0..7).
    Returns highest-numbered match, or 2 (default mid-level).
    """
    if not job_title or not isinstance(job_title, str):
        return 2.0
    
    matches = []
    for level, pattern in SENIORITY_PATTERNS:
        if re.search(pattern, job_title, re.IGNORECASE):
            matches.append(level)
            
    if matches:
        return float(max(matches))
    return 2.0

def build_feature_manifest(db: Database) -> Dict[str, Any]:
    """
    Computes and saves the canonical feature manifest to backend/app/artifacts/feature_manifest.json.
    Manifest version: 2 (323 total features).
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Skill columns (sorted canonical skills - 265 skills)
    vocab_docs = list(db.skill_vocabulary.find({}, {"canonical_skill": 1}))
    skills_ordered = sorted(list(set(d["canonical_skill"] for d in vocab_docs if d.get("canonical_skill"))))

    # 2. Top 20 locations from primary jobs
    loc_counter: Counter = Counter()
    for job in db.jobs.find({"source_quality": "primary"}, {"locations": 1}):
        for loc in job.get("locations", []):
            if loc and isinstance(loc, str) and loc.strip():
                loc_counter[loc.strip().title()] += 1

    top_20_loc_tuples = loc_counter.most_common(20)
    locations_ordered = [loc for loc, _ in top_20_loc_tuples]

    # 3. Top 30 companies from primary disclosed salary jobs
    comp_counter: Counter = Counter()
    for job in db.jobs.find({"source_quality": "primary", "salary_disclosed": True}, {"company": 1}):
        c = job.get("company")
        if c and isinstance(c, str) and c.strip():
            comp_counter[c.strip().title()] += 1

    top_30_comp_tuples = comp_counter.most_common(30)
    companies_ordered = [comp for comp, _ in top_30_comp_tuples]

    # 4. Complete ordered feature names list
    exp_features = ["experience_min_years", "experience_max_years", "experience_mid_years"]
    loc_features = [f"loc_{loc}" for loc in locations_ordered]
    meta_loc_features = ["multi_city_posting", "other_location"]
    seniority_features = ["seniority_level", "seniority_unspecified"]
    company_features = [f"comp_{comp}" for comp in companies_ordered] + ["other_company"]

    feature_names = skills_ordered + exp_features + loc_features + meta_loc_features + seniority_features + company_features

    manifest = {
        "manifest_version": 2,
        "num_skills": len(skills_ordered),
        "num_locations": len(locations_ordered),
        "num_companies": len(companies_ordered),
        "num_total_features": len(feature_names),
        "skills_ordered": skills_ordered,
        "locations_ordered": locations_ordered,
        "companies_ordered": companies_ordered,
        "feature_names": feature_names
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[Feature Manifest v2] Saved manifest ({len(feature_names)} features) to: {MANIFEST_PATH}")
    return manifest

def load_feature_manifest() -> Dict[str, Any]:
    """
    Loads the feature manifest from backend/app/artifacts/feature_manifest.json.
    """
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Feature manifest not found at {MANIFEST_PATH}. Run build_feature_manifest(db) first.")
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def vectorize(
    skills: Union[Set[str], List[str]],
    experience_min: float = 2.0,
    experience_max: float = 5.0,
    locations: Optional[List[str]] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    manifest: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Vectorizes a learner profile or job posting into a 1D numpy float64 array according to manifest v2 (323 features).
    """
    if manifest is None:
        manifest = load_feature_manifest()

    skills_set = set(skills)
    skills_ordered = manifest["skills_ordered"]
    locations_ordered = manifest["locations_ordered"]
    companies_ordered = manifest.get("companies_ordered", [])

    # 1. Skill multi-hot encoding
    skill_vec = [1.0 if s in skills_set else 0.0 for s in skills_ordered]

    # 2. Experience features
    exp_min = float(experience_min) if experience_min is not None else 2.0
    exp_max = float(experience_max) if experience_max is not None else exp_min
    exp_mid = (exp_min + exp_max) / 2.0
    exp_vec = [exp_min, exp_max, exp_mid]

    # 3. Location features
    input_locs = locations if locations is not None else ["Bangalore"]
    norm_input_locs = [l.strip().title() for l in input_locs if l and isinstance(l, str) and l.strip()]
    loc_set = set(norm_input_locs)

    loc_vec = [1.0 if loc in loc_set else 0.0 for loc in locations_ordered]
    multi_city = 1.0 if len(norm_input_locs) > 1 else 0.0
    has_top_loc = any(loc in locations_ordered for loc in norm_input_locs)
    other_loc = 1.0 if (norm_input_locs and not has_top_loc) else 0.0

    meta_loc_vec = [multi_city, other_loc]

    # 4. Seniority features (B1)
    if job_title:
        seniority_lvl = parse_seniority(job_title)
        seniority_unspec = 0.0
    else:
        seniority_lvl = 2.0  # Mid-level default
        seniority_unspec = 0.0

    seniority_vec = [seniority_lvl, seniority_unspec]

    # 5. Company features (B2)
    comp_vec = []
    comp_clean = company.strip().title() if (company and isinstance(company, str) and company.strip()) else ""
    if comp_clean:
        comp_vec = [1.0 if c == comp_clean else 0.0 for c in companies_ordered]
        has_top_comp = comp_clean in companies_ordered
        comp_vec.append(1.0 if not has_top_comp else 0.0)
    else:
        comp_vec = [0.0] * len(companies_ordered) + [0.0]

    # Concatenate all feature blocks into a 1D vector
    full_vec = np.array(skill_vec + exp_vec + loc_vec + meta_loc_vec + seniority_vec + comp_vec, dtype=np.float64)
    return full_vec
