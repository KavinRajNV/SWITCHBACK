"""Intent-routing tests for the conversational assistant layer."""
import pytest

from app.nlp.assistant import classify_intent, INTENTS


class _FakeMatch:
    def __init__(self, skill):
        self.skill = skill


class _FakeMatcher:
    """Minimal stand-in: finds a known skill name as a substring of the text."""
    KNOWN = ["AWS", "Docker", "Python", "SQL", "Power BI", "Machine Learning", "Kubernetes"]

    def extract_skills(self, text):
        tl = (text or "").lower()
        return [_FakeMatch(s) for s in self.KNOWN if s.lower() in tl]

    def match_direct(self, text):
        for s in self.KNOWN:
            if s.lower() == (text or "").strip().lower():
                return _FakeMatch(s)
        return None


matcher = _FakeMatcher()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("How long will this whole path take me?", "how_long_will_this_take"),
        ("how many weeks until I'm done?", "how_long_will_this_take"),
        ("what if I already know AWS?", "what_if_i_already_know_x"),
        ("if I learn Docker can I skip a step?", "what_if_i_already_know_x"),
        ("is there a free course for Docker?", "show_free_alternatives"),
        ("show me a cheaper way to learn Python", "show_free_alternatives"),
        ("why should I target this role?", "why_this_role"),
        ("am I qualified for this role yet?", "am_i_qualified_already"),
        ("what's my skill gap?", "am_i_qualified_already"),
        ("what skills do I already have?", "what_skills_do_i_already_have"),
        ("explain my confidence score", "explain_confidence_score"),
        ("why is Kubernetes on my path?", "why_this_skill"),
    ],
)
def test_classify_intent_maps_phrasings(text, expected):
    intent, _params = classify_intent(text, matcher)
    assert intent == expected, f"{text!r} -> {intent} (wanted {expected})"


def test_skill_is_extracted_for_skill_scoped_intents():
    intent, params = classify_intent("what if I already know AWS?", matcher)
    assert intent == "what_if_i_already_know_x"
    assert params.get("skill") == "AWS"


def test_unrecognized_text_falls_back_to_general():
    intent, _ = classify_intent("hello there, nice weather today", matcher)
    assert intent == "general"


def test_general_when_no_matcher_and_vague():
    intent, _ = classify_intent("tell me about stuff", None)
    assert intent == "general"


def test_every_intent_id_has_a_rationale():
    from app.nlp.assistant import _RATIONALE
    for iid in list(INTENTS) + ["general"]:
        assert iid in _RATIONALE and _RATIONALE[iid]
