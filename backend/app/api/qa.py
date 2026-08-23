from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.api.session_store import get_session
from app.nlp import qa_engine
from app.models.schemas import LearnerProfile, GoalProfile, Milestone

router = APIRouter(prefix="/api/qa", tags=["Constrained Q&A Engine"])

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

@router.post("/ask")
async def ask_question(req_data: QARequest, request: Request):
    """
    Constrained Q&A engine dispatcher. Answers canned question_id using session state.
    """
    if req_data.question_id not in KNOWN_QUESTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown question_id '{req_data.question_id}'. Known set: {sorted(list(KNOWN_QUESTIONS))}"
        )

    db = request.app.state.db
    graph = request.app.state.graph

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    lp = LearnerProfile(**sess.get("learner_profile", {}))
    gp = GoalProfile(**sess.get("goal_profile", {}))
    target_soc = sess.get("target_occupation_soc_code", "15-2051.00")
    curr_skills = sess.get("current_skills", [])
    stored_path = sess.get("stored_path", [])

    params = req_data.params or {}
    q_id = req_data.question_id

    if q_id == "why_this_skill":
        skill = params.get("skill") or (stored_path[0]["skill"] if stored_path else "Python")
        ms_dict = next((m for m in stored_path if m["skill"].lower() == skill.lower()), None)
        ms = Milestone(**ms_dict) if ms_dict else None
        return qa_engine.answer_why_this_skill(skill, milestone=ms)

    elif q_id == "how_long_will_this_take":
        path_len = len(stored_path) if stored_path else 10
        return qa_engine.answer_how_long_will_this_take(gp, path_length=path_len)

    elif q_id == "what_if_i_already_know_x":
        extra_skill = params.get("skill") or "AWS"
        return qa_engine.answer_what_if_i_already_know_x(extra_skill, curr_skills, target_soc, graph=graph)

    elif q_id == "show_free_alternatives":
        skill = params.get("skill") or (stored_path[0]["skill"] if stored_path else "Python")
        return qa_engine.answer_show_free_alternatives(skill, db=db)

    elif q_id == "why_this_role":
        return qa_engine.answer_why_this_role(target_soc, db=db)

    elif q_id == "am_i_qualified_already":
        return qa_engine.answer_am_i_qualified_already(curr_skills, target_soc, db=db)

    elif q_id == "what_skills_do_i_already_have":
        return qa_engine.answer_what_skills_do_i_already_have(lp)

    elif q_id == "explain_confidence_score":
        skill = params.get("skill") or (curr_skills[0] if curr_skills else "Python")
        return qa_engine.answer_explain_confidence_score(skill, lp)

    raise HTTPException(status_code=400, detail=f"Unhandled question_id '{q_id}'.")
