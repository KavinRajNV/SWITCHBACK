import pytest
from app.nlp.goal_parser import parse_goal_text, parse_timeframe_days, parse_hours_per_week

def test_parse_timeframe_days_patterns():
    assert parse_timeframe_days("I want to become a data scientist in 3 months") == 90
    assert parse_timeframe_days("finish in 6 weeks") == 42
    assert parse_timeframe_days("complete in 1 year") == 365
    assert parse_timeframe_days("by December") is not None
    assert parse_timeframe_days("random text with no date") is None

def test_parse_hours_per_week_patterns():
    assert parse_hours_per_week("I can dedicate 10 hours a week") == 10
    assert parse_hours_per_week("working part time") == 15
    assert parse_hours_per_week("intensive full time study") == 35
    assert parse_hours_per_week("random text") is None

def test_parse_goal_text_clean_example():
    goal = parse_goal_text("I want to become a Data Scientist in 3 months working 10 hours a week")
    assert goal.target_role is not None
    assert "Data Science" in goal.target_role or "Data Scientist" in goal.target_role
    assert goal.timeframe_days == 90
    assert goal.hours_per_week == 10
    assert goal.needs_clarification is False

def test_parse_goal_text_ambiguous_example():
    goal = parse_goal_text("I want to do something cool with computers")
    assert goal.timeframe_days is None
    assert goal.hours_per_week is None
    assert goal.needs_clarification is True
