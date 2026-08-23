import pytest
from app.data_pipeline.skill_matcher import SkillMatcher
from app.data_pipeline.segment_concatenated import segment_concatenated

@pytest.fixture
def matcher():
    return SkillMatcher.from_csv()

def test_audit_concatenated_string(matcher):
    raw_str = "Text miningCareer developmentdata scienceFinanceMachine learningData miningStakeholder managementSQL"
    result = segment_concatenated(raw_str, matcher)
    matched = result["matched_skills"]
    leftover = result["leftover"]
    
    # Vocabulary matched skills
    assert "Text Mining" in matched
    assert "Machine Learning" in matched
    assert "Data Mining" in matched
    assert "Stakeholder Management" in matched
    assert "SQL" in matched
    
    # Leftover tokens (terms not in seed vocabulary)
    all_extracted_text = [m.lower() for m in matched + leftover]
    assert any("career" in t for t in all_extracted_text)
    assert any("science" in t for t in all_extracted_text)
    assert any("finance" in t for t in all_extracted_text)

def test_delimited_string(matcher):
    raw_str = "Python, SQL, Machine Learning, React"
    result = segment_concatenated(raw_str, matcher)
    matched = result["matched_skills"]
    
    assert "Python" in matched
    assert "SQL" in matched
    assert "Machine Learning" in matched
    assert "React" in matched
