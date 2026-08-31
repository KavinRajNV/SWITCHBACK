import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple
from rapidfuzz import fuzz, process
from pymongo.database import Database

from app.models.schemas import GoalProfile
from app.db.mongo_client import get_db

MONTH_NAMES = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12
}

def parse_timeframe_days(text: str) -> Optional[int]:
    """
    Parses timeframe phrasings like '3 months', '6 weeks', '1 year', 'by December' into integer days.
    """
    if not text:
        return None

    text_lower = text.lower()

    # 1. Check months
    m = re.search(r'\b(\d+)\s*(month|months|mon|mth)\b', text_lower)
    if m:
        return int(m.group(1)) * 30

    # 2. Check weeks
    m = re.search(r'\b(\d+)\s*(week|weeks|wk|wks)\b', text_lower)
    if m:
        return int(m.group(1)) * 7

    # 3. Check years
    m = re.search(r'\b(\d+)\s*(year|years|yr|yrs)\b', text_lower)
    if m:
        return int(m.group(1)) * 365

    # 4. Check 'in a year' or 'in a month'
    if "a year" in text_lower or "one year" in text_lower:
        return 365
    if "a month" in text_lower or "one month" in text_lower:
        return 30

    # 5. Check 'by <MonthName>'
    m = re.search(r'\bby\s+([a-z]+)\b', text_lower)
    if m:
        month_str = m.group(1)
        target_month = MONTH_NAMES.get(month_str)
        if target_month:
            today = date.today()
            curr_year = today.year
            curr_month = today.month

            if target_month >= curr_month:
                target_year = curr_year
            else:
                target_year = curr_year + 1

            # Estimate days to end of target month
            target_date = date(target_year, target_month, 28)
            delta = (target_date - today).days
            return max(delta, 15)

    return None

def parse_hours_per_week(text: str) -> Optional[int]:
    """
    Parses availability phrasings like '10 hours a week', 'part time', 'full time' into integer hours/week.
    Defaults: 'part time' -> 15 hrs/wk, 'full time' / 'intensive' -> 35 hrs/wk.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Explicit numbers
    m = re.search(r'\b(\d+)\s*(hours|hrs|hr)\b', text_lower)
    if m:
        return int(m.group(1))

    if "part time" in text_lower or "part-time" in text_lower:
        return 15

    if "full time" in text_lower or "full-time" in text_lower or "intensive" in text_lower:
        return 35

    return None

def parse_goal_text(text: str, db: Optional[Database] = None) -> GoalProfile:
    """
    Parses free-text goal input using rapidfuzz & regex rules.
    Returns GoalProfile Pydantic model.
    """
    if not text or not text.strip():
        return GoalProfile(needs_clarification=True)

    text_str = text.strip()

    if db is None:
        try:
            db = get_db()
        except Exception:
            db = None

    # 1. Match target role against occupations catalog
    target_role = None
    target_soc = None
    needs_clarification = False

    if db is not None:
        occ_docs = list(db.occupations_enriched.find({}, {"title": 1, "onet_soc_code": 1}))
        if occ_docs:
            titles_map = {d["title"]: d["onet_soc_code"] for d in occ_docs if d.get("title")}
            titles_list = list(titles_map.keys())

            # Expanded alias mappings for natural-language goal phrases → canonical O*NET titles
            role_aliases = {
                # Data roles
                "data scientist": "Data Scientists",
                "senior data scientist": "Data Scientists",
                "machine learning engineer": "Data Scientists",
                "ml engineer": "Data Scientists",
                "ai engineer": "Data Scientists",
                "nlp engineer": "Data Scientists",
                "natural language processing": "Data Scientists",
                "computer vision": "Data Scientists",
                "data analyst": "Data Analysts",
                "business analyst": "Management Analysts",
                "data engineer": "Database Architects",
                "database admin": "Database Administrators",
                "database architect": "Database Architects",
                # Software engineering
                "software engineer": "Software Developers",
                "software developer": "Software Developers",
                "backend developer": "Software Developers",
                "backend engineer": "Software Developers",
                "frontend developer": "Web Developers",
                "frontend engineer": "Web Developers",
                "full stack developer": "Software Developers",
                "full stack engineer": "Software Developers",
                "web developer": "Web Developers",
                "mobile developer": "Software Developers",
                "ios developer": "Software Developers",
                "android developer": "Software Developers",
                # Cloud / DevOps / Infra
                "cloud developer": "Computer Network Architects",
                "cloud engineer": "Computer Network Architects",
                "cloud architect": "Computer Network Architects",
                "solutions architect": "Computer Network Architects",
                "devops engineer": "Network and Computer Systems Administrators",
                "platform engineer": "Network and Computer Systems Administrators",
                "site reliability engineer": "Network and Computer Systems Administrators",
                "sre": "Network and Computer Systems Administrators",
                "systems administrator": "Network and Computer Systems Administrators",
                # Cybersecurity
                "security engineer": "Information Security Analysts",
                "cybersecurity analyst": "Information Security Analysts",
                "security analyst": "Information Security Analysts",
                # Product / UX
                "product manager": "Computer and Information Systems Managers",
                "product owner": "Computer and Information Systems Managers",
                "ux designer": "Web and Digital Interface Designers",
                "ui designer": "Web and Digital Interface Designers",
                # Finance / Analytics
                "financial analyst": "Financial Analysts",
                "quantitative analyst": "Financial Analysts",
            }

            matched_title = None
            text_lower = text_str.lower()

            for alias, canon in role_aliases.items():
                if alias in text_lower:
                    matched_title = canon
                    break

            if not matched_title:
                res = process.extractOne(text_str, titles_list, scorer=fuzz.token_set_ratio, score_cutoff=60)
                if res:
                    matched_title = res[0]


            if matched_title:
                target_role = matched_title
                target_soc = titles_map.get(matched_title)
            else:
                needs_clarification = True
        else:
            needs_clarification = True
    else:
        needs_clarification = True

    # 2. Parse timeframe & hours
    timeframe_days = parse_timeframe_days(text_str)
    hours_per_week = parse_hours_per_week(text_str)

    # 3. Background hint
    background_hint = text_str

    return GoalProfile(
        target_role=target_role,
        target_soc_code=target_soc,
        timeframe_days=timeframe_days,
        hours_per_week=hours_per_week,
        background_hint=background_hint,
        needs_clarification=needs_clarification
    )
