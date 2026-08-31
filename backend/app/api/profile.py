from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from app.models.schemas import LearnerProfile, GoalProfile, SkillEvidence
from app.nlp.parse_resume import parse_resume
from app.nlp.goal_parser import parse_goal_text

from app.api.session_store import create_session, get_session, update_session

router = APIRouter(prefix="/api", tags=["Profile & Goal"])

class GoalTextRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    goal_text: str = Field(..., description="Free-text goal prompt")

class ManualSkillItem(BaseModel):
    skill: str = Field(..., description="Skill name")
    confidence: Optional[int] = Field(default=5, ge=1, le=10, description="Self-rated confidence 1-10")

class ManualSkillsRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    # Accept either {skill, confidence} objects OR plain strings (normalised in endpoint)
    skills: List[Any] = Field(..., description="List of skill objects or skill name strings")

@router.post("/profile/from-resume")
async def profile_from_resume(request: Request, file: UploadFile = File(...)):
    """
    Parses an uploaded PDF, DOCX, or text resume file, creates a session, and returns profile.
    """
    filename = file.filename or ""
    fn_lower = filename.lower()

    if fn_lower.endswith(".pdf"):
        file_type = "pdf"
    elif fn_lower.endswith(".docx"):
        file_type = "docx"
    else:
        file_type = "text"

    content = await file.read()
    matcher = request.app.state.matcher
    db = request.app.state.db

    profile = parse_resume(content, file_type=file_type, matcher=matcher)
    session_id = create_session(learner_profile=profile, db=db)

    return {
        "session_id": session_id,
        "learner_profile": profile
    }

@router.post("/profile/from-goal-text")
async def profile_from_goal_text(req_data: GoalTextRequest, request: Request):
    """
    Parses a free-text goal input, attaching to an existing session or creating a new session.
    """
    db = request.app.state.db
    # Keep the deterministic parser as the contract/authority for catalog role
    # matching, while NVIDIA extracts explicit baseline skills and fills in
    # natural-language details the regex parser cannot reliably see.
    goal_profile = parse_goal_text(req_data.goal_text, db=db)
    
    extracted_evidence = []
    extracted_skills = []
    
    from app.nlp.openai_extract import extract_goal_openai
    ai_result = extract_goal_openai(req_data.goal_text)
    if ai_result:
        if not goal_profile.timeframe_days and isinstance(ai_result.get("timeframe_days"), int):
            goal_profile.timeframe_days = max(1, ai_result["timeframe_days"])
        if not goal_profile.hours_per_week and isinstance(ai_result.get("hours_per_week"), int):
            goal_profile.hours_per_week = max(1, min(168, ai_result["hours_per_week"]))
        if not goal_profile.background_hint and isinstance(ai_result.get("background_hint"), str):
            goal_profile.background_hint = ai_result["background_hint"][:2000]
        
        if not goal_profile.target_role and isinstance(ai_result.get("target_role"), str):
            role_profile = parse_goal_text(ai_result["target_role"], db=db)
            if role_profile.target_role:
                goal_profile.target_role = role_profile.target_role
                goal_profile.target_soc_code = role_profile.target_soc_code
                goal_profile.needs_clarification = False

        # Extract current skills from the AI result
        matcher = request.app.state.matcher
        yoe = ai_result.get("years_of_experience")
        # Score logic: base 5, +1 for each year, capped at 10
        conf = 5
        if isinstance(yoe, (int, float)) and yoe > 0:
            conf = min(10, 5 + int(yoe))
            
        raw_ai_skills = ai_result.get("current_skills") or []
        if isinstance(raw_ai_skills, list) and matcher:
            for skill_str in raw_ai_skills:
                if not isinstance(skill_str, str): continue
                match = matcher.match_direct(skill_str)
                if match:
                    extracted_skills.append(match.skill)
                    extracted_evidence.append(SkillEvidence(
                        skill=match.skill,
                        category=match.category,
                        confidence=conf,
                        mention_count=1,
                        found_in_sections=["GOAL_AI_EXTRACTED"]
                    ))

    session_id = req_data.session_id
    if session_id:
        sess = get_session(session_id, db=db)
        if not sess:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        target_soc = goal_profile.target_soc_code or sess.get("target_occupation_soc_code")
        existing_profile = sess.get("learner_profile", {})
        existing_evidence = existing_profile.get("extracted_skills", [])
        existing_names = {item.get("skill", "").lower() for item in existing_evidence}
        for evidence in extracted_evidence:
            if evidence.skill.lower() not in existing_names:
                existing_evidence.append(evidence.model_dump())
        existing_profile["extracted_skills"] = existing_evidence
        current_skills = list(dict.fromkeys(sess.get("current_skills", []) + extracted_skills))
        update_session(session_id, {
            "goal_profile": goal_profile.model_dump(),
            "target_occupation_soc_code": target_soc,
            "learner_profile": existing_profile,
            "current_skills": current_skills,
        }, db=db)
    else:
        learner_profile = LearnerProfile(extracted_skills=extracted_evidence)
        session_id = create_session(
            learner_profile=learner_profile,
            goal_profile=goal_profile,
            current_skills=extracted_skills,
            db=db,
        )

    return {
        "session_id": session_id,
        "goal_profile": goal_profile,
        # Return the (empty) learner_profile so frontend never falls back to hardcoded skills
        "learner_profile": get_session(session_id, db=db).get("learner_profile", {}),
        # Expose target_occupation as a top-level convenience object
        "target_occupation": {
            "onet_soc_code": goal_profile.target_soc_code,
            "title": goal_profile.target_role,
        } if goal_profile.target_soc_code else None
    }


@router.post("/profile/manual-skills")
async def profile_manual_skills(req_data: ManualSkillsRequest, request: Request):
    """
    Attaches manually entered skill strings to a session after canonicalization via SkillMatcher.
    Confidence tier for self-reported manual skills is assigned to 5.
    """
    matcher = request.app.state.matcher
    db = request.app.state.db

    # Normalise each element: accept {skill, confidence} dict or plain string
    raw_items: List[ManualSkillItem] = []
    for item in req_data.skills:
        if isinstance(item, dict):
            raw_items.append(ManualSkillItem(
                skill=item.get("skill", ""),
                confidence=item.get("confidence", 5)
            ))
        else:
            raw_items.append(ManualSkillItem(skill=str(item), confidence=5))

    canonical_skills: List[str] = []
    evidence_list: List[SkillEvidence] = []

    for item in raw_items:
        raw_s = item.skill
        conf = item.confidence or 5
        d = matcher.match_direct(raw_s)
        if d:
            sk = d.skill
            cat = d.category
        else:
            extracted = matcher.extract_skills(raw_s)
            if extracted:
                sk = extracted[0].skill
                cat = extracted[0].category
            else:
                sk = raw_s.strip()
                cat = "General"

        if sk and sk not in canonical_skills:
            canonical_skills.append(sk)
            evidence_list.append(SkillEvidence(
                skill=sk,
                category=cat,
                confidence=conf,
                mention_count=1,
                found_in_sections=["MANUAL"]
            ))

    session_id = req_data.session_id
    if session_id:
        sess = get_session(session_id, db=db)
        if not sess:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

        existing_curr = set(sess.get("current_skills", []))
        existing_curr.update(canonical_skills)
        
        # Merge learner profile extracted skills
        lp_dict = sess.get("learner_profile", {})
        existing_ev = lp_dict.get("extracted_skills", [])
        existing_skills_map = {e["skill"]: e for e in existing_ev}

        for new_ev in evidence_list:
            if new_ev.skill not in existing_skills_map:
                existing_ev.append(new_ev.model_dump())

        lp_dict["extracted_skills"] = existing_ev
        update_session(session_id, {
            "current_skills": list(existing_curr),
            "learner_profile": lp_dict
        }, db=db)
    else:
        lp = LearnerProfile(extracted_skills=evidence_list)
        session_id = create_session(learner_profile=lp, current_skills=canonical_skills, db=db)
        lp_dict = lp.model_dump()

    # Always return learner_profile so the frontend never falls back to hardcoded defaults
    final_sess = get_session(session_id, db=db)
    lp_out = final_sess.get("learner_profile", {})
    return {
        "session_id": session_id,
        "added_skills": canonical_skills,
        "total_current_skills": len(final_sess.get("current_skills", [])),
        "learner_profile": lp_out,
    }

@router.get("/skills/search")
async def search_skills(request: Request, q: str = Query(..., min_length=1)):
    """
    Autocomplete search against skill vocabulary (top 10).
    """
    matcher = request.app.state.matcher
    q_lower = q.strip().lower()

    # Prefix match first
    matches = [s for s in sorted(list(matcher.canonical_skills)) if s.lower().startswith(q_lower)]
    if len(matches) < 10:
        fuzzy_res = process.extract(q_lower, list(matcher.canonical_skills), scorer=fuzz.token_set_ratio, limit=10)
        for name, score, _ in fuzzy_res:
            if name not in matches and len(matches) < 10:
                matches.append(name)

    return {
        "query": q,
        "results": matches[:10]
    }

@router.get("/roles/search")
async def search_roles(request: Request, q: str = Query(..., min_length=1)):
    """
    E5: Unified occupation search across both O*NET/ESCO catalog (occupations_dict)
    and the Naukri-native market catalog (market_roles_dict).
    Market roles are returned first as they use familiar, recognizable titles.
    """
    occupations_dict = request.app.state.occupations_dict
    market_roles_dict = getattr(request.app.state, "market_roles_dict", {})
    q_lower = q.strip().lower()

    results = []

    # 1. Market-native roles first (familiar titles, real posting volumes)
    market_results = []
    for mid, doc in market_roles_dict.items():
        title = doc.get("title", "")
        if title.lower().startswith(q_lower):
            market_results.insert(0, {
                "title": title,
                "catalog_source": "market",
                "market_role_id": mid,
                "onet_soc_code": doc.get("onet_soc_code"),
                "market_posting_count": doc.get("market_posting_count"),
                "market_median_salary_lpa": doc.get("market_median_salary_lpa"),
            })
        elif q_lower in title.lower():
            market_results.append({
                "title": title,
                "catalog_source": "market",
                "market_role_id": mid,
                "onet_soc_code": doc.get("onet_soc_code"),
                "market_posting_count": doc.get("market_posting_count"),
                "market_median_salary_lpa": doc.get("market_median_salary_lpa"),
            })
    # Sort market results by posting count (most popular first)
    market_results.sort(key=lambda x: x.get("market_posting_count") or 0, reverse=True)
    results.extend(market_results[:5])

    # 2. O*NET roles (formal/specialized titles)
    titles_map = {doc["title"]: doc["onet_soc_code"] for doc in occupations_dict.values() if doc.get("title")}
    titles = list(titles_map.keys())
    existing_titles = {r["title"] for r in results}

    prefix_matches = [t for t in titles if t.lower().startswith(q_lower) and t not in existing_titles]
    for t in prefix_matches[:5]:
        results.append({"title": t, "catalog_source": "onet", "onet_soc_code": titles_map[t]})
        existing_titles.add(t)

    if len(results) < 10:
        fuzzy_res = process.extract(q_lower, titles, scorer=fuzz.token_set_ratio, limit=10)
        for name, score, _ in fuzzy_res:
            if name not in existing_titles and len(results) < 10:
                results.append({"title": name, "catalog_source": "onet", "onet_soc_code": titles_map[name]})
                existing_titles.add(name)

    return {
        "query": q,
        "results": results[:10]
    }

@router.get("/roles/{soc_code}/related")
async def get_related_roles(soc_code: str, request: Request):
    """
    Returns top 3-5 related occupations for a given O*NET SOC code from onet_related_occupations
    where Relatedness Tier == 'Primary-Short', enriched with market median salary if available.
    """
    db = request.app.state.db
    soc_code = soc_code.strip()

    cursor = db.onet_related_occupations.find({
        "O*NET-SOC Code": soc_code,
        "Relatedness Tier": "Primary-Short"
    }).sort("Index", 1).limit(5)

    related_docs = list(cursor)
    results = []

    for doc in related_docs:
        rel_soc = doc.get("Related O*NET-SOC Code")
        rel_title = doc.get("Related Title")
        idx = doc.get("Index")

        enriched_doc = db.occupations_enriched.find_one({"onet_soc_code": rel_soc}) or {}
        salary = enriched_doc.get("market_median_salary_lpa")

        results.append({
            "onet_soc_code": rel_soc,
            "title": rel_title,
            "index": idx,
            "relatedness_tier": "Primary-Short",
            "market_median_salary_lpa": salary
        })

    return {
        "soc_code": soc_code,
        "count": len(results),
        "related_occupations": results
    }


@router.get("/roles/recommended")
async def get_recommended_roles(request: Request, session_id: str = Query(..., description="Session ID")):
    """
    E5+G: Unified IDF-weighted role recommendations across both catalogs.

    Scoring:
    1. Unified catalog: O*NET occupations_dict + Naukri market_roles_dict combined.
    2. IDF weights computed over the full unified catalog — rarer skills score higher.
    3. Market-source boost: roles from the market catalog get a boost proportional
       to their real posting volume (log scale). This implements Part G:
       real market evidence outweighs thin taxonomy-only matching.
    4. Title-domain boost: occupation title contains tech/data keywords (+0.05).
    5. Minimum overlap floor: >= 2 matched skills to be eligible.
    6. For default 'suggested roles' view: market-native entries with real posting
       volume are strongly preferred (directly addresses the 'feels academic' complaint).
    Zero LLM calls.
    """
    import math
    db = request.app.state.db
    occupations_dict = request.app.state.occupations_dict
    market_roles_dict = getattr(request.app.state, "market_roles_dict", {})
    skill_idf: dict = getattr(request.app.state, "skill_idf_weights", {})

    sess = get_session(session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    current_skills_raw = sess.get("current_skills", [])
    if not current_skills_raw:
        return {"session_id": session_id, "recommendations": [], "note": "No current skills found in session."}

    current_skills_lower = {sk.lower() for sk in current_skills_raw}

    tech_title_words = {
        "data", "software", "computer", "information", "web", "network",
        "database", "systems", "analytics", "cloud", "developer", "engineer",
        "scientist", "analyst", "security", "machine", "learning", "backend",
        "frontend", "full", "stack", "devops", "platform", "infrastructure",
    }

    # Catch-all cluster titles to exclude from recommendations
    # These are artifact clusters from the normalization (too broad to be meaningful)
    CATCHALL_TITLES = {
        "Analyst", "Developer", "Engineer", "Manager", "Lead",
        "Specialist", "Consultant", "Architect", "Scientist",
        "Intern", "Senior Manager",
    }

    MIN_OVERLAP = 2

    # Naukri clusters are the primary recommendation catalogue: their titles,
    # skills, and salaries originate in Indian job postings.  O*NET is a useful
    # fallback for a role search, but should not drown out the local market.
    market_roles = [(mid, doc, "market") for mid, doc in market_roles_dict.items()]
    onet_roles = [(soc, doc, "onet") for soc, doc in occupations_dict.items()]

    scored = []
    def score_catalog(all_roles):
      for role_id, occ, catalog in all_roles:
        required_raw = occ.get("combined_required_skills", [])
        if not required_raw:
            continue

        # Skip over-broad catch-all market clusters (artifact of title normalization)
        role_title = occ.get("title", "")
        if catalog == "market" and role_title in CATCHALL_TITLES:
            continue

        required_lower = {sk.lower() for sk in required_raw if isinstance(sk, str)}
        intersection = current_skills_lower & required_lower

        if len(intersection) < MIN_OVERLAP:
            continue

        # Use a weighted F-score instead of Jaccard.  It rewards both learner
        # coverage and role fit; raw Jaccard favours tiny/obscure skill lists.
        # The role-frequency map makes a match on a role's core skills count
        # more than an incidental skill in a handful of postings.
        frequencies = {str(k).lower(): float(v) for k, v in (occ.get("skill_frequencies") or {}).items()}
        weight = lambda skill: skill_idf.get(skill, math.log(2)) * (0.5 + frequencies.get(skill, 0.5))
        matched_weight = sum(weight(sk) for sk in intersection)
        learner_weight = sum(skill_idf.get(sk, math.log(2)) for sk in current_skills_lower)
        role_weight = sum(weight(sk) for sk in required_lower)
        recall = matched_weight / learner_weight if learner_weight else 0.0
        precision = matched_weight / role_weight if role_weight else 0.0
        match_score = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

        # Posting volume is a small, bounded tiebreaker.  It must never
        # overwhelm actual skill compatibility.
        posting_count = occ.get("market_posting_count") or 0
        market_boost = min(0.08, math.log1p(posting_count) / 100.0) if catalog == "market" else 0.0
        salary = occ.get("market_median_salary_lpa") or 0

        # Title relevance boost
        title_lower = occ.get("title", "").lower()
        title_is_tech = any(w in title_lower for w in tech_title_words)
        title_boost = 0.03 if title_is_tech else 0.0
        composite = match_score + market_boost + title_boost

        union = current_skills_lower | required_lower
        jaccard = len(intersection) / len(union) if union else 0.0

        scored.append({
            "role_id": role_id,
            "market_role_id": role_id if catalog == "market" else None,
            "onet_soc_code": occ.get("onet_soc_code"),
            "title": occ.get("title", role_id),
            "catalog_source": catalog,
            "overlap_count": len(intersection),
            "jaccard_score": round(jaccard, 4),
            "idf_weighted_score": round(match_score, 4),
            "match_score": round(match_score, 4),
            "composite_score": round(composite, 4),
            "market_posting_count": posting_count,
            "market_median_salary_lpa": salary or None,
            "matched_skills": sorted(intersection),
        })

    score_catalog(market_roles)
    # Only fall back to O*NET when local market data cannot provide a useful
    # choice. This prevents unrelated US taxonomy roles appearing above Indian
    # entry-level developer/data roles.
    if len(scored) < 4:
        score_catalog(onet_roles)

    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    return {
        "session_id": session_id,
        "skill_count": len(current_skills_lower),
        "min_overlap_floor": MIN_OVERLAP,
        "catalog_size": len(market_roles) + len(onet_roles),
        "recommendations": scored[:8],
    }
