from typing import Dict, List, Set, Any, Optional
from collections import Counter, defaultdict

from app.nlp.section_classifier import classify_section
from app.models.schemas import SkillEvidence
from app.data_pipeline.skill_matcher import SkillMatcher
from app.db.mongo_client import get_db

SECTION_WEIGHT_MAP = {
    "SKILLS": 4.0,
    "EXPERIENCE": 4.0,
    "PROJECTS": 3.0,
    "CERTIFICATIONS": 3.0,
    "SUMMARY": 2.0,
    "EDUCATION": 1.0,
    "OTHER": 1.0
}

def score_skills(sections: Dict[str, str], matcher: Optional[SkillMatcher] = None) -> List[SkillEvidence]:
    """
    Extracts vocabulary skills per section, merges per skill across sections, and computes exact confidence scores (1-10).
    """
    if matcher is None:
        try:
            db = get_db()
            matcher = SkillMatcher.from_mongo(db)
        except Exception:
            matcher = SkillMatcher.from_csv()

    # Track per-skill occurrences across sections
    skill_mention_counts: Counter = Counter()
    skill_found_sections: Dict[str, Set[str]] = defaultdict(set)
    skill_categories: Dict[str, str] = {}

    for raw_header, body_text in sections.items():
        if not body_text or not body_text.strip():
            continue

        canonical_sec = classify_section(raw_header)
        matches = matcher.extract_skills(body_text)

        for m in matches:
            sk = m.skill
            skill_mention_counts[sk] += 1
            skill_found_sections[sk].add(canonical_sec)
            if sk not in skill_categories:
                skill_categories[sk] = m.category

    evidence_list: List[SkillEvidence] = []

    for sk, count in skill_mention_counts.most_common():
        found_secs = sorted(list(skill_found_sections[sk]))
        cat = skill_categories.get(sk, "General")

        # 1. Section weight (max weight across sections where skill was found)
        sec_weights = [SECTION_WEIGHT_MAP.get(sec, 1.0) for sec in found_secs]
        sec_weight = max(sec_weights) if sec_weights else 1.0

        # 2. Frequency score (caps out at 3 points for 5+ mentions)
        freq_score = (min(count, 5) / 5.0) * 3.0

        # 3. Applied bonus (2 points if found in EXPERIENCE or PROJECTS)
        applied_bonus = 2.0 if ("EXPERIENCE" in found_secs or "PROJECTS" in found_secs) else 0.0

        raw_score = sec_weight + freq_score + applied_bonus
        confidence = int(min(max(round(raw_score), 1), 10))

        evidence = SkillEvidence(
            skill=sk,
            category=cat,
            confidence=confidence,
            mention_count=count,
            found_in_sections=found_secs
        )
        evidence_list.append(evidence)

    return evidence_list
