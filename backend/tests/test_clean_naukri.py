import pytest
from app.data_pipeline.clean_naukri import (
    normalize_job_title,
    parse_experience,
    parse_salary
)

def test_normalize_job_title():
    assert normalize_job_title("senior sql developer") == "Senior SQL Developer"
    assert normalize_job_title("ai / ml engineer") == "AI / ML Engineer"

def test_parse_experience():
    assert parse_experience("4-8 Yrs") == (4.0, 8.0)
    assert parse_experience("2 - 5 yrs") == (2.0, 5.0)
    assert parse_experience("5 yrs") == (5.0, 5.0)
    assert parse_experience("Not disclosed") == (None, None)

def test_parse_salary():
    min_sal, max_sal, disclosed = parse_salary("10-20 Lacs PA")
    assert disclosed is True
    assert min_sal == 10.0
    assert max_sal == 20.0
    
    min_sal, max_sal, disclosed = parse_salary("Not disclosed")
    assert disclosed is False
    assert min_sal is None
    assert max_sal is None

    min_sal, max_sal, disclosed = parse_salary("3,00,000 - 6,00,000 P.A.")
    assert disclosed is True
    assert min_sal == 3.0
    assert max_sal == 6.0
