import re

CANONICAL_SECTIONS = [
    "SUMMARY",
    "EXPERIENCE",
    "EDUCATION",
    "SKILLS",
    "PROJECTS",
    "CERTIFICATIONS",
    "OTHER"
]

SECTION_KEYWORDS = {
    "SUMMARY": [
        "summary", "objective", "profile", "about me", "professional summary",
        "executive summary", "career summary", "personal profile", "overview"
    ],
    "EXPERIENCE": [
        "experience", "work experience", "professional experience", "employment history",
        "work history", "career history", "internships", "employment", "positions held",
        "experience history", "work background"
    ],
    "EDUCATION": [
        "education", "academic background", "qualifications", "education & training",
        "educational background", "academic qualifications", "academics", "educational history",
        "degrees", "scholastic background"
    ],
    "SKILLS": [
        "skills", "technical skills", "core competencies", "skills & tools", "key skills",
        "technologies", "expertise", "technical proficiencies", "areas of expertise",
        "tooling", "technologies & frameworks", "hard skills", "proficiencies"
    ],
    "PROJECTS": [
        "projects", "academic projects", "key projects", "personal projects",
        "side projects", "featured projects", "project history", "technical projects"
    ],
    "CERTIFICATIONS": [
        "certifications", "licenses", "certificates", "courses & certifications",
        "credentials", "professional certifications", "trainings & certifications",
        "license & certification"
    ]
}

def classify_section(raw_header: str) -> str:
    """
    Classifies a raw section header string into one of canonical types:
    SUMMARY, EXPERIENCE, EDUCATION, SKILLS, PROJECTS, CERTIFICATIONS, OTHER.
    """
    if not raw_header or not isinstance(raw_header, str):
        return "OTHER"

    header_clean = raw_header.strip().lower()
    header_clean = re.sub(r'[^a-z0-9\s&]', ' ', header_clean).strip()

    if header_clean == "unstructured":
        return "OTHER"

    for canonical, keywords in SECTION_KEYWORDS.items():
        for kw in keywords:
            if header_clean == kw:
                return canonical
            if f" {kw} " in f" {header_clean} ":
                return canonical
            if header_clean.startswith(kw) or header_clean.endswith(kw):
                return canonical

    return "OTHER"
