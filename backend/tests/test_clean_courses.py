import pytest
import ast
from app.data_pipeline.clean_courses import strip_currency
from app.data_pipeline.skill_matcher import SkillMatcher
from app.db.mongo_client import get_db

@pytest.fixture
def matcher():
    return SkillMatcher.from_csv()

def test_strip_currency():
    assert strip_currency("$19.99 Python Course") == "19.99 Python Course"
    assert strip_currency("Rs. 500 Data Science") == "500 Data Science"

def test_coursera_tag_parsing(matcher):
    raw_tag_str = "['Data Science', 'Data Analysis', 'Python Programming']"
    parsed_tags = ast.literal_eval(raw_tag_str)
    assert parsed_tags == ['Data Science', 'Data Analysis', 'Python Programming']
    
    matched_skills = []
    for tag in parsed_tags:
        direct = matcher.match_direct(tag)
        if direct and direct.skill not in matched_skills:
            matched_skills.append(direct.skill)
        else:
            extracted = matcher.extract_skills(tag)
            for m in extracted:
                if m.skill not in matched_skills:
                    matched_skills.append(m.skill)
            
    assert "Data Analysis" in matched_skills
    assert "Python" in matched_skills

def test_coursera_ingestion_regression():
    db = get_db()
    coll = db["courses"]
    udemy_large_count = coll.count_documents({"source": "udemy_large"})
    udemy_small_count = coll.count_documents({"source": "udemy_small"})
    coursera_count = coll.count_documents({"source": "coursera"})
    total_count = coll.count_documents({})
    
    assert udemy_large_count == 98104
    assert udemy_small_count == 3672
    assert coursera_count == 3850, f"Expected exactly 3850 Coursera courses, found: {coursera_count}"
    assert total_count == 105626, f"Expected exactly 105626 total courses, found: {total_count}"
