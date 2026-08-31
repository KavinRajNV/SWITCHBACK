from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query

from app.api.session_store import get_session
from app.ml.features import vectorize

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("")
async def get_dashboard(request: Request, session_id: str = Query(..., description="Session ID")):
    """
    Aggregates profile summary, completion progress %, current elevation profile,
    next action milestone, and recent activity streak.
    """
    db = request.app.state.db
    salary_model = request.app.state.salary_model
    manifest = request.app.state.manifest
    occupations_dict = request.app.state.occupations_dict

    sess = get_session(session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    lp = sess.get("learner_profile", {})
    curr_skills = set(sess.get("current_skills", []))
    target_soc = sess.get("target_occupation_soc_code")
    completed_log = sess.get("completed_milestones", [])
    stored_path = sess.get("stored_path", [])

    occ = None
    if target_soc:
        occ = occupations_dict.get(target_soc) or db.occupations_enriched.find_one({"onet_soc_code": target_soc})

    # No fabricated fallback: if the learner hasn't picked a role yet, say so.
    target_title = occ.get("title") if occ else (target_soc or None)
    target_median_salary = occ.get("market_median_salary_lpa") if occ else None

    # Calculate progress %
    completed_count = len(completed_log)
    total_path_milestones = len(stored_path) + completed_count
    progress_pct = round((completed_count / total_path_milestones * 100.0), 1) if total_path_milestones > 0 else 0.0

    # Current predicted salary
    vec = vectorize(curr_skills, manifest=manifest)
    current_predicted_salary_lpa = float(salary_model.predict(vec.reshape(1, -1))[0])

    # Next action milestone
    next_action = stored_path[0] if stored_path else None

    # Elevation Profile
    elevation_profile = []
    accumulated_skills = set(curr_skills)
    
    vec0 = vectorize(accumulated_skills, manifest=manifest)
    sal0 = float(salary_model.predict(vec0.reshape(1, -1))[0])
    max_sal = sal0
    
    elevation_profile.append({
        "step": 0,
        "skill": "Baseline (Current Skills)",
        "raw_predicted_salary_lpa": round(sal0, 2),
        "cumulative_predicted_salary_lpa": round(sal0, 2)
    })

    if stored_path:
        for ms in stored_path:
            accumulated_skills.add(ms["skill"])
            vec_k = vectorize(accumulated_skills, manifest=manifest)
            sal_k = float(salary_model.predict(vec_k.reshape(1, -1))[0])
            # Ensure the graph goes up by at least 0.25 for each skill to show contribution
            max_sal = max(max_sal + 0.25, sal_k)
            elevation_profile.append({
                "step": ms["step_number"],
                "skill": ms["skill"],
                "raw_predicted_salary_lpa": round(sal_k, 2),
                "cumulative_predicted_salary_lpa": round(max_sal, 2)
            })

    # Recent activity streak
    recent_activities = sorted(completed_log, key=lambda x: x.get("completed_at", ""), reverse=True)[:5]

    return {
        "session_id": session_id,
        "profile_summary": {
            "total_acquired_skills": len(curr_skills),
            "experience_years_est": lp.get("experience_years_est"),
            "current_predicted_salary_lpa": round(current_predicted_salary_lpa, 2)
        },
        "target_role": {
            "onet_soc_code": target_soc,
            "title": target_title,
            "market_median_salary_lpa": target_median_salary
        },
        "progress": {
            "completed_milestones_count": completed_count,
            "remaining_milestones_count": len(stored_path),
            "progress_percentage": progress_pct
        },
        "next_action_milestone": next_action,
        "elevation_profile": elevation_profile,
        "recent_activities": recent_activities
    }
