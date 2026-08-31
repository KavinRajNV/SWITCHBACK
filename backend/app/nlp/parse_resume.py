import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal

from app.models.schemas import LearnerProfile, SkillEvidence
from app.nlp.resume_sections import extract_pdf_sections, extract_docx_sections, extract_text_sections
from app.nlp.section_classifier import classify_section
from app.nlp.skill_confidence import score_skills
from app.data_pipeline.skill_matcher import SkillMatcher

def estimate_experience_years(sections: Dict[str, str]) -> Optional[float]:
    """
    Simple heuristic: scans EXPERIENCE section text for 4-digit years (1990-2029) and date ranges.
    Returns span from earliest year to latest year (or current year if 'present' appears), or None if no parseable dates found.
    """
    exp_text = ""
    for raw_hdr, body in sections.items():
        if classify_section(raw_hdr) == "EXPERIENCE":
            exp_text += f"\n{body}"

    if not exp_text.strip():
        # Fallback to searching all text if no explicit EXPERIENCE section
        exp_text = "\n".join(sections.values())

    years = [int(y) for y in re.findall(r'\b(199\d|20[0-2]\d)\b', exp_text)]
    if not years:
        return None

    min_year = min(years)
    has_present = bool(re.search(r'\b(present|current|now|till date)\b', exp_text, re.IGNORECASE))
    max_year = datetime.now().year if has_present else max(years)

    if max_year >= min_year:
        diff = float(max_year - min_year)
        return max(diff, 0.5)

    return None

def parse_resume(
    file_bytes: bytes,
    file_type: Literal["pdf", "docx", "text"],
    matcher: Optional[SkillMatcher] = None
) -> LearnerProfile:
    """
    Master resume parsing orchestrator.
    Extracts sections, classifies headers, extracts skills with confidence scoring, estimates experience,
    and logs parse warnings for degraded conditions.
    """
    warnings: List[str] = []

    # 1. Document section extraction
    if file_type == "pdf":
        raw_sections = extract_pdf_sections(file_bytes)
    elif file_type == "docx":
        raw_sections = extract_docx_sections(file_bytes)
    elif file_type == "text":
        text_str = file_bytes.decode("utf-8", errors="ignore") if isinstance(file_bytes, bytes) else str(file_bytes)
        raw_sections = extract_text_sections(text_str)
    else:
        raise ValueError(f"Unsupported file_type '{file_type}'. Supported: 'pdf', 'docx', 'text'.")

    if not raw_sections:
        raw_sections = {"UNSTRUCTURED": ""}
        warnings.append("Document text extraction yielded empty content.")

    if "UNSTRUCTURED" in raw_sections and len(raw_sections) == 1:
        warnings.append("Document contained zero detected section headers; parsed under single 'UNSTRUCTURED' section.")

    # 2. Section classification check
    classified_types = [classify_section(hdr) for hdr in raw_sections.keys()]
    if "SKILLS" not in classified_types:
        warnings.append("No explicit SKILLS section detected; skill extraction performed over full document text.")

    # 3. Skill confidence scoring
    extracted_skills = score_skills(raw_sections, matcher=matcher)

    if not extracted_skills:
        warnings.append("No canonical vocabulary skills extracted from document text.")

    # 4. Experience estimation
    exp_years = estimate_experience_years(raw_sections)
    if exp_years is None:
        warnings.append("No parseable date ranges found in EXPERIENCE section; experience estimation defaulted to None.")

    return LearnerProfile(
        raw_sections=raw_sections,
        extracted_skills=extracted_skills,
        experience_years_est=exp_years,
        parse_warnings=warnings
    )
