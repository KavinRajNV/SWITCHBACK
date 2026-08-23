import pytest
from pathlib import Path
from app.nlp.parse_resume import parse_resume
from app.models.schemas import LearnerProfile

def test_parse_resume_plain_text_fixture():
    fixture_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "sample_resumes_for_parser_testing.txt"
    if not fixture_path.exists():
        pytest.skip(f"Fixture file not found at {fixture_path}")

    with open(fixture_path, "r", encoding="utf-8") as f:
        content = f.read()

    profile = parse_resume(content.encode("utf-8"), file_type="text")

    assert isinstance(profile, LearnerProfile)
    assert profile.raw_sections is not None
    assert len(profile.extracted_skills) > 0, "Should extract skills from sample resume fixture"

    skill_names = [se.skill for se in profile.extracted_skills]
    assert any(s in skill_names for s in ["Python", "SQL", "Java", "C++", "Machine Learning"]), f"Expected common skills in fixture, found: {skill_names}"

def test_parse_resume_empty_input():
    profile = parse_resume(b"", file_type="text")
    assert isinstance(profile, LearnerProfile)
    assert len(profile.parse_warnings) > 0
