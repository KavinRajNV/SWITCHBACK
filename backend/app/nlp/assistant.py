"""Conversational layer over the deterministic Q&A engine.

The learner types a free-text question; ``classify_intent`` maps it onto one of
the eight grounded ``qa_engine`` functions (or a general status summary) using
keyword + fuzzy matching over the vocabulary. When ``NVIDIA_API_KEY`` is set the
model is asked *only* to pick the intent and the skill — never to write the
answer. Every number in every reply still comes from Mongo, the skill graph or
the salary model.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from rapidfuzz import fuzz

from app.config import settings
from app.models.schemas import LearnerProfile, GoalProfile, Milestone
from app.nlp import qa_engine


# intent_id -> trigger phrases. Order matters only for display; scoring is symmetric.
INTENTS: Dict[str, List[str]] = {
    "how_long_will_this_take": [
        "how long", "how many weeks", "how many months", "how much time",
        "duration", "when will i finish", "time to complete", "pace", "timeline",
    ],
    "what_if_i_already_know_x": [
        "what if i know", "what if i already know", "if i learn", "if i already knew",
        "already know", "skip a step", "shorten my path", "what if i add",
    ],
    "show_free_alternatives": [
        "free course", "free option", "free alternative", "without paying",
        "no cost", "cheaper", "free resource", "free way to learn",
    ],
    "why_this_role": [
        "why this role", "why should i target", "is this role worth", "salary for this role",
        "demand for this role", "why data scientist", "why that job",
    ],
    "am_i_qualified_already": [
        "am i qualified", "am i ready", "can i apply", "do i already qualify",
        "how close am i", "what's my gap", "skill gap", "qualified for this role",
    ],
    "what_skills_do_i_already_have": [
        "what skills do i have", "my current skills", "what do i already have",
        "list my skills", "skills on my profile",
    ],
    "explain_confidence_score": [
        "confidence score", "how is my score", "why is my confidence", "evidence score",
        "how was my score", "explain my rating",
    ],
    "why_this_skill": [
        "why this skill", "why do i need", "why is this recommended", "reason for this step",
        "why learn", "why is", "purpose of this milestone",
    ],
}

_SKILL_SCOPED = {
    "what_if_i_already_know_x", "show_free_alternatives",
    "explain_confidence_score", "why_this_skill",
}

_RATIONALE = {
    "how_long_will_this_take": "a question about how long the path takes",
    "what_if_i_already_know_x": "a what-if about adding a skill",
    "show_free_alternatives": "a request for free learning options",
    "why_this_role": "a question about why this role",
    "am_i_qualified_already": "a question about your gap to the role",
    "what_skills_do_i_already_have": "a question about your current skills",
    "explain_confidence_score": "a question about a confidence score",
    "why_this_skill": "a question about why a skill is on your path",
    "general": "a general question about your plan",
}


def _score_intent(text_lc: str, phrases: List[str]) -> float:
    best = 0.0
    for p in phrases:
        if p in text_lc:
            best = max(best, 100.0 + len(p))          # exact substring wins decisively
        else:
            best = max(best, fuzz.partial_ratio(p, text_lc))
    return best


def _extract_skill(text: str, matcher: Any) -> Optional[str]:
    if matcher is None:
        return None
    matches = matcher.extract_skills(text)
    if matches:
        # Longest matched span first (already sorted by the matcher); take that skill.
        return matches[0].skill
    direct = matcher.match_direct(text.strip())
    return direct.skill if direct else None


def classify_intent(text: str, matcher: Any = None) -> Tuple[str, Dict[str, Any]]:
    """Return ``(intent_id, params)``. ``intent_id`` is ``"general"`` when nothing scores well."""
    text_lc = (text or "").lower().strip()
    if not text_lc:
        return "general", {}

    # "what next / what should I do / where do I stand" -> the grounded status summary.
    if re.search(r"\b(what('s| is)? next|what now|what should i do|where do i stand|status|overview|next step)\b", text_lc):
        return "general", {}

    scored = sorted(
        ((iid, _score_intent(text_lc, phrases)) for iid, phrases in INTENTS.items()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    top_intent, top_score = scored[0]

    skill = _extract_skill(text, matcher)

    # A bare "why ...?" with a skill in it is about that skill.
    if skill and top_score < 80 and re.search(r"\bwhy\b", text_lc):
        return "why_this_skill", {"skill": skill}

    # Below this, keyword/fuzzy evidence is too weak to trust.
    if top_score < 70:
        return "general", {"skill": skill} if skill else {}

    params: Dict[str, Any] = {}
    if top_intent in _SKILL_SCOPED and skill:
        params["skill"] = skill
    return top_intent, params


# --------------------------------------------------------------------------- #
# Optional NVIDIA intent assist (never writes answer text)
# --------------------------------------------------------------------------- #
_NVIDIA_SYS = (
    "You route a learner's question to one label. Reply with JSON only: "
    '{"intent": <one of %s or "general">, "skill": <a skill name mentioned, or null>}. '
    "Do not answer the question."
)


def _nvidia_intent(text: str) -> Optional[Dict[str, Any]]:
    if not settings.NVIDIA_API_KEY:
        return None
    labels = list(INTENTS.keys())
    payload = {
        "model": settings.NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": _NVIDIA_SYS % labels},
            {"role": "user", "content": text.strip()[:2000]},
        ],
        "temperature": 0,
        "max_tokens": 120,
        "stream": False,
    }
    req = urlrequest.Request(
        f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=settings.NVIDIA_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            return None
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.S | re.I)
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            return None
        obj = json.loads(content[start:end + 1])
        intent = obj.get("intent")
        if intent in INTENTS or intent == "general":
            out: Dict[str, Any] = {"intent": intent}
            if isinstance(obj.get("skill"), str) and obj["skill"].strip():
                out["skill"] = obj["skill"].strip()
            return out
    except Exception as exc:  # optional assist — never break the request
        print(f"[assistant] NVIDIA intent assist unavailable: {exc}")
    return None


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def _general_summary(sess: Dict[str, Any], salary_model: Any, manifest: Any) -> Tuple[str, Dict[str, Any]]:
    from app.ml.features import vectorize

    curr = sess.get("current_skills", []) or []
    stored_path = sess.get("stored_path", []) or []
    gp = sess.get("goal_profile", {}) or {}
    target = gp.get("target_role") or sess.get("target_occupation_soc_code")
    completed = len(sess.get("completed_milestones", []) or [])

    sal = None
    if salary_model is not None and manifest is not None and curr:
        try:
            sal = round(float(salary_model.predict(vectorize(set(curr), manifest=manifest).reshape(1, -1))[0]), 2)
        except Exception:
            sal = None

    bits = [f"You have {len(curr)} skill(s) on your profile"]
    if target:
        bits.append(f"aiming for {target}")
    if stored_path:
        bits.append(f"{len(stored_path)} milestone(s) remain (next: {stored_path[0]['skill']})")
    if completed:
        bits.append(f"{completed} completed")
    if sal is not None:
        bits.append(f"current model-predicted salary ~₹{sal} LPA")
    text = ("Here's where you stand: " + "; ".join(bits) + ". "
            "Ask me things like \"how long will this take?\", \"is there a free course for Docker?\", "
            "or \"am I qualified yet?\".")
    return text, {"current_skills": curr, "remaining_milestones": len(stored_path), "completed": completed,
                  "predicted_salary_lpa": sal, "target": target}


def route(
    message: str,
    sess: Dict[str, Any],
    *,
    db: Any,
    graph: Any,
    matcher: Any,
    salary_model: Any = None,
    shap_explainer: Any = None,
    manifest: Any = None,
) -> Dict[str, Any]:
    """Classify ``message`` and answer it from grounded data. Returns a dict for the API layer."""
    intent, params = classify_intent(message, matcher)

    # LLM assist is a fallback only: pay its latency when the keyword classifier
    # was not confident, never on the common cases it already nails.
    if intent == "general":
        ai = _nvidia_intent(message)
        if ai and ai["intent"] != "general":
            intent = ai["intent"]
            if ai.get("skill"):
                params = {"skill": ai["skill"]} if intent in _SKILL_SCOPED else params
            elif not params.get("skill") and intent in _SKILL_SCOPED:
                # model chose a skill-scoped intent but named no skill — try the matcher again
                s = _extract_skill(message, matcher)
                if s:
                    params = {"skill": s}

    lp = LearnerProfile(**sess.get("learner_profile", {}))
    gp = GoalProfile(**sess.get("goal_profile", {}))
    target_soc = sess.get("target_occupation_soc_code")
    curr_skills = sess.get("current_skills", []) or []
    stored_path = sess.get("stored_path", []) or []
    skill = params.get("skill")

    rationale = f"I read this as {_RATIONALE.get(intent, 'a general question')}."
    qa = None
    note = None

    if intent == "why_this_skill":
        target_skill = skill or (stored_path[0]["skill"] if stored_path else None)
        if not target_skill:
            note = "Generate a learning path first and I can explain any milestone on it."
        else:
            ms_dict = next((m for m in stored_path if m["skill"].lower() == target_skill.lower()), None)
            qa = qa_engine.answer_why_this_skill(target_skill, milestone=Milestone(**ms_dict) if ms_dict else None)

    elif intent == "how_long_will_this_take":
        if not stored_path:
            note = "Pick a target role and generate a path, then I can estimate the time."
        else:
            qa = qa_engine.answer_how_long_will_this_take(gp, path_length=len(stored_path))

    elif intent == "what_if_i_already_know_x":
        if not skill:
            note = "Tell me which skill to test, e.g. \"what if I already know AWS?\"."
        elif not target_soc:
            note = "Choose a target role first so I can recompute the path."
        else:
            qa = qa_engine.answer_what_if_i_already_know_x(skill, curr_skills, target_soc, graph=graph, matcher=matcher)

    elif intent == "show_free_alternatives":
        if not skill:
            note = "Which skill do you want free courses for?"
        else:
            qa = qa_engine.answer_show_free_alternatives(skill, db=db)

    elif intent == "why_this_role":
        if not target_soc:
            note = "Select a target role first."
        else:
            qa = qa_engine.answer_why_this_role(target_soc, db=db)

    elif intent == "am_i_qualified_already":
        if not target_soc:
            note = "Select a target role first and I'll measure your gap."
        else:
            qa = qa_engine.answer_am_i_qualified_already(curr_skills, target_soc, db=db)

    elif intent == "what_skills_do_i_already_have":
        qa = qa_engine.answer_what_skills_do_i_already_have(lp)

    elif intent == "explain_confidence_score":
        conf_skill = skill or (curr_skills[0] if curr_skills else None)
        if not conf_skill:
            note = "Add a skill to your profile first."
        else:
            qa = qa_engine.answer_explain_confidence_score(conf_skill, lp)

    if qa is not None:
        return {
            "intent": intent,
            "rationale": rationale,
            "reply": qa.answer_text,
            "structured_payload": qa.structured_payload,
        }

    if note is not None:
        return {"intent": intent, "rationale": rationale, "reply": note, "structured_payload": None}

    text, payload = _general_summary(sess, salary_model, manifest)
    return {"intent": "general", "rationale": rationale, "reply": text, "structured_payload": payload}
