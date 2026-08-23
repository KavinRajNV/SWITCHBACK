import pytest
from app.nlp.section_classifier import classify_section

def test_classify_section_summary():
    assert classify_section("Professional Summary") == "SUMMARY"
    assert classify_section("Executive Summary") == "SUMMARY"
    assert classify_section("About Me") == "SUMMARY"
    assert classify_section("Career Objective") == "SUMMARY"
    assert classify_section("Personal Profile") == "SUMMARY"

def test_classify_section_experience():
    assert classify_section("Work Experience") == "EXPERIENCE"
    assert classify_section("Professional Experience") == "EXPERIENCE"
    assert classify_section("Employment History") == "EXPERIENCE"
    assert classify_section("Work History") == "EXPERIENCE"
    assert classify_section("Internships") == "EXPERIENCE"

def test_classify_section_education():
    assert classify_section("Education") == "EDUCATION"
    assert classify_section("Academic Background") == "EDUCATION"
    assert classify_section("Educational Qualifications") == "EDUCATION"
    assert classify_section("Education & Training") == "EDUCATION"
    assert classify_section("Scholastic Background") == "EDUCATION"

def test_classify_section_skills():
    assert classify_section("Technical Skills") == "SKILLS"
    assert classify_section("Core Competencies") == "SKILLS"
    assert classify_section("Skills & Tools") == "SKILLS"
    assert classify_section("Key Skills") == "SKILLS"
    assert classify_section("Areas of Expertise") == "SKILLS"

def test_classify_section_projects():
    assert classify_section("Academic Projects") == "PROJECTS"
    assert classify_section("Key Projects") == "PROJECTS"
    assert classify_section("Personal Projects") == "PROJECTS"
    assert classify_section("Side Projects") == "PROJECTS"
    assert classify_section("Technical Projects") == "PROJECTS"

def test_classify_section_certifications():
    assert classify_section("Certifications") == "CERTIFICATIONS"
    assert classify_section("Licenses & Certifications") == "CERTIFICATIONS"
    assert classify_section("Courses & Certifications") == "CERTIFICATIONS"
    assert classify_section("Professional Credentials") == "CERTIFICATIONS"
    assert classify_section("Trainings & Certifications") == "CERTIFICATIONS"

def test_classify_section_other():
    assert classify_section("Hobbies & Interests") == "OTHER"
    assert classify_section("Languages Spoken") == "OTHER"
    assert classify_section("References") == "OTHER"
    assert classify_section("Random Unrecognized Header") == "OTHER"
