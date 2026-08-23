"""Deterministic, title-first course ranking.

``skills_matched`` is a retrieval index, not proof that a course teaches a
skill: historic fuzzy tagging contains false positives (notably C#, Spark and
short language names).  This module applies a second, explainable relevance
gate before a course can be shown to a learner.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List


# Abbreviations need aliases rather than naïve word matching.  The generic
# fallback intentionally requires every meaningful word from a skill name.
SKILL_PATTERNS = {
    "SQL": (r"\bsql\b", r"structured query", r"mysql", r"postgres", r"oracle database", r"sql server"),
    "C#": (r"\bc#\b", r"csharp", r"c sharp", r"\.net", r"asp\.net", r"dotnet"),
    "C++": (r"c\+\+", r"cpp", r"c plus plus"),
    "Apache Spark": (r"apache spark", r"\bspark\b", r"pyspark", r"databricks"),
    "Microsoft Excel": (r"\bexcel\b", r"spreadsheet"),
    "Power BI": (r"power\s*bi", r"powerbi"),
    "AWS": (r"\baws\b", r"amazon web services"),
    "Amazon EC2": (r"\bec2\b", r"elastic compute cloud"),
    "Amazon S3": (r"\bs3\b", r"simple storage service"),
    "Machine Learning": (r"machine learning", r"scikit", r"sklearn"),
    "Data Analysis": (r"data analys", r"data analytics", r"data analysis"),
    "Software Development": (r"software develop", r"software engineer", r"programming", r"computer science"),
}


def _text(course: Dict[str, Any]) -> str:
    # Titles are deliberately weighted most heavily: descriptions and broad
    # categories are much noisier in the imported catalogues.
    return " ".join(str(course.get(k) or "") for k in ("title", "headline", "category")).lower()


def _patterns(skill: str) -> Iterable[str]:
    if skill in SKILL_PATTERNS:
        return SKILL_PATTERNS[skill]
    words = [re.escape(w) for w in skill.lower().split() if len(w) >= 3]
    return tuple(r"\b" + w + r"\w*" for w in words)


def relevance_score(course: Dict[str, Any], skill: str) -> float:
    """Return 0 for a course that does not visibly teach ``skill``.

    A visible title/headline match is mandatory.  Ratings and learner counts
    are used only to order already-relevant courses, never as a substitute for
    topical relevance.
    """
    title = str(course.get("title") or "").lower()
    headline = str(course.get("headline") or "").lower()
    category = str(course.get("category") or "").lower()
    patterns = tuple(_patterns(skill))
    title_hits = sum(bool(re.search(p, title, re.I)) for p in patterns)
    detail_hits = sum(bool(re.search(p, headline + " " + category, re.I)) for p in patterns)

    # Multiword generic skills require every meaningful word in title/headline;
    # an isolated 'analysis' must not make a finance or music course a Data
    # Analysis recommendation.
    generic_words = [w for w in skill.lower().split() if len(w) >= 3]
    if skill not in SKILL_PATTERNS and generic_words:
        haystack = title + " " + headline
        if not all(re.search(r"\b" + re.escape(w) + r"\w*", haystack) for w in generic_words):
            return 0.0

    if not title_hits and not detail_hits:
        return 0.0

    rating = float(course.get("rating") or 0)
    reviews = max(0, int(course.get("num_reviews") or 0))
    subscribers = max(0, int(course.get("num_subscribers") or 0))
    return (title_hits * 10.0) + (detail_hits * 2.0) + rating + math.log1p(reviews + subscribers) / 5.0


def rank_courses(courses: Iterable[Dict[str, Any]], skill: str, limit: int = 3) -> List[Dict[str, Any]]:
    scored = [(relevance_score(course, skill), course) for course in courses]
    scored = [(score, course) for score, course in scored if score > 0]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [course for _, course in scored[:limit]]
