import pytest
from app.data_pipeline.skill_matcher import SkillMatcher

@pytest.fixture
def matcher():
    return SkillMatcher.from_csv()

def test_exact_canonical_match(matcher):
    res = matcher.match_direct("Python")
    assert res is not None
    assert res.skill == "Python"
    assert res.score == 100.0

def test_alias_match(matcher):
    res = matcher.match_direct("ReactJS")
    assert res is not None
    assert res.skill == "React"
    assert res.score == 100.0

def test_near_miss_fuzzy_match(matcher):
    # "Reactjs" or slight typo
    res = matcher.match_direct("Reactjs", min_score=85)
    assert res is not None
    assert res.skill == "React"
    assert res.score >= 85.0

def test_no_vocabulary_skills(matcher):
    text = "The quick brown fox jumps over the lazy dog."
    skills = matcher.extract_skills(text)
    assert isinstance(skills, list)
    assert len(skills) == 0

def test_multi_skill_sentence(matcher):
    sentence = "Looking for a Data Scientist proficient in Python, SQL, and Machine Learning with PyTorch expertise."
    extracted = matcher.extract_skills(sentence)
    extracted_skills = [m.skill for m in extracted]
    assert "Python" in extracted_skills
    assert "SQL" in extracted_skills
    assert "Machine Learning" in extracted_skills
    assert "PyTorch" in extracted_skills
