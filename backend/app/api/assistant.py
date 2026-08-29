from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.session_store import get_session
from app.nlp import assistant

router = APIRouter(prefix="/api/assistant", tags=["Conversational Assistant"])

# Human-readable labels for the suggested-prompt chips.
SUGGESTION_LABELS: Dict[str, str] = {
    "how_long_will_this_take": "How long will this path take?",
    "am_i_qualified_already": "Am I qualified for this role yet?",
    "why_this_role": "Why target this role?",
    "what_skills_do_i_already_have": "What skills do I already have?",
    "show_free_alternatives": "Any free courses for my next skill?",
    "why_this_skill": "Why is my next skill on the path?",
}


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    message: str = Field(..., min_length=1, description="Free-text learner question")
    history: Optional[List[ChatTurn]] = Field(default_factory=list)


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    """
    Free-text learner question -> grounded answer.

    The message is classified onto one of the deterministic Q&A functions (or a
    general status summary); every figure in the reply comes from Mongo, the
    skill graph, or the salary model. The response also carries the detected
    intent, a one-line rationale, and up to three suggested follow-up prompts.
    """
    state = request.app.state
    sess = get_session(req.session_id, db=state.db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found.")

    result = assistant.route(
        req.message,
        sess,
        db=state.db,
        graph=state.graph,
        matcher=state.matcher,
        salary_model=getattr(state, "salary_model", None),
        shap_explainer=getattr(state, "shap_explainer", None),
        manifest=getattr(state, "manifest", None),
    )

    used = {t.content for t in (req.history or [])} | {result["intent"]}
    suggestions = [label for iid, label in SUGGESTION_LABELS.items() if iid not in used][:3]

    return {
        "session_id": req.session_id,
        "intent": result["intent"],
        "rationale": result["rationale"],
        "reply": result["reply"],
        "structured_payload": result.get("structured_payload"),
        "suggestions": suggestions,
    }
