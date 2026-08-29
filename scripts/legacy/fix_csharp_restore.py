"""
RESTORE + FIX: C# filter was too aggressive due to regex word-boundary bug.
The pattern \\bc#\\b doesn't match "c#" because '#' is not a word character.
Correct pattern: c# (no word boundary needed since # ends the token anyway).

This script:
1. Restores C# tag to courses whose title contains "c#" (case-insensitive) 
   AND were stripped in the previous run (they no longer have C# in skills_matched).
2. Re-runs the sanity pass with a corrected C# filter to catch only the truly bad ones.
"""
import sys, re
sys.path.insert(0, r'd:\switchback\backend')
sys.stdout.reconfigure(encoding='utf-8')
from app.db.mongo_client import get_db
db = get_db()

# Step 1: Restore C# tag for courses with "c#" in their title/headline
# that were stripped (i.e., no longer have "C#" in skills_matched)
print("Step 1: Restoring C# tag to courses with 'c#' in title/headline...")

cursor = db.courses.find(
    {
        "title": {"$regex": "c#", "$options": "i"},
        "skills_matched": {"$ne": "C#"}
    },
    {"_id": 1, "title": 1}
)
restore_ids = []
for doc in cursor:
    restore_ids.append(doc["_id"])

print(f"  Found {len(restore_ids)} courses with 'c#' in title but missing C# tag")

if restore_ids:
    batch_size = 500
    restored = 0
    for i in range(0, len(restore_ids), batch_size):
        batch = restore_ids[i:i + batch_size]
        result = db.courses.update_many(
            {"_id": {"$in": batch}},
            {"$addToSet": {"skills_matched": "C#"}}
        )
        restored += result.modified_count
    print(f"  Restored C# tag to {restored} courses")

# Also restore for courses with "c sharp" or "csharp" in title
for pat in ["c sharp", "csharp"]:
    cursor2 = db.courses.find(
        {"title": {"$regex": pat, "$options": "i"}, "skills_matched": {"$ne": "C#"}},
        {"_id": 1}
    )
    extra_ids = [d["_id"] for d in cursor2]
    if extra_ids:
        db.courses.update_many(
            {"_id": {"$in": extra_ids}},
            {"$addToSet": {"skills_matched": "C#"}}
        )
        print(f"  Restored C# for {len(extra_ids)} courses with '{pat}' in title")

# Step 2: Now re-apply the CORRECTED sanity filter for C#
# The fixed filter: title OR headline must mention c# / .net / unity / xamarin etc.
CORRECTED_CSHARP_PATTERNS = [
    r"c#", r"c sharp", r"csharp",              # The language name (no word boundary needed)
    r"\.net", r"asp\.net",                      # .NET ecosystem
    r"\bunity\b", r"\bxamarin\b", r"\bblazor\b",
    r"\bwpf\b", r"\bwinforms\b", r"\bmonogame\b",
    r"visual studio",
    r"\bselenium\b",                            # Selenium with C# is common
    r"game develop",
]

print("\nStep 2: Re-applying corrected C# sanity filter...")
total_tagged = db.courses.count_documents({"skills_matched": "C#"})
print(f"  Current C# tagged count: {total_tagged}")

bad_ids_2 = []
sample_bad_2 = []
for doc in db.courses.find({"skills_matched": "C#"}, {"_id": 1, "title": 1, "headline": 1}):
    title = doc.get("title", "") or ""
    headline = doc.get("headline", "") or ""
    combined = (title + " " + headline).lower()
    if not any(re.search(p, combined, re.IGNORECASE) for p in CORRECTED_CSHARP_PATTERNS):
        bad_ids_2.append(doc["_id"])
        if len(sample_bad_2) < 5:
            sample_bad_2.append(title[:70])

print(f"  Still spurious after corrected filter: {len(bad_ids_2)}")
for s in sample_bad_2:
    print(f"    BAD: [{s}]")

if bad_ids_2:
    batch_size = 500
    stripped2 = 0
    for i in range(0, len(bad_ids_2), batch_size):
        batch = bad_ids_2[i:i + batch_size]
        result = db.courses.update_many(
            {"_id": {"$in": batch}},
            {"$pull": {"skills_matched": "C#"}}
        )
        stripped2 += result.modified_count
    print(f"  Stripped spurious C# tag from {stripped2} courses")

final_count = db.courses.count_documents({"skills_matched": "C#"})
print(f"\nFinal C# course count: {final_count}")

# Verify a few spot samples
print("\nSample C# courses after fix:")
for c in db.courses.find({"skills_matched": "C#"}, {"title": 1}).sort("rating", -1).limit(8):
    print(f"  {c.get('title','?')[:70]}")

print("\nDone.")
