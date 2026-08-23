"""
PART E (revised): Rebuild market_roles with better skill extraction from skills_raw.

The issue: skills_raw contains concatenated text like "React.jsNode.jsJavascriptHTMLCSS"
without spaces, so the SkillMatcher missed many skills.

Fix: Pre-process skills_raw by inserting word boundaries before known skill names,
then run the SkillMatcher on the result.

Also: for the 'combined_required_skills' field, use BOTH:
1. The existing skills_matched (canonical skills from phase 2 pipeline)
2. Direct re-extraction from skills_raw using SkillMatcher

Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\rebuild_market_roles.py
"""
import sys, re
from collections import defaultdict, Counter
import statistics

sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()
from app.data_pipeline.skill_matcher import SkillMatcher

print("Loading SkillMatcher...")
matcher = SkillMatcher.from_mongo(db)
print(f"Vocabulary: {len(matcher.canonical_skills)} canonical skills")

print("Loading primary-quality jobs...")
jobs = list(db.jobs.find(
    {"source_quality": "primary"},
    {
        "job_title": 1,
        "skills_matched": 1,
        "skills_raw": 1,
        "salary_min_lpa": 1,
        "salary_max_lpa": 1,
    }
))
print(f"Loaded {len(jobs)} jobs")

# ─── Title normalization (same as before) ─────────────────────────────────────
def normalize_title(raw: str) -> str:
    if not raw: return ""
    t = raw.lower().strip()
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\s*[-|/].*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\bsr\.?\b', 'senior', t)
    t = re.sub(r'\bjr\.?\b', 'junior', t)
    t = re.sub(r'\bmgr\.?\b', 'manager', t)
    t = re.sub(r'\bdev\b', 'developer', t)
    t = re.sub(r'\beng\b', 'engineer', t)
    t = re.sub(r'\bspec\b', 'specialist', t)
    return t

CLUSTER_RULES = [
    (r'machine learning engineer',  'Machine Learning Engineer'),
    (r'ml engineer',               'Machine Learning Engineer'),
    (r'ai engineer',               'Machine Learning Engineer'),
    (r'deep learning engineer',    'Machine Learning Engineer'),
    (r'nlp engineer',              'NLP Engineer'),
    (r'nlp scientist',             'NLP Engineer'),
    (r'computer vision engineer',  'Computer Vision Engineer'),
    (r'data science lead',         'Data Science Lead'),
    (r'head.*data science',        'Data Science Lead'),
    (r'data science manager',      'Data Science Manager'),
    (r'principal data scientist',  'Principal Data Scientist'),
    (r'lead data scientist',       'Lead Data Scientist'),
    (r'senior data scientist',     'Senior Data Scientist'),
    (r'data scientist',            'Data Scientist'),
    (r'data science',              'Data Scientist'),
    (r'senior.*data analyst',      'Senior Data Analyst'),
    (r'data analyst',              'Data Analyst'),
    (r'analytics engineer',        'Analytics Engineer'),
    (r'business analyst',          'Business Analyst'),
    (r'business intelligence',     'Business Intelligence Analyst'),
    (r'product analyst',           'Product Analyst'),
    (r'marketing analyst',         'Marketing Analyst'),
    (r'financial analyst',         'Financial Analyst'),
    (r'quantitative analyst',      'Quantitative Analyst'),
    (r'risk analyst',              'Risk Analyst'),
    (r'operations analyst',        'Operations Analyst'),
    (r'senior data engineer',      'Senior Data Engineer'),
    (r'data engineer',             'Data Engineer'),
    (r'data platform engineer',    'Data Engineer'),
    (r'etl developer',             'Data Engineer'),
    (r'etl engineer',              'Data Engineer'),
    (r'full.?stack developer',     'Full Stack Developer'),
    (r'full.?stack engineer',      'Full Stack Developer'),
    (r'full stack',                'Full Stack Developer'),
    (r'backend developer',         'Backend Developer'),
    (r'backend engineer',          'Backend Developer'),
    (r'back.?end developer',       'Backend Developer'),
    (r'back.?end engineer',        'Backend Developer'),
    (r'frontend developer',        'Frontend Developer'),
    (r'frontend engineer',         'Frontend Developer'),
    (r'front.?end developer',      'Frontend Developer'),
    (r'front.?end engineer',       'Frontend Developer'),
    (r'react developer',           'Frontend Developer'),
    (r'angular developer',         'Frontend Developer'),
    (r'vue developer',             'Frontend Developer'),
    (r'ui developer',              'Frontend Developer'),
    (r'ux developer',              'Frontend Developer'),
    (r'web developer',             'Web Developer'),
    (r'mobile developer',          'Mobile App Developer'),
    (r'android developer',         'Android Developer'),
    (r'ios developer',             'iOS Developer'),
    (r'flutter developer',         'Mobile App Developer'),
    (r'react native developer',    'Mobile App Developer'),
    (r'java developer',            'Java Developer'),
    (r'java engineer',             'Java Developer'),
    (r'python developer',          'Python Developer'),
    (r'python engineer',           'Python Developer'),
    (r'node\.?js developer',       'Node.js Developer'),
    (r'node developer',            'Node.js Developer'),
    (r'\.net developer',           '.NET Developer'),
    (r'dotnet developer',          '.NET Developer'),
    (r'c# developer',              '.NET Developer'),
    (r'c\+\+ developer',           'C++ Developer'),
    (r'php developer',             'PHP Developer'),
    (r'golang developer',          'Go Developer'),
    (r'go developer',              'Go Developer'),
    (r'rust developer',            'Rust Developer'),
    (r'scala developer',           'Scala Developer'),
    (r'kotlin developer',          'Android Developer'),
    (r'swift developer',           'iOS Developer'),
    (r'r developer',               'R Developer'),
    (r'senior software engineer',  'Senior Software Engineer'),
    (r'senior software developer', 'Senior Software Engineer'),
    (r'principal engineer',        'Principal Software Engineer'),
    (r'staff engineer',            'Staff Software Engineer'),
    (r'software engineer',         'Software Engineer'),
    (r'software developer',        'Software Developer'),
    (r'software development engineer', 'Software Engineer'),
    (r'application developer',     'Software Developer'),
    (r'devops engineer',           'DevOps Engineer'),
    (r'devsecops',                 'DevSecOps Engineer'),
    (r'site reliability engineer', 'Site Reliability Engineer'),
    (r'\bsre\b',                   'Site Reliability Engineer'),
    (r'platform engineer',         'Platform Engineer'),
    (r'infrastructure engineer',   'Infrastructure Engineer'),
    (r'cloud engineer',            'Cloud Engineer'),
    (r'aws engineer',              'Cloud Engineer'),
    (r'azure engineer',            'Cloud Engineer'),
    (r'gcp engineer',              'Cloud Engineer'),
    (r'cloud architect',           'Cloud Architect'),
    (r'solutions architect',       'Solutions Architect'),
    (r'enterprise architect',      'Enterprise Architect'),
    (r'database administrator',    'Database Administrator'),
    (r'\bdba\b',                   'Database Administrator'),
    (r'database engineer',         'Database Engineer'),
    (r'database developer',        'Database Engineer'),
    (r'test engineer',             'QA Engineer'),
    (r'qa engineer',               'QA Engineer'),
    (r'quality assurance engineer','QA Engineer'),
    (r'automation engineer',       'QA Automation Engineer'),
    (r'automation test',           'QA Automation Engineer'),
    (r'sdet\b',                    'QA Automation Engineer'),
    (r'security engineer',         'Security Engineer'),
    (r'security analyst',          'Security Analyst'),
    (r'cybersecurity',             'Security Analyst'),
    (r'information security',      'Security Analyst'),
    (r'product manager',           'Product Manager'),
    (r'product owner',             'Product Manager'),
    (r'program manager',           'Program Manager'),
    (r'project manager',           'Project Manager'),
    (r'scrum master',              'Scrum Master'),
    (r'engineering manager',       'Engineering Manager'),
    (r'technical lead',            'Technical Lead'),
    (r'\btech lead\b',             'Technical Lead'),
    (r'team lead',                 'Team Lead'),
    (r'senior manager',            'Senior Manager'),
    (r'research scientist',        'Research Scientist'),
    (r'research engineer',         'Research Engineer'),
    (r'applied scientist',         'Applied Scientist'),
    (r'generative ai',             'Generative AI Engineer'),
    (r'llm engineer',              'Generative AI Engineer'),
    (r'management consultant',     'Management Consultant'),
    (r'technology consultant',     'Technology Consultant'),
    (r'business analyst',          'Business Analyst'),
    (r'analyst',                   'Analyst'),
    (r'engineer',                  'Engineer'),
    (r'developer',                 'Developer'),
    (r'architect',                 'Architect'),
    (r'scientist',                 'Scientist'),
    (r'\bmanager\b',               'Manager'),
    (r'lead\b',                    'Lead'),
    (r'specialist',                'Specialist'),
    (r'consultant',                'Consultant'),
]

def cluster_title(normalized: str):
    for pattern, label in CLUSTER_RULES:
        if re.search(pattern, normalized):
            return label
    return None

# ─── Better skill extraction from skills_raw ──────────────────────────────────
def extract_skills_from_raw(skills_raw: str) -> list:
    """
    Insert spaces before camelCase transitions and known skill prefixes,
    then run SkillMatcher on the result.
    """
    if not skills_raw:
        return []
    # Insert spaces at camelCase boundaries
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', skills_raw)
    # Insert spaces before known tech words that may be concatenated
    for tech in ['React', 'Node', 'Angular', 'Vue', 'Docker', 'Kubernetes',
                 'Spring', 'Django', 'Flask', 'Redis', 'MongoDB', 'Postgres',
                 'Python', 'JavaScript', 'TypeScript', 'GraphQL', 'FastAPI',
                 'AWS', 'Azure', 'GCP', 'Linux', 'Jenkins', 'Kafka', 'Spark',
                 'TensorFlow', 'PyTorch', 'Scikit', 'Pandas', 'NumPy', 'Git',
                 'GitHub', 'GitLab', 'SQL', 'MySQL', 'Oracle', 'Java', 'Scala',
                 'Golang', 'Kotlin', 'Swift', 'Flutter', 'Tableau', 'Power']:
        text = re.sub(f'([a-zA-Z0-9])({re.escape(tech)})', r'\1 \2', text)
    # Replace semicolons and other delimiters with spaces
    text = re.sub(r'[;,|]', ' ', text)
    # Clean up
    text = re.sub(r'\s+', ' ', text).strip()
    
    matched = matcher.extract_skills(text)
    return [m.skill for m in matched] if matched else []


print("Aggregating with improved skill extraction...")

cluster_data = defaultdict(lambda: {
    "skill_counts": Counter(),
    "salaries": [],
    "posting_count": 0,
})

total_matched = 0
for job in jobs:
    raw_title = job.get("job_title", "") or ""
    norm = normalize_title(raw_title)
    label = cluster_title(norm)
    if not label:
        continue
    total_matched += 1
    cluster_data[label]["posting_count"] += 1

    # Combine existing skills_matched + re-extracted from skills_raw
    skill_set = set(job.get("skills_matched") or [])
    raw_skills = extract_skills_from_raw(job.get("skills_raw") or "")
    skill_set.update(raw_skills)
    for sk in skill_set:
        if sk:
            cluster_data[label]["skill_counts"][sk] += 1

    sal_min = job.get("salary_min_lpa")
    sal_max = job.get("salary_max_lpa")
    if sal_min is not None and sal_max is not None:
        cluster_data[label]["salaries"].append((sal_min + sal_max) / 2)
    elif sal_min is not None:
        cluster_data[label]["salaries"].append(sal_min)
    elif sal_max is not None:
        cluster_data[label]["salaries"].append(sal_max)

print(f"Matched {total_matched:,} jobs, {len(cluster_data)} clusters")

# Build market_roles docs
market_roles = []
for label, data in cluster_data.items():
    if data["posting_count"] < 10:
        continue
    total = data["posting_count"]
    min_freq = max(5, int(total * 0.06))
    top_skills = [sk for sk, cnt in data["skill_counts"].most_common(40) if cnt >= min_freq]
    required_skills = top_skills[:30]
    skill_freqs = {sk: round(cnt/total, 3) for sk, cnt in data["skill_counts"].most_common(30) if cnt >= min_freq}
    salaries = data["salaries"]
    median_sal = round(statistics.median(salaries), 2) if salaries else None

    market_roles.append({
        "catalog_source": "market",
        "title": label,
        "combined_required_skills": required_skills,
        "skill_frequencies": skill_freqs,
        "market_posting_count": total,
        "market_median_salary_lpa": median_sal,
        "salary_sample_count": len(salaries),
        "onet_soc_code": None,
    })

market_roles.sort(key=lambda x: x["market_posting_count"], reverse=True)

# O*NET cross-ref
ONET_CROSSREF = {
    "Data Scientist": "15-2051.00",
    "Data Analyst": "15-2041.01",
    "Business Analyst": "13-1111.00",
    "Software Developer": "15-1252.00",
    "Software Engineer": "15-1252.00",
    "Senior Software Engineer": "15-1252.00",
    "Full Stack Developer": "15-1252.00",
    "Backend Developer": "15-1252.00",
    "Frontend Developer": "15-1254.00",
    "Web Developer": "15-1254.00",
    "Machine Learning Engineer": "15-2051.00",
    "Data Engineer": "15-1243.01",
    "DevOps Engineer": "15-1244.00",
    "Cloud Engineer": "15-1241.01",
    "Database Administrator": "15-1245.00",
    "QA Engineer": "15-1253.00",
    "Security Engineer": "15-1212.00",
    "Security Analyst": "15-1212.00",
    "Product Manager": "11-3021.00",
    "Business Intelligence Analyst": "15-2051.02",
    "Analytics Engineer": "15-2041.01",
}
for r in market_roles:
    r["onet_soc_code"] = ONET_CROSSREF.get(r["title"])

# Write to market_roles
db.market_roles.drop()
if market_roles:
    db.market_roles.insert_many(market_roles)
db.market_roles.create_index("title")
db.market_roles.create_index("combined_required_skills")
db.market_roles.create_index([("market_posting_count", -1)])

print(f"\nInserted {len(market_roles)} market role documents")

# Spot-check key roles
print("\n=== Spot-check: skills for key roles ===")
for title in ['Full Stack Developer', 'Software Engineer', 'Machine Learning Engineer',
              'Data Scientist', 'Backend Developer', 'Frontend Developer', 'DevOps Engineer',
              'Data Engineer']:
    r = next((x for x in market_roles if x["title"] == title), None)
    if r:
        count = r["market_posting_count"]
        sal = r.get("market_median_salary_lpa")
        skills = r["combined_required_skills"]
        print(f"\n{title} ({count} postings, ₹{sal}L):")
        print(f"  {skills[:15]}")
    else:
        print(f"\n{title}: NOT FOUND")

print("\nREBUILD COMPLETE")
