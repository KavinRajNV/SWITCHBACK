"""
A3 FIX: Remove spuriously tagged courses from skills_matched.

Problem: The fuzzy skill-matcher applied to course titles/headlines incorrectly
tagged many courses with skills based on substring matching:
  - "C#" matched musical note C# -> piano/music courses
  - "Apache Spark" matched word "spark" -> spirituality/leadership courses
  - "Groovy" matched adjective "groovy" -> guitar/music courses
  - "C" matched the letter C in many titles
  - "Go" matched the word "go" generically
  - "R" matched the single letter R
  - "F#" matched musical note F#

Fix: For each problematic skill, apply a title/headline sanity filter:
  - A course is only allowed to keep that skill tag if its title or headline
    contains at least one technical keyword associated with that skill.
  - If it fails the sanity check: remove that skill from skills_matched.
  - We do NOT delete the course; we only remove the false tag.

Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\fix_course_tags.py
"""

import sys
import re
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')

from app.db.mongo_client import get_db
db = get_db()

# ─── Sanity filter definitions ─────────────────────────────────────────────────
# For each skill, a list of keywords that MUST appear (case-insensitive) in
# title+headline for the tag to be valid.  If NONE match → strip the tag.
SKILL_SANITY_FILTERS = {
    "C#": {
        "required_any": [
            r"\bc#\b", r"\bc sharp\b", r"csharp", r"\.net", r"asp\.net",
            r"unity", r"xamarin", r"monogame", r"winforms", r"wpf", r"blazor",
            r"microsoft.*develop", r"game develop", r"programming.*c#",
        ],
        "description": "C# programming language"
    },
    "Apache Spark": {
        "required_any": [
            r"spark", r"apache spark", r"pyspark", r"databricks", r"hadoop",
            r"big data", r"distributed", r"scala.*data", r"data engineering",
            r"spark streaming", r"rdd", r"dataframe.*spark",
        ],
        "description": "Apache Spark big-data framework"
    },
    "Groovy": {
        "required_any": [
            r"groovy", r"gradle", r"grails", r"spock", r"jenkins.*pipeline",
            r"jvm.*scripting", r"groovy.*program",
        ],
        "description": "Groovy JVM programming language"
    },
    "Go": {
        "required_any": [
            r"\bgo\b.*programming", r"\bgolang\b", r"\bgo\b.*lang",
            r"go.*develop", r"go.*microservice", r"go.*backend",
            r"programming.*\bgo\b", r"\bgo\b.*concurr",
        ],
        "description": "Go (Golang) programming language"
    },
    "R": {
        "required_any": [
            r"\br\b.*programming", r"\br\b.*statistic", r"\br\b.*data",
            r"\brstudio\b", r"\br\b.*language", r"data.*\br\b",
            r"\br\b.*analys", r"ggplot", r"tidyverse", r"cran",
        ],
        "description": "R statistical programming language"
    },
    "C": {
        "required_any": [
            r"\bc programming\b", r"\bc language\b", r"c/c\+\+",
            r"\bc\b.*pointer", r"system.*programming.*\bc\b",
            r"\bc\b.*algorithm", r"\bc\b.*embed", r"embedded.*c\b",
        ],
        "description": "C programming language"
    },
    "F#": {
        "required_any": [
            r"f#", r"f sharp", r"fsharp", r"functional.*\.net", r"\.net.*functional",
        ],
        "description": "F# functional programming language"
    },
    "Rust": {
        "required_any": [
            r"\brust\b.*programming", r"\brust\b.*language", r"rustlang",
            r"\brust\b.*system", r"\brust\b.*web", r"cargo.*rust",
        ],
        "description": "Rust systems programming language"
    },
    "Julia": {
        "required_any": [
            r"\bjulia\b.*programming", r"\bjulia\b.*language", r"\bjulia\b.*data",
            r"\bjulia\b.*science", r"\bjulia\b.*numeric",
        ],
        "description": "Julia scientific programming language"
    },
}

def text_passes_filter(title: str, headline: str, filter_def: dict) -> bool:
    """
    Returns True if the course's title+headline contains at least one
    of the required keywords (as regex patterns) for this skill.
    """
    combined = (title + " " + headline).lower()
    for pattern in filter_def["required_any"]:
        if re.search(pattern, combined, re.IGNORECASE):
            return True
    return False

print("=" * 70)
print("A3: Course tag sanity fix")
print("=" * 70)
print()

total_stripped = 0

for skill, filter_def in SKILL_SANITY_FILTERS.items():
    # Find all courses tagged with this skill
    tagged_count = db.courses.count_documents({"skills_matched": skill})
    if tagged_count == 0:
        print(f"  {skill}: 0 tagged courses — skip")
        continue
    
    print(f"  {skill} ({filter_def['description']}): {tagged_count} tagged courses")
    
    # Scan and find spurious tags
    bad_ids = []
    sample_bad = []
    
    cursor = db.courses.find(
        {"skills_matched": skill},
        {"_id": 1, "title": 1, "headline": 1, "skills_matched": 1}
    )
    for doc in cursor:
        title = doc.get("title", "") or ""
        headline = doc.get("headline", "") or ""
        if not text_passes_filter(title, headline, filter_def):
            bad_ids.append(doc["_id"])
            if len(sample_bad) < 3:
                sample_bad.append(f"    BAD: [{title[:60]}]")
    
    good_count = tagged_count - len(bad_ids)
    print(f"    Valid (pass filter): {good_count}")
    print(f"    Spurious (will strip): {len(bad_ids)}")
    for s in sample_bad:
        print(s)
    
    if bad_ids:
        # Remove this skill from skills_matched for bad docs (in batches of 500)
        batch_size = 500
        removed = 0
        for i in range(0, len(bad_ids), batch_size):
            batch = bad_ids[i:i+batch_size]
            result = db.courses.update_many(
                {"_id": {"$in": batch}},
                {"$pull": {"skills_matched": skill}}
            )
            removed += result.modified_count
        print(f"    Stripped tag from {removed} documents")
        total_stripped += removed
    print()

print(f"Total tags stripped across all skills: {total_stripped}")
print()

# ─── Verify counts after fix ────────────────────────────────────────────────────
print("=" * 70)
print("Post-fix course counts (should be much lower for C#, Apache Spark, Groovy):")
print("=" * 70)
for skill in ["Apache Spark", "C#", "Groovy", "Go", "R", "C", "F#"]:
    count = db.courses.count_documents({"skills_matched": skill})
    print(f"  {skill:<30} -> {count:>4} courses")

print()
print("A3 Fix complete.")
