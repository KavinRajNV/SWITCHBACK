from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.api.session_store import get_session, update_session
from app.ml.path_sequencer import generate_path
from app.ml.features import vectorize
from app.ml.explain import get_skill_contributions
from app.nlp.explain_templates import explain_gap_skill, explain_owned_skill
from app.api.youtube_service import fetch_youtube_videos
from app.ml.course_ranking import rank_courses

router = APIRouter(prefix="/api/path", tags=["Path Generation"])

class PathGenerateRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    target_occupation_soc_code: Optional[str] = Field(default=None, description="Optional target O*NET SOC code")
    target_market_role_id: Optional[str] = Field(default=None, description="Optional Indian market-role identifier")

@router.post("/generate")
async def generate_learning_path(req_data: PathGenerateRequest, request: Request):
    """
    Generates dynamic learning path with gap explanations, course offerings (free/paid split),
    owned SHAP explanations, and model-predicted salary elevation profile.
    """
    db = request.app.state.db
    graph = request.app.state.graph
    salary_model = request.app.state.salary_model
    shap_explainer = request.app.state.shap_explainer
    manifest = request.app.state.manifest
    occupations_dict = request.app.state.occupations_dict

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    target_soc = req_data.target_occupation_soc_code or sess.get("target_occupation_soc_code")
    if not target_soc:
        # Fallback to Data Scientist default if none specified
        target_soc = "15-2051.00"

    market_role_id = req_data.target_market_role_id
    market_roles_dict = getattr(request.app.state, "market_roles_dict", {})
    occ = market_roles_dict.get(market_role_id) if market_role_id else occupations_dict.get(target_soc)
    if not occ:
        occ = db.occupations_enriched.find_one({"onet_soc_code": target_soc})
        if not occ:
            raise HTTPException(status_code=404, detail=f"Target SOC code '{target_soc}' not found.")

    target_title = occ.get("title", target_soc)
    current_skills = set(sess.get("current_skills", []))

    # 1. Generate path using Dijkstra sequencer
    path_milestones_raw = generate_path(
        current_skills, target_soc, graph,
        occupations_enriched=occ if market_role_id else None,
    )

    # 2. Owned skill SHAP contributions
    current_vector = vectorize(current_skills, manifest=manifest)
    shap_dict = get_skill_contributions(current_vector, user_skills=current_skills, manifest=manifest, shap_explainer=shap_explainer)
    owned_explanations = [
        {
            "skill": sk,
            "contribution_lpa": contrib_val,
            "explanation": explain_owned_skill(sk, contrib_val)
        }
        for sk, contrib_val in shap_dict.items()
    ]

    # Global SHAP top feature ranks map
    global_shap_ranks = {
        name: i + 1 for i, name in enumerate(manifest.get("feature_names", []))
    }

    # 3. Enrich path milestones with explanations and course offerings
    enriched_milestones = []
    for ms in path_milestones_raw:
        sk = ms["skill"]
        rank = global_shap_ranks.get(sk, 45)
        gap_exp = explain_gap_skill(sk, rank, 0.25)

        # Query top 10 courses split into free and paid; P3: filtered by this milestone's skill

        matched_courses = list(db.courses.find(
            {"skills_matched": sk},
            {"title": 1, "headline": 1, "source": 1, "url": 1, "is_paid": 1, "price": 1,
             "rating": 1, "num_reviews": 1, "num_subscribers": 1, "category": 1}
        ).limit(250))

        free_candidates = [c for c in matched_courses
                           if (c.get("is_paid") is False or c.get("price") == 0)]
        paid_candidates = [c for c in matched_courses
                           if c.get("is_paid") is True and c.get("price") != 0]
        free_courses = [
            {"title": c.get("title"), "source": c.get("source"), "url": c.get("url", "#"), "rating": c.get("rating"), "is_paid": False}
            for c in rank_courses(free_candidates, sk)
        ]

        # P4: Append YouTube free videos (cached, quota-safe)
        try:
            yt_videos = await fetch_youtube_videos(sk, db)
            for v in yt_videos:
                free_courses.append({
                    "title": v["title"],
                    "source": v.get("source", "YouTube (Free)"),
                    "url": v["url"],
                    "rating": None,
                    "is_paid": False,
                })
        except Exception as yt_err:
            pass  # YouTube failure is non-fatal

        paid_courses = [
            {"title": c.get("title"), "source": c.get("source"), "url": c.get("url", "#"), "price": c.get("price"), "rating": c.get("rating")}
            for c in rank_courses(paid_candidates, sk)
        ]


        enriched_milestones.append({
            "step_number": ms["step_number"],
            "skill": sk,
            "cost": ms["cost"],
            "reachable_via": ms["reachable_via"],
            "is_essential": ms.get("is_essential", True),
            "explanation": gap_exp,
            "free_courses": free_courses,
            "paid_courses": paid_courses
        })

    # 4. Elevation Profile (Salary prediction trajectory)
    elevation_profile = []
    accumulated_skills = set(current_skills)

    # Step 0: Baseline current skills
    vec0 = vectorize(accumulated_skills, manifest=manifest)
    sal0 = float(salary_model.predict(vec0.reshape(1, -1))[0])
    elevation_profile.append({
        "step": 0,
        "skill": "Baseline (Current Skills)",
        "cumulative_predicted_salary_lpa": round(sal0, 2)
    })

    # Step 1..N: Accumulate milestone skills
    for ms in path_milestones_raw:
        accumulated_skills.add(ms["skill"])
        vec_k = vectorize(accumulated_skills, manifest=manifest)
        sal_k = float(salary_model.predict(vec_k.reshape(1, -1))[0])
        elevation_profile.append({
            "step": ms["step_number"],
            "skill": ms["skill"],
            "cumulative_predicted_salary_lpa": round(sal_k, 2)
        })

    # Update session store
    update_session(req_data.session_id, {
        "target_occupation_soc_code": target_soc,
        "target_market_role_id": market_role_id,
        # Persist this small snapshot so progress recomputation remains tied to
        # the selected Indian role rather than its broad O*NET cross-reference.
        "target_role_required_skills": occ.get("combined_required_skills", []),
        "stored_path": enriched_milestones
    }, db=db)

    is_fully_qualified = len(path_milestones_raw) == 0

    return {
        "session_id": req_data.session_id,
        "target_occupation_soc_code": target_soc,
        "target_market_role_id": market_role_id,
        "target_occupation_title": target_title,
        "is_fully_qualified": is_fully_qualified,
        "path_length": len(enriched_milestones),
        "milestones": enriched_milestones,
        "owned_skill_contributions": owned_explanations,
        "elevation_profile": elevation_profile
    }
