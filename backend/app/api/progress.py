from datetime import datetime
from typing import Optional, Literal, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.api.session_store import get_session, update_session
from app.models.schemas import SkillEvidence, LearnerProfile
from app.ml.path_sequencer import generate_path

router = APIRouter(prefix="/api/progress", tags=["Progress & Feedback Loop"])

EVIDENCE_CONFIDENCE_MAP = {
    "self_report": 6,
    "project_log": 7,
    "github_verified": 9
}

class MilestoneCompleteRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    skill: str = Field(..., description="Milestone skill completed")
    evidence_type: Literal["self_report", "project_log", "github_verified"] = Field(..., description="Evidence verification tier")
    project_description: Optional[str] = Field(default=None, description="Optional project log text description")

@router.post("/complete-milestone")
async def complete_milestone(req_data: MilestoneCompleteRequest, request: Request):
    """
    Adaptive progress feedback loop. Marks a milestone complete, updates confidence evidence tier,
    adds skill to learner frontier, recomputes Dijkstra path, and returns exact milestones saved.
    """
    db = request.app.state.db
    graph = request.app.state.graph
    matcher = request.app.state.matcher

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    # Canonicalize skill
    d = matcher.match_direct(req_data.skill)
    canon_skill = d.skill if d else req_data.skill.strip()

    # 1. Update current_skills
    curr_skills = set(sess.get("current_skills", []))
    curr_skills.add(canon_skill)

    # 2. Assign confidence tier
    conf = EVIDENCE_CONFIDENCE_MAP.get(req_data.evidence_type, 6)

    # Update LearnerProfile extracted skills
    lp_dict = sess.get("learner_profile", {})
    extracted_skills = lp_dict.get("extracted_skills", [])
    skill_map = {e["skill"]: e for e in extracted_skills}

    if canon_skill in skill_map:
        skill_map[canon_skill]["confidence"] = max(skill_map[canon_skill]["confidence"], conf)
        if req_data.evidence_type.upper() not in skill_map[canon_skill]["found_in_sections"]:
            skill_map[canon_skill]["found_in_sections"].append(req_data.evidence_type.upper())
    else:
        new_ev = SkillEvidence(
            skill=canon_skill,
            category="Acquired",
            confidence=conf,
            mention_count=1,
            found_in_sections=[req_data.evidence_type.upper()]
        )
        extracted_skills.append(new_ev.model_dump())

    lp_dict["extracted_skills"] = extracted_skills

    # 3. Log completed milestone with timestamp
    completed_log = sess.get("completed_milestones", [])
    now_iso = datetime.now().isoformat()
    completed_log.append({
        "skill": canon_skill,
        "evidence_type": req_data.evidence_type,
        "confidence": conf,
        "completed_at": now_iso,
        "project_description": req_data.project_description
    })

    # 4. Recompute path against target occupation
    old_path = sess.get("stored_path", [])
    old_len = len(old_path)
    target_soc = sess.get("target_occupation_soc_code", "15-2051.00")

    selected_market_role = sess.get("target_market_role_id")
    required_skills = sess.get("target_role_required_skills")
    market_occ = (
        {"combined_required_skills": required_skills, "taxonomy_required_skills": []}
        if selected_market_role and required_skills else None
    )
    new_path_raw = generate_path(curr_skills, target_soc, graph, occupations_enriched=market_occ)
    new_len = len(new_path_raw)
    milestones_saved = max(old_len - new_len, 0)

    # Re-package simple milestone dicts for updated stored_path
    new_stored_path = [
        {
            "step_number": ms["step_number"],
            "skill": ms["skill"],
            "cost": ms["cost"],
            "reachable_via": ms["reachable_via"],
            "is_essential": ms.get("is_essential", True)
        }
        for ms in new_path_raw
    ]

    update_session(req_data.session_id, {
        "current_skills": list(curr_skills),
        "learner_profile": lp_dict,
        "completed_milestones": completed_log,
        "stored_path": new_stored_path
    }, db=db)

    return {
        "session_id": req_data.session_id,
        "completed_skill": canon_skill,
        "evidence_type": req_data.evidence_type,
        "confidence_assigned": conf,
        "milestones_saved": milestones_saved,
        "previous_path_length": old_len,
        "new_path_length": new_len,
        "remaining_milestones": new_stored_path,  # key expected by PathScreen.tsx
        "updated_profile": lp_dict
    }
