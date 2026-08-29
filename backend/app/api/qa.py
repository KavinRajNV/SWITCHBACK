from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.api.session_store import get_session
from app.nlp import qa_engine
from app.models.schemas import LearnerProfile, GoalProfile, Milestone

router = APIRouter(prefix="/api/qa", tags=["Grounded Q&A Engine"])

KNOWN_QUESTIONS = {
    "why_this_skill",
    "how_long_will_this_take",
    "what_if_i_already_know_x",
    "show_free_alternatives",
    "why_this_role",
    "am_i_qualified_already",
    "what_skills_do_i_already_have",
    "explain_confidence_score"
}


class QARequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    question_id: str = Field(..., description="Canned question identifier")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional question-specific parameters")
    # Accepted at the top level too, matching the frontend api.ts contract.
    extra_skill: Optional[str] = Field(default=None, description="Skill argument for skill-scoped questions")
    milestone_index: Optional[int] = Field(default=None, description="0-based milestone index for why_this_skill")


def _resolve_skill(explicit: Optional[str], params: Dict[str, Any], stored_path: list, milestone_index: Optional[int]) -> Optional[str]:
    """Pick the skill a question is about: explicit arg > params > indexed milestone > first milestone."""
    if explicit:
        return explicit
    if params.get("skill"):
        return params["skill"]
    if milestone_index is not None and 0 <= milestone_index < len(stored_path):
        return stored_path[milestone_index]["skill"]
    if stored_path:
        return stored_path[0]["skill"]
    return None


@router.post("/ask")
async def ask_question(req_data: QARequest, request: Request):
    """
    Grounded Q&A dispatcher. Answers a known question_id using session state only —
    every number comes from Mongo, the skill graph, or the salary model.
    """
    if req_data.question_id not in KNOWN_QUESTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_id '{req_data.question_id}'. Known set: {sorted(list(KNOWN_QUESTIONS))}"
        )

    db = request.app.state.db
    graph = request.app.state.graph
    matcher = request.app.state.matcher

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    lp = LearnerProfile(**sess.get("learner_profile", {}))
    gp = GoalProfile(**sess.get("goal_profile", {}))
    target_soc = sess.get("target_occupation_soc_code")
    curr_skills = sess.get("current_skills", [])
    stored_path = sess.get("stored_path", [])

    params = req_data.params or {}
    q_id = req_data.question_id
    skill = _resolve_skill(req_data.extra_skill, params, stored_path, req_data.milestone_index)

    if q_id == "why_this_skill":
        if not skill:
            raise HTTPException(status_code=422, detail="Generate a learning path first — there's no milestone to explain yet.")
        ms_dict = next((m for m in stored_path if m["skill"].lower() == skill.lower()), None)
        ms = Milestone(**ms_dict) if ms_dict else None
        return qa_engine.answer_why_this_skill(skill, milestone=ms)

    elif q_id == "how_long_will_this_take":
        if not stored_path:
            raise HTTPException(status_code=422, detail="Generate a learning path first so there's a duration to estimate.")
        return qa_engine.answer_how_long_will_this_take(gp, path_length=len(stored_path))

    elif q_id == "what_if_i_already_know_x":
        explicit_skill = req_data.extra_skill or params.get("skill")
        if not explicit_skill:
            raise HTTPException(status_code=422, detail="This question needs a skill to test — pick one first.")
        if not target_soc:
            raise HTTPException(status_code=422, detail="Select a target role first.")
        return qa_engine.answer_what_if_i_already_know_x(
            explicit_skill, curr_skills, target_soc, graph=graph, matcher=matcher
        )

    elif q_id == "show_free_alternatives":
        if not skill:
            raise HTTPException(status_code=422, detail="Tell me which skill you want free courses for.")
        return qa_engine.answer_show_free_alternatives(skill, db=db)

    elif q_id == "why_this_role":
        if not target_soc:
            raise HTTPException(status_code=422, detail="Select a target role first.")
        return qa_engine.answer_why_this_role(target_soc, db=db)

    elif q_id == "am_i_qualified_already":
        if not target_soc:
            raise HTTPException(status_code=422, detail="Select a target role first.")
        return qa_engine.answer_am_i_qualified_already(curr_skills, target_soc, db=db)

    elif q_id == "what_skills_do_i_already_have":
        return qa_engine.answer_what_skills_do_i_already_have(lp)

    elif q_id == "explain_confidence_score":
        conf_skill = skill or (curr_skills[0] if curr_skills else None)
        if not conf_skill:
            raise HTTPException(status_code=422, detail="Add a skill to your profile first.")
        return qa_engine.answer_explain_confidence_score(conf_skill, lp)

    raise HTTPException(status_code=400, detail=f"Unhandled question_id '{q_id}'.")
