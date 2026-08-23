import pytest
from app.nlp.explain_templates import explain_owned_skill, explain_gap_skill

def test_explain_owned_skill_positive():
    text = explain_owned_skill("Python", 0.4503)
    assert "Python" in text
    assert "+₹0.45L" in text
    assert "contributing" in text

def test_explain_owned_skill_negative():
    text = explain_owned_skill("Visual Basic", -0.1500)
    assert "Visual Basic" in text
    assert "-₹0.15L" in text
    assert "market adjustment" in text

def test_explain_owned_skill_near_zero():
    text = explain_owned_skill("Git", 0.0200)
    assert "Git" in text
    assert "neutral" in text or "foundational" in text

def test_explain_gap_skill():
    text = explain_gap_skill("Machine Learning", 6, 0.4503)
    assert "Machine Learning" in text
    assert "#6" in text
    assert "out of 265" in text
    assert "₹0.45L" in text
