"""Check if C# filter erroneously removed legitimate C# courses."""
import sys, re
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

patterns = [r'\bc#\b', r'\bc sharp\b', r'csharp', r'\.net', r'asp\.net',
            r'unity', r'xamarin', r'monogame', r'winforms', r'wpf', r'blazor',
            r'microsoft.*develop', r'game develop', r'programming.*c#']

# Find courses that used to have C# but now don't (approximately: title contains "c#" but not in skills_matched)
import re as _re
samples = list(db.courses.find({"title": {"$regex": "c#", "$options": "i"}}, {"title": 1, "headline": 1, "skills_matched": 1}).limit(20))
print("Courses with 'c#' in title and their current skills_matched (checking if incorrectly stripped):")
for s in samples:
    t = s.get('title','')
    h = s.get('headline','') or ''
    combined = (t + ' ' + h).lower()
    matched_patterns = [p for p in patterns if re.search(p, combined, re.IGNORECASE)]
    still_tagged = "C#" in (s.get('skills_matched') or [])
    print(f"  Title: {t[:70]}")
    print(f"  Patterns matched: {matched_patterns}")
    print(f"  Still tagged C#: {still_tagged}")
    print()
