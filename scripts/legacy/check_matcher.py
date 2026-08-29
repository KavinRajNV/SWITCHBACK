"""
Check SkillMatcher vocabulary and re-extract skills from skills_raw for Full Stack/Software jobs.
"""
import sys, re
from collections import Counter
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()
from app.data_pipeline.skill_matcher import SkillMatcher

matcher = SkillMatcher.from_mongo(db)
print(f"Skill matcher vocabulary size: {len(matcher.skills_list)}")
print(f"Sample skills: {matcher.skills_list[:30]}")

# Check what skills exist in the matcher for web dev topics
web_skills = [s for s in matcher.skills_list if any(kw in s.lower() for kw in
    ['react', 'angular', 'vue', 'node', 'javascript', 'html', 'css', 'django',
     'flask', 'spring', 'docker', 'kubernetes', 'aws', 'git', 'mongodb', 'redis',
     'postgres', 'fastapi', 'typescript', 'graphql'])]
print(f"\nWeb/backend tech in matcher vocabulary ({len(web_skills)}):")
for s in sorted(web_skills):
    print(f"  {s}")

# Now test direct skill extraction from skills_raw for a sample Full Stack job
print("\n=== Direct extraction test ===")
sample_raws = [
    "React.jsNode.jsJavascriptHTMLCSSMongoDBRESTful APIsGitDocker",
    "PythonDjangoFlaskFastAPIMySQLPostgreSQLDockerKubernetes",
    "JavaSpring BootHibernateRESTAPIsMicroservicesKafkaRedis",
]

for raw in sample_raws:
    # Simple space-insertion heuristic for concatenated skills
    # Insert space before uppercase after lowercase
    spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw)
    # Also handle known concatenation patterns
    spaced = re.sub(r'(\w)(React|Node|Java|Python|Docker|Mongo|Redis|Kafka)', r'\1 \2', spaced)
    print(f"  Raw: {raw[:60]}")
    print(f"  Spaced: {spaced[:80]}")
    result = matcher.match_skills(spaced)
    print(f"  Matched: {result}")
    print()
