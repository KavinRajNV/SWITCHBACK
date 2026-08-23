import pytest
from app.nlp.skill_confidence import score_skills
from app.data_pipeline.skill_matcher import SkillMatcher

@pytest.fixture
def matcher():
    return SkillMatcher.from_csv()

def test_education_only_skill_score_low(matcher):
    sections = {
        "Education": "Bachelor of Science in Computer Science with coursework in Python and SQL."
    }
    evidence = score_skills(sections, matcher=matcher)
    py_ev = next((e for e in evidence if e.skill == "Python"), None)

    assert py_ev is not None
    assert "EDUCATION" in py_ev.found_in_sections
    assert py_ev.confidence <= 4, f"Education-only skill should have low confidence, got {py_ev.confidence}"

def test_skills_and_experience_multi_mention_near_ten(matcher):
    sections = {
        "Technical Skills": "Python, SQL, Machine Learning, TensorFlow, PyTorch",
        "Work Experience": "Senior Data Scientist using Python for Machine Learning models daily. Developed Python pipelines and Machine Learning algorithms."
    }
    evidence = score_skills(sections, matcher=matcher)
    py_ev = next((e for e in evidence if e.skill == "Python"), None)

    assert py_ev is not None
    assert "SKILLS" in py_ev.found_in_sections
    assert "EXPERIENCE" in py_ev.found_in_sections
    assert py_ev.mention_count >= 2
    assert py_ev.confidence >= 8, f"Skills + Experience multi-mention should score near 10, got {py_ev.confidence}"

def test_other_section_only_skill_score_low_nonzero(matcher):
    sections = {
        "Hobbies & Interests": "Enjoy reading technical blogs on AWS cloud computing."
    }
    evidence = score_skills(sections, matcher=matcher)
    aws_ev = next((e for e in evidence if e.skill == "AWS"), None)

    assert aws_ev is not None
    assert "OTHER" in aws_ev.found_in_sections
    assert 1 <= aws_ev.confidence <= 4, f"Other-section skill should score low but non-zero (1-4), got {aws_ev.confidence}"
