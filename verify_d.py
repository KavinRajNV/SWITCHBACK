"""Verify Part D: YouTube Excel fix — confirm no Azure content returned."""
import sys, asyncio
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
from app.api.youtube_service import _skill_matches_channel

db = get_db()

# 1. Verify the channel-matching fix directly
print("=== Part D: Channel-skill matching tests ===")
# Fetch channel docs from allowlist
all_docs = list(db.youtube_allowlist.find({}, {"channel_name": 1, "domain": 1, "primary_topics": 1}))
print(f"Total allowlisted channels: {len(all_docs)}")

test_cases = [
    ("microsoft excel", True),    # should match an Excel/Office-focused channel
    ("microsoft excel", False),   # should NOT match Microsoft Azure channel
    ("python", True),
    ("data analysis", True),
    ("apache spark", True),
]

for skill, _ in test_cases:
    matched = [d["channel_name"] for d in all_docs if _skill_matches_channel(skill, d)]
    print(f"\n  Skill: '{skill}' -> matched channels: {matched}")

# 2. Specifically check Azure channel does NOT match Excel
azure_doc = next((d for d in all_docs if "azure" in d.get("channel_name", "").lower()), None)
if azure_doc:
    result = _skill_matches_channel("microsoft excel", azure_doc)
    status = "PASS" if not result else "FAIL"
    print(f"\n[{status}] 'Microsoft Azure' channel matches 'microsoft excel': {result} (expected False)")
else:
    print("\n[INFO] No 'Microsoft Azure' channel in allowlist")

# 3. Check all channels that WOULD match 'microsoft excel'
print("\n=== Channels that match 'microsoft excel' ===")
excel_matches = [(d["channel_name"], d.get("domain",""), d.get("primary_topics","")) 
                 for d in all_docs if _skill_matches_channel("microsoft excel", d)]
if excel_matches:
    for name, domain, topics in excel_matches:
        print(f"  {name:<40} domain={domain}  topics={topics[:60]}")
else:
    print("  None — will fall back to general-tech channels (with post-fetch title filter)")

# 4. Show what the fallback general-tech channels would be
print("\n=== Fallback channels (general-tech) ===")
general_tech = [d for d in all_docs
                if any(w in str(d.get("domain", "")).lower()
                       for w in ["programming", "web", "data", "software", "computer"])]
for d in general_tech[:5]:
    print(f"  {d['channel_name']:<40} domain={d.get('domain','')}")

# 5. Show cached video for Excel (should be empty since we deleted it)
print("\n=== Excel YouTube cache state ===")
cached = db.youtube_cache.find_one({"skill_key": "microsoft excel"})
if cached:
    vids = cached.get("videos", [])
    print(f"Cache exists with {len(vids)} videos:")
    for v in vids:
        title = v.get("title", "?")
        chan = v.get("channel_title", "?")
        bad = any(w in title.lower() for w in ["azure", "copilot", "confidential", "cloud"])
        flag = "FAIL-IRRELEVANT" if bad else "OK"
        print(f"  [{flag}] [{chan}] {title[:70]}")
else:
    print("  No cache (cleared — will re-fetch with fixed logic on next request)")

print("\nPART D VERIFICATION COMPLETE")
