"""
PART E: Build Naukri-native market role catalog from jobs collection.

Algorithm:
1. Load all primary-quality jobs with job_title + skills_matched + salary fields
2. Normalize titles: lowercase, strip punctuation, remove company suffixes,
   canonical-form common variants (senior/sr -> senior, etc.)
3. Cluster via keyword extraction: map each normalized title to a canonical 
   cluster label using keyword priority matching (rules-based, not ML)
4. For each cluster: aggregate skill frequencies, compute median salary,
   count postings
5. Write to market_roles collection

Run: $env:PYTHONIOENCODING='utf-8'; python d:\switchback\build_market_roles.py
"""
import sys, re
from collections import defaultdict, Counter
import statistics

sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

# ─── Step 1: Load all primary jobs ───────────────────────────────────────────
print("Loading primary-quality jobs...")
jobs = list(db.jobs.find(
    {"source_quality": "primary"},
    {
        "job_title": 1,
        "skills_matched": 1,
        "salary_min_lpa": 1,
        "salary_max_lpa": 1,
        "salary_disclosed": 1,
        "experience_min_years": 1,
        "experience_max_years": 1,
    }
))
print(f"Loaded {len(jobs)} jobs")

# ─── Step 2: Title normalization ──────────────────────────────────────────────
def normalize_title(raw: str) -> str:
    if not raw:
        return ""
    t = raw.lower().strip()
    # Remove parenthetical/bracketed noise
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\(.*?\)', '', t)
    # Remove common suffixes
    t = re.sub(r'\s*[-–|/].*$', '', t)  # strip after dash/pipe/slash
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    # Expand abbreviations
    t = re.sub(r'\bsr\.?\b', 'senior', t)
    t = re.sub(r'\bjr\.?\b', 'junior', t)
    t = re.sub(r'\bmgr\.?\b', 'manager', t)
    t = re.sub(r'\bdev\b', 'developer', t)
    t = re.sub(r'\beng\b', 'engineer', t)
    t = re.sub(r'\bspec\b', 'specialist', t)
    t = re.sub(r'\banalyt\b', 'analytics', t)
    return t

# ─── Step 3: Cluster rules — ordered by specificity (most-specific first) ────
# Each rule: (keyword pattern, canonical_label)
# A title is assigned to the FIRST matching rule.
CLUSTER_RULES = [
    # ML/AI/Data Science variants
    (r'machine learning engineer',          'Machine Learning Engineer'),
    (r'ml engineer',                        'Machine Learning Engineer'),
    (r'ai engineer',                        'Machine Learning Engineer'),
    (r'deep learning engineer',             'Machine Learning Engineer'),
    (r'nlp engineer',                       'NLP Engineer'),
    (r'nlp scientist',                      'NLP Engineer'),
    (r'computer vision engineer',           'Computer Vision Engineer'),
    (r'data science lead',                  'Data Science Lead'),
    (r'head.*data science',                 'Data Science Lead'),
    (r'data science manager',               'Data Science Manager'),
    (r'principal data scientist',           'Principal Data Scientist'),
    (r'lead data scientist',                'Lead Data Scientist'),
    (r'senior data scientist',              'Senior Data Scientist'),
    (r'data scientist',                     'Data Scientist'),
    (r'data science',                       'Data Scientist'),
    # Analytics
    (r'senior.*data analyst',               'Senior Data Analyst'),
    (r'data analyst',                       'Data Analyst'),
    (r'analytics engineer',                 'Analytics Engineer'),
    (r'business analyst',                   'Business Analyst'),
    (r'business intelligence',              'Business Intelligence Analyst'),
    (r'product analyst',                    'Product Analyst'),
    (r'marketing analyst',                  'Marketing Analyst'),
    (r'financial analyst',                  'Financial Analyst'),
    (r'quantitative analyst',               'Quantitative Analyst'),
    (r'risk analyst',                       'Risk Analyst'),
    (r'operations analyst',                 'Operations Analyst'),
    # Data Engineering
    (r'senior data engineer',               'Senior Data Engineer'),
    (r'data engineer',                      'Data Engineer'),
    (r'data platform engineer',             'Data Engineer'),
    (r'etl developer',                      'Data Engineer'),
    (r'etl engineer',                       'Data Engineer'),
    # Software Engineering — specializations
    (r'full.?stack developer',              'Full Stack Developer'),
    (r'full.?stack engineer',               'Full Stack Developer'),
    (r'full stack',                         'Full Stack Developer'),
    (r'backend developer',                  'Backend Developer'),
    (r'backend engineer',                   'Backend Developer'),
    (r'back.?end developer',                'Backend Developer'),
    (r'back.?end engineer',                 'Backend Developer'),
    (r'frontend developer',                 'Frontend Developer'),
    (r'frontend engineer',                  'Frontend Developer'),
    (r'front.?end developer',               'Frontend Developer'),
    (r'front.?end engineer',                'Frontend Developer'),
    (r'react developer',                    'Frontend Developer'),
    (r'angular developer',                  'Frontend Developer'),
    (r'vue developer',                      'Frontend Developer'),
    (r'ui developer',                       'Frontend Developer'),
    (r'ux developer',                       'Frontend Developer'),
    (r'web developer',                      'Web Developer'),
    (r'mobile developer',                   'Mobile App Developer'),
    (r'android developer',                  'Android Developer'),
    (r'ios developer',                      'iOS Developer'),
    (r'flutter developer',                  'Mobile App Developer'),
    (r'react native developer',             'Mobile App Developer'),
    (r'java developer',                     'Java Developer'),
    (r'java engineer',                      'Java Developer'),
    (r'python developer',                   'Python Developer'),
    (r'python engineer',                    'Python Developer'),
    (r'node\.?js developer',               'Node.js Developer'),
    (r'node developer',                     'Node.js Developer'),
    (r'\.net developer',                    '.NET Developer'),
    (r'dotnet developer',                   '.NET Developer'),
    (r'c# developer',                       '.NET Developer'),
    (r'c\+\+ developer',                    'C++ Developer'),
    (r'php developer',                      'PHP Developer'),
    (r'golang developer',                   'Go Developer'),
    (r'go developer',                       'Go Developer'),
    (r'rust developer',                     'Rust Developer'),
    (r'scala developer',                    'Scala Developer'),
    (r'kotlin developer',                   'Android Developer'),
    (r'swift developer',                    'iOS Developer'),
    (r'r developer',                        'R Developer'),
    (r'senior software engineer',           'Senior Software Engineer'),
    (r'senior software developer',          'Senior Software Engineer'),
    (r'principal engineer',                 'Principal Software Engineer'),
    (r'staff engineer',                     'Staff Software Engineer'),
    (r'software engineer',                  'Software Engineer'),
    (r'software developer',                 'Software Developer'),
    (r'software development engineer',      'Software Engineer'),
    (r'application developer',              'Software Developer'),
    # Cloud / DevOps / Infra
    (r'devops engineer',                    'DevOps Engineer'),
    (r'devsecops',                          'DevSecOps Engineer'),
    (r'site reliability engineer',          'Site Reliability Engineer'),
    (r'\bsre\b',                            'Site Reliability Engineer'),
    (r'platform engineer',                  'Platform Engineer'),
    (r'infrastructure engineer',            'Infrastructure Engineer'),
    (r'cloud engineer',                     'Cloud Engineer'),
    (r'aws engineer',                       'Cloud Engineer'),
    (r'azure engineer',                     'Cloud Engineer'),
    (r'gcp engineer',                       'Cloud Engineer'),
    (r'cloud architect',                    'Cloud Architect'),
    (r'solutions architect',                'Solutions Architect'),
    (r'enterprise architect',               'Enterprise Architect'),
    # Database
    (r'database administrator',             'Database Administrator'),
    (r'\bdba\b',                            'Database Administrator'),
    (r'database engineer',                  'Database Engineer'),
    (r'database developer',                 'Database Engineer'),
    # QA / Testing
    (r'test engineer',                      'QA Engineer'),
    (r'qa engineer',                        'QA Engineer'),
    (r'quality assurance engineer',         'QA Engineer'),
    (r'automation engineer',                'QA Automation Engineer'),
    (r'automation test',                    'QA Automation Engineer'),
    (r'sdet\b',                             'QA Automation Engineer'),
    # Cybersecurity
    (r'security engineer',                  'Security Engineer'),
    (r'security analyst',                   'Security Analyst'),
    (r'cybersecurity',                      'Security Analyst'),
    (r'information security',               'Security Analyst'),
    (r'penetration tester',                 'Penetration Tester'),
    (r'\bpent[e]?st',                       'Penetration Tester'),
    # Product / Management
    (r'product manager',                    'Product Manager'),
    (r'product owner',                      'Product Manager'),
    (r'program manager',                    'Program Manager'),
    (r'project manager',                    'Project Manager'),
    (r'scrum master',                       'Scrum Master'),
    (r'agile coach',                        'Agile Coach'),
    (r'delivery manager',                   'Delivery Manager'),
    # Design / UX
    (r'ux designer',                        'UX Designer'),
    (r'ui designer',                        'UX Designer'),
    (r'ux researcher',                      'UX Researcher'),
    (r'product designer',                   'Product Designer'),
    (r'graphic designer',                   'Graphic Designer'),
    # Management (tech)
    (r'engineering manager',                'Engineering Manager'),
    (r'technology manager',                 'Technology Manager'),
    (r'vp engineering',                     'VP of Engineering'),
    (r'vp of engineering',                  'VP of Engineering'),
    (r'cto\b',                              'Chief Technology Officer'),
    (r'chief technology',                   'Chief Technology Officer'),
    (r'technical lead',                     'Technical Lead'),
    (r'\btech lead\b',                      'Technical Lead'),
    (r'team lead',                          'Team Lead'),
    (r'senior manager',                     'Senior Manager'),
    (r'\bmanager\b',                        'Manager'),
    # Research
    (r'research scientist',                 'Research Scientist'),
    (r'research engineer',                  'Research Engineer'),
    (r'applied scientist',                  'Applied Scientist'),
    # GenAI / LLM specific (modern)
    (r'generative ai',                      'Generative AI Engineer'),
    (r'llm engineer',                       'Generative AI Engineer'),
    (r'ai.*developer',                      'AI Developer'),
    # Consulting / Strategy
    (r'management consultant',              'Management Consultant'),
    (r'strategy consultant',               'Strategy Consultant'),
    (r'technology consultant',             'Technology Consultant'),
    (r'consultant',                         'Consultant'),
    # Support / Ops
    (r'data scientist.*intern',             'Data Science Intern'),
    (r'software engineer.*intern',          'Software Engineering Intern'),
    (r'intern',                             'Intern'),
    # Catch-alls
    (r'analyst',                            'Analyst'),
    (r'engineer',                           'Engineer'),
    (r'developer',                          'Developer'),
    (r'architect',                          'Architect'),
    (r'scientist',                          'Scientist'),
    (r'manager',                            'Manager'),
    (r'lead\b',                             'Lead'),
    (r'specialist',                         'Specialist'),
    (r'consultant',                         'Consultant'),
]

def cluster_title(normalized: str) -> str | None:
    for pattern, label in CLUSTER_RULES:
        if re.search(pattern, normalized):
            return label
    return None

# ─── Step 4: Aggregate ────────────────────────────────────────────────────────
print("Clustering titles and aggregating skills...")
cluster_data = defaultdict(lambda: {
    "skill_counts": Counter(),
    "salaries": [],
    "posting_count": 0,
    "raw_title_samples": Counter(),
})

unmatched = Counter()
total_matched = 0

for job in jobs:
    raw_title = job.get("job_title", "") or ""
    norm = normalize_title(raw_title)
    label = cluster_title(norm)
    
    if not label:
        unmatched[norm[:60]] += 1
        continue
    
    total_matched += 1
    cluster_data[label]["posting_count"] += 1
    cluster_data[label]["raw_title_samples"][raw_title] += 1
    
    # Aggregate skills
    for sk in (job.get("skills_matched") or []):
        if sk:
            cluster_data[label]["skill_counts"][sk] += 1
    
    # Aggregate salary (use midpoint of min/max if available)
    sal_min = job.get("salary_min_lpa")
    sal_max = job.get("salary_max_lpa")
    if sal_min is not None and sal_max is not None:
        cluster_data[label]["salaries"].append((sal_min + sal_max) / 2)
    elif sal_min is not None:
        cluster_data[label]["salaries"].append(sal_min)
    elif sal_max is not None:
        cluster_data[label]["salaries"].append(sal_max)

print(f"  Matched {total_matched:,} jobs ({100*total_matched/len(jobs):.1f}%)")
print(f"  Clusters formed: {len(cluster_data)}")
print(f"  Top 10 unmatched titles:")
for title, cnt in unmatched.most_common(10):
    print(f"    {cnt:>4}  {title}")

# ─── Step 5: Build market_roles documents ────────────────────────────────────
print("\nBuilding market_roles collection...")

market_roles = []
for label, data in cluster_data.items():
    if data["posting_count"] < 10:
        continue  # Skip tiny clusters
    
    skill_counts = data["skill_counts"]
    total_postings = data["posting_count"]
    
    # Required skills: top skills by frequency, but only if they appear
    # in at least 10% of postings in this cluster
    min_freq_threshold = max(5, int(total_postings * 0.08))
    top_skills = [
        sk for sk, cnt in skill_counts.most_common(50)
        if cnt >= min_freq_threshold
    ]
    # Cap at 30 skills max, keep at least 5
    required_skills = top_skills[:30]
    
    # Skill frequency ratios (for IDF computation later)
    skill_frequencies = {
        sk: round(cnt / total_postings, 3)
        for sk, cnt in skill_counts.most_common(30)
        if cnt >= min_freq_threshold
    }
    
    # Median salary
    salaries = data["salaries"]
    median_salary = round(statistics.median(salaries), 2) if salaries else None
    
    # Sample titles
    sample_titles = [t for t, _ in data["raw_title_samples"].most_common(3)]
    
    market_roles.append({
        "catalog_source": "market",
        "title": label,
        "combined_required_skills": required_skills,
        "skill_frequencies": skill_frequencies,
        "market_posting_count": total_postings,
        "market_median_salary_lpa": median_salary,
        "salary_sample_count": len(salaries),
        "sample_raw_titles": sample_titles,
        "onet_soc_code": None,  # Will be cross-referenced below
    })

# Sort by posting count
market_roles.sort(key=lambda x: x["market_posting_count"], reverse=True)

print(f"Market roles with >= 10 postings: {len(market_roles)}")
print("\nTop 20 market-native roles:")
for r in market_roles[:20]:
    sal = f"₹{r['market_median_salary_lpa']}L" if r['market_median_salary_lpa'] else "no salary"
    skills_sample = r["combined_required_skills"][:5]
    print(f"  {r['posting_count'] if 'posting_count' in r else r['market_posting_count']:>5}  {r['title']:<40} {sal}")
    print(f"         skills: {skills_sample}")

# ─── Step 6: Cross-reference O*NET titles ────────────────────────────────────
print("\nCross-referencing against O*NET catalog...")
ONET_CROSSREF = {
    "Data Scientist":          "15-2051.00",
    "Data Analyst":            "15-2041.01",
    "Business Analyst":        "13-1111.00",
    "Software Developer":      "15-1252.00",
    "Software Engineer":       "15-1252.00",
    "Senior Software Engineer":"15-1252.00",
    "Full Stack Developer":    "15-1252.00",
    "Backend Developer":       "15-1252.00",
    "Frontend Developer":      "15-1254.00",
    "Web Developer":           "15-1254.00",
    "Machine Learning Engineer":"15-2051.00",
    "Data Engineer":           "15-1243.01",
    "DevOps Engineer":         "15-1244.00",
    "Cloud Engineer":          "15-1241.01",
    "Cloud Architect":         "15-1241.01",
    "Database Administrator":  "15-1245.00",
    "QA Engineer":             "15-1253.00",
    "Security Engineer":       "15-1212.00",
    "Security Analyst":        "15-1212.00",
    "Product Manager":         "11-3021.00",
    "Business Intelligence Analyst": "15-2051.02",
    "Analytics Engineer":      "15-2041.01",
}
for role in market_roles:
    role["onet_soc_code"] = ONET_CROSSREF.get(role["title"])

# ─── Step 7: Write to market_roles collection ─────────────────────────────────
print("\nWriting to market_roles collection...")
db.market_roles.drop()
if market_roles:
    result = db.market_roles.insert_many(market_roles)
    print(f"Inserted {len(result.inserted_ids)} market role documents")

# Create indexes
db.market_roles.create_index("title")
db.market_roles.create_index("combined_required_skills")
db.market_roles.create_index([("market_posting_count", -1)])
print("Indexes created on market_roles")

# ─── Final summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
total_market = db.market_roles.count_documents({})
print(f"market_roles collection: {total_market} documents")
print(f"Titles with salary data: {sum(1 for r in market_roles if r['market_median_salary_lpa'])}")
print(f"Titles with >= 100 postings: {sum(1 for r in market_roles if r['market_posting_count'] >= 100)}")
print(f"Titles with >= 500 postings: {sum(1 for r in market_roles if r['market_posting_count'] >= 500)}")

print("\nAll clusters (posting_count >= 50):")
for r in market_roles:
    if r["market_posting_count"] >= 50:
        sal = f"  salary={r['market_median_salary_lpa']}L" if r["market_median_salary_lpa"] else ""
        print(f"  {r['market_posting_count']:>5}  {r['title']}{sal}")

print("\nBUILD COMPLETE")
