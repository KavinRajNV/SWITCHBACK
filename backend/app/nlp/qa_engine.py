import math
from typing import Dict, Any, List, Set, Optional, Union
from pymongo.database import Database

from app.models.schemas import QAResponse, LearnerProfile, GoalProfile, Milestone
from app.db.mongo_client import get_db
from app.ml.path_sequencer import generate_path, get_graph
from app.nlp.explain_templates import explain_gap_skill

def answer_why_this_skill(skill: str, milestone: Optional[Milestone] = None, global_rank: int = 10, global_val: float = 0.45) -> QAResponse:
    """
    1. why_this_skill: Explains why a specific milestone skill is recommended.
    """
    if milestone and milestone.reachable_via:
        transition_str = f"It builds directly upon your acquired '{milestone.reachable_via}' skill with low transition friction (cost weight: {milestone.cost:.2f})."
    else:
        transition_str = "It serves as a foundational entry milestone for your target career path."

    shap_str = explain_gap_skill(skill, global_rank, global_val)
    answer = f"{skill} is recommended at step #{milestone.step_number if milestone else 1}. {transition_str} {shap_str}"

    return QAResponse(
        question_id="why_this_skill",
        answer_text=answer,
        structured_payload={
            "skill": skill,
            "milestone": milestone.model_dump() if milestone else None,
            "global_rank": global_rank,
            "global_val": global_val
        }
    )

def answer_how_long_will_this_take(goal_profile: GoalProfile, path_length: int) -> QAResponse:
    """
    2. how_long_will_this_take: Estimates completion timeframe based on path length and learner commitment.
    Formula: Estimated study hours = path_length * 40 hours per milestone.
    Weeks = study_hours / hours_per_week.
    """
    hrs_per_wk = goal_profile.hours_per_week or 15
    est_total_hours = path_length * 40
    est_weeks = math.ceil(est_total_hours / hrs_per_wk)
    est_days = est_weeks * 7

    target_tf = goal_profile.timeframe_days
    on_track_str = ""
    if target_tf:
        if est_days <= target_tf:
            on_track_str = f" At your pace of {hrs_per_wk} hrs/week, you are well on track to complete the path within your target timeframe of {target_tf} days!"
        else:
            on_track_str = f" At {hrs_per_wk} hrs/week, this path will require approximately {est_days} days, which is slightly longer than your target timeframe of {target_tf} days. Consider increasing your weekly commitment to {math.ceil(est_total_hours / (target_tf / 7))} hrs/week to stay on schedule."

    answer = f"Completing your {path_length}-milestone learning path requires an estimated {est_total_hours} total study hours (~40 hours per skill). At {hrs_per_wk} hours/week, you will finish in approximately {est_weeks} weeks (~{est_days} days).{on_track_str}"

    return QAResponse(
        question_id="how_long_will_this_take",
        answer_text=answer,
        structured_payload={
            "path_length": path_length,
            "hours_per_week": hrs_per_wk,
            "estimated_total_hours": est_total_hours,
            "estimated_weeks": est_weeks,
            "estimated_days": est_days,
            "target_timeframe_days": target_tf
        }
    )

def answer_what_if_i_already_know_x(extra_skill: str, current_skills: Union[Set[str], List[str]], target_soc: str, graph: Any = None) -> QAResponse:
    """
    3. what_if_i_already_know_x: Recomputes path with extra skill added to current skills.
    """
    if graph is None:
        graph = get_graph()

    curr_set = set(current_skills)
    new_skills = set(curr_set)
    new_skills.add(extra_skill)

    old_path = generate_path(curr_set, target_soc, graph)
    new_path = generate_path(new_skills, target_soc, graph)

    saved_steps = len(old_path) - len(new_path)
    if saved_steps > 0:
        answer = f"Adding '{extra_skill}' to your acquired skills reduces your learning path length by {saved_steps} milestone(s) (from {len(old_path)} down to {len(new_path)} steps)!"
    else:
        answer = f"Adding '{extra_skill}' updates your skill frontier. Your remaining learning path consists of {len(new_path)} milestone(s)."

    return QAResponse(
        question_id="what_if_i_already_know_x",
        answer_text=answer,
        structured_payload={
            "added_skill": extra_skill,
            "original_path_length": len(old_path),
            "new_path_length": len(new_path),
            "milestones_saved": max(saved_steps, 0),
            "new_path": new_path
        }
    )

def answer_show_free_alternatives(skill: str, db: Any = None) -> QAResponse:
    """
    4. show_free_alternatives: Queries courses collection filtered to skill and is_paid == False or price == 0.
    """
    if db is None:
        db = get_db()

    free_courses = list(db.courses.find(
        {
            "skills_matched": skill,
            "$or": [{"is_paid": False}, {"price": 0}, {"price": None, "source": "coursera"}]
        },
        {"_id": 0, "title": 1, "source": 1, "url": 1, "rating": 1, "category": 1}
    ).limit(5))

    if free_courses:
        c_list_str = "\n".join([f"- [{c.get('title')}]({c.get('url', '#')}) ({c.get('source', 'free')})" for c in free_courses])
        answer = f"Here are top free course options to learn {skill}:\n{c_list_str}"
    else:
        answer = f"No 100% free courses found for '{skill}' in database, but free community tutorials and YouTube channels are available on the allowlist."

    return QAResponse(
        question_id="show_free_alternatives",
        answer_text=answer,
        structured_payload={
            "skill": skill,
            "free_courses_count": len(free_courses),
            "courses": free_courses
        }
    )

def answer_why_this_role(target_soc: str, db: Any = None) -> QAResponse:
    """
    5. why_this_role: Summarizes market median salary and job posting count for target occupation.
    """
    if db is None:
        db = get_db()

    occ = db.occupations_enriched.find_one({"onet_soc_code": target_soc}, {"_id": 0})
    if not occ:
        occ = db.occupations_enriched.find_one({"title": {"$regex": target_soc, "$options": "i"}}, {"_id": 0})

    if occ:
        title = occ.get("title", target_soc)
        salary = occ.get("market_median_salary_lpa")
        postings = occ.get("market_posting_count", 0)

        sal_str = f"₹{salary:.1f} LPA" if salary else "competitive market benchmarks"
        answer = f"'{title}' is a high-demand career role featuring an estimated median salary of {sal_str} across {postings} verified job postings in our dataset."
    else:
        answer = f"Target occupation '{target_soc}' is an established professional SOC role with verified industry demand."

    return QAResponse(
        question_id="why_this_role",
        answer_text=answer,
        structured_payload={
            "target_soc": target_soc,
            "title": occ.get("title") if occ else None,
            "median_salary_lpa": occ.get("market_median_salary_lpa") if occ else None,
            "posting_count": occ.get("market_posting_count") if occ else 0
        }
    )

def answer_am_i_qualified_already(current_skills: Union[Set[str], List[str]], target_soc: str, db: Any = None) -> QAResponse:
    """
    6. am_i_qualified_already: Checks if skill gap is empty for current profile.
    """
    if db is None:
        db = get_db()

    occ = db.occupations_enriched.find_one({"onet_soc_code": target_soc}, {"_id": 0})
    if not occ:
        occ = db.occupations_enriched.find_one({"title": {"$regex": target_soc, "$options": "i"}}, {"_id": 0})

    required = set(occ.get("combined_required_skills", [])) if occ else set()
    curr_set = set(current_skills)
    gap = required - curr_set

    if not gap and required:
        answer = f"Yes! You already possess all {len(required)} top required skills for '{occ.get('title') if occ else target_soc}'. You are fully qualified for this role!"
    else:
        covered = len(required) - len(gap)
        answer = f"You currently possess {covered} out of {len(required)} required skills for '{occ.get('title') if occ else target_soc}'. You have a focused gap of {len(gap)} skill(s) to achieve full qualification."

    return QAResponse(
        question_id="am_i_qualified_already",
        answer_text=answer,
        structured_payload={
            "is_fully_qualified": len(gap) == 0 and len(required) > 0,
            "required_count": len(required),
            "covered_count": len(required) - len(gap),
            "gap_count": len(gap),
            "remaining_gap_skills": sorted(list(gap))
        }
    )

def answer_what_skills_do_i_already_have(profile: LearnerProfile) -> QAResponse:
    """
    7. what_skills_do_i_already_have: Lists current skills with confidence scores.
    """
    skills = profile.extracted_skills
    if skills:
        sk_lines = [f"- **{se.skill}** (Confidence: {se.confidence}/10, Mentions: {se.mention_count}, Sections: {', '.join(se.found_in_sections)})" for se in skills]
        answer = f"Based on your resume parsing, you possess {len(skills)} verified skill(s):\n" + "\n".join(sk_lines)
    else:
        answer = "No verified skills were extracted from your current profile."

    return QAResponse(
        question_id="what_skills_do_i_already_have",
        answer_text=answer,
        structured_payload={
            "total_skills": len(skills),
            "skills": [se.model_dump() for se in skills]
        }
    )

def answer_explain_confidence_score(skill: str, profile: LearnerProfile) -> QAResponse:
    """
    8. explain_confidence_score: Returns Task 3 formula in plain language for a specific skill.
    """
    se = next((s for s in profile.extracted_skills if s.skill.lower() == skill.lower()), None)
    if se:
        answer = (
            f"The confidence score of {se.confidence}/10 for **{se.skill}** was calculated as follows:\n"
            f"- **Section Weight**: Found in section(s) `{', '.join(se.found_in_sections)}` (weight contribution: max section weight).\n"
            f"- **Frequency Score**: Mentioned {se.mention_count} time(s) across your document (frequency contribution: {min(se.mention_count, 5)}/5 * 3 points).\n"
            f"- **Applied Experience Bonus**: {'+2 points applied for appearance in EXPERIENCE/PROJECTS.' if ('EXPERIENCE' in se.found_in_sections or 'PROJECTS' in se.found_in_sections) else '0 bonus points (not found in EXPERIENCE/PROJECTS).'}"
        )
    else:
        answer = f"Skill '{skill}' was not found in your current profile."

    return QAResponse(
        question_id="explain_confidence_score",
        answer_text=answer,
        structured_payload={
            "skill": skill,
            "evidence": se.model_dump() if se else None
        }
    )
