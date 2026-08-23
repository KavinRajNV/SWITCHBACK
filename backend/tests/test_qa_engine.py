import pytest
from app.models.schemas import Milestone, LearnerProfile, GoalProfile, SkillEvidence
from app.nlp.qa_engine import (
    answer_why_this_skill,
    answer_how_long_will_this_take,
    answer_what_if_i_already_know_x,
    answer_show_free_alternatives,
    answer_why_this_role,
    answer_am_i_qualified_already,
    answer_what_skills_do_i_already_have,
    answer_explain_confidence_score
)

def test_answer_why_this_skill():
    ms = Milestone(skill="Machine Learning", step_number=1, cost=0.2, reachable_via="Python", is_essential=True)
    res = answer_why_this_skill("Machine Learning", milestone=ms, global_rank=6, global_val=0.45)

    assert res.question_id == "why_this_skill"
    assert "Machine Learning" in res.answer_text
    assert "Python" in res.answer_text
    assert "#6" in res.answer_text

def test_answer_how_long_will_this_take():
    gp = GoalProfile(hours_per_week=10, timeframe_days=90)
    res = answer_how_long_will_this_take(gp, path_length=10)

    assert res.question_id == "how_long_will_this_take"
    assert "400 total study hours" in res.answer_text
    assert "40 weeks" in res.answer_text

def test_answer_what_if_i_already_know_x():
    res = answer_what_if_i_already_know_x("AWS", {"Python", "SQL"}, "15-2051.00")

    assert res.question_id == "what_if_i_already_know_x"
    assert "AWS" in res.answer_text
    assert res.structured_payload["added_skill"] == "AWS"

def test_answer_what_skills_do_i_already_have():
    ev1 = SkillEvidence(skill="Python", category="Programming", confidence=10, mention_count=5, found_in_sections=["SKILLS", "EXPERIENCE"])
    ev2 = SkillEvidence(skill="SQL", category="Databases", confidence=8, mention_count=3, found_in_sections=["SKILLS"])
    profile = LearnerProfile(extracted_skills=[ev1, ev2])

    res = answer_what_skills_do_i_already_have(profile)
    assert res.question_id == "what_skills_do_i_already_have"
    assert "Python" in res.answer_text
    assert "SQL" in res.answer_text

def test_answer_explain_confidence_score():
    ev = SkillEvidence(skill="Python", category="Programming", confidence=10, mention_count=5, found_in_sections=["SKILLS", "EXPERIENCE"])
    profile = LearnerProfile(extracted_skills=[ev])

    res = answer_explain_confidence_score("Python", profile)
    assert res.question_id == "explain_confidence_score"
    assert "10/10" in res.answer_text
    assert "EXPERIENCE" in res.answer_text
