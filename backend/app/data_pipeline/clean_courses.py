import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from pymongo.database import Database
from pymongo import ASCENDING

from app.config import settings
from app.data_pipeline.skill_matcher import SkillMatcher

def strip_currency(text: Optional[str]) -> str:
    if not text or pd.isna(text):
        return ""
    clean = re.sub(r'[\$₹€£]|Rs\.?', '', str(text))
    return clean.strip()

def parse_is_paid(value: Any, default: bool = True) -> bool:
    """Parse dataset booleans safely; ``bool('False')`` is True in Python."""
    if value is None or pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "paid"}

def clean_course_datasets(db: Database, matcher: SkillMatcher) -> Dict[str, Any]:
    """
    Cleans Udemy (Data3, Data4) and Coursera (Data5) datasets, normalizes schemas,
    and loads into Mongo collection 'courses'.
    """
    data_dir = settings.DATA_RAW_DIR
    data3_path = data_dir / "Data3" / "udemy_courses.csv"
    data4_path = data_dir / "Data4" / "udemy_courses.csv"
    c_data_path = data_dir / "Data5" / "coursera-course-data.csv"
    c_detail_path = data_dir / "Data5" / "coursera-course-detail-data.csv"

    all_courses: List[dict] = []
    stats: Dict[str, Any] = {
        "udemy_large_raw": 0,
        "udemy_small_raw": 0,
        "udemy_small_deduped": 0,
        "coursera_joined": 0,
        "total_courses": 0,
        "courses_with_skills_count": 0,
        "skill_coverage_pct": 0.0
    }

    # 1. Udemy Large File (Data3)
    if data3_path.exists():
        print(f"[Course Cleaner] Processing Udemy 98K file ({data3_path.name})...")
        df3 = pd.read_csv(data3_path)
        stats["udemy_large_raw"] = len(df3)
        
        total_rows = len(df3)
        for idx, row in df3.iterrows():
            if (idx + 1) % 30000 == 0 or (idx + 1) == total_rows:
                print(f"[Course Cleaner Progress] Processed {idx + 1}/{total_rows} Udemy 98K courses...")
                
            headline = strip_currency(row.get("headline"))
            objectives = strip_currency(row.get("objectives"))
            curriculum = strip_currency(row.get("curriculum"))
            title = strip_currency(row.get("title"))
            
            # Combine text fields for skill extraction
            combined_text = f"{title}. {headline}. {objectives}. {curriculum}"
            extracted_matches = matcher.extract_skills(combined_text)
            matched_skills = list(dict.fromkeys([m.skill for m in extracted_matches]))
            
            subscribers = int(row.get("num_subscribers")) if pd.notna(row.get("num_subscribers")) else 0
            rating = float(row.get("rating")) if pd.notna(row.get("rating")) else None
            reviews = int(row.get("num_reviews")) if pd.notna(row.get("num_reviews")) else 0
            is_paid = parse_is_paid(row.get("is_paid"))
            
            doc = {
                "source": "udemy_large",
                "title": title,
                "url": str(row.get("url")) if pd.notna(row.get("url")) else "",
                "is_paid": is_paid,
                "instructor_names": str(row.get("instructor_names")) if pd.notna(row.get("instructor_names")) else "",
                "category": str(row.get("category")) if pd.notna(row.get("category")) else "",
                "headline": headline,
                "num_subscribers": subscribers,
                "rating": rating,
                "num_reviews": reviews,
                "instructional_level": str(row.get("instructional_level")) if pd.notna(row.get("instructional_level")) else "",
                "skills_matched": matched_skills,
                "price": None
            }
            all_courses.append(doc)

    # 2. Udemy Small File (Data4)
    if data4_path.exists():
        print(f"[Course Cleaner] Processing Udemy 3.6K file ({data4_path.name})...")
        df4 = pd.read_csv(data4_path)
        stats["udemy_small_raw"] = len(df4)
        df4_clean = df4.drop_duplicates().copy()
        stats["udemy_small_deduped"] = len(df4_clean)
        
        for _, row in df4_clean.iterrows():
            title = strip_currency(row.get("course_title"))
            subject = str(row.get("subject")) if pd.notna(row.get("subject")) else ""
            
            # Match skills if title/subject contains any
            extracted_matches = matcher.extract_skills(f"{title} {subject}")
            matched_skills = list(dict.fromkeys([m.skill for m in extracted_matches]))
            
            subscribers = int(row.get("num_subscribers")) if pd.notna(row.get("num_subscribers")) else 0
            reviews = int(row.get("num_reviews")) if pd.notna(row.get("num_reviews")) else 0
            price_val = float(row.get("price")) if pd.notna(row.get("price")) else None
            is_paid = parse_is_paid(row.get("is_paid"))
            
            doc = {
                "source": "udemy_small",
                "title": title,
                "url": str(row.get("url")) if pd.notna(row.get("url")) else "",
                "is_paid": is_paid,
                "instructor_names": "",
                "category": subject,
                "headline": "",
                "num_subscribers": subscribers,
                "rating": None,
                "num_reviews": reviews,
                "instructional_level": str(row.get("level")) if pd.notna(row.get("level")) else "",
                "skills_matched": matched_skills,
                "price": price_val,
                "published_timestamp": str(row.get("published_timestamp")) if pd.notna(row.get("published_timestamp")) else None
            }
            all_courses.append(doc)

    # 3. Coursera Data (Data5) — Preserving all 3,850 rows as distinct documents
    if c_data_path.exists() and c_detail_path.exists():
        print(f"[Course Cleaner] Processing Coursera joined files...")
        df_cdata = pd.read_csv(c_data_path)
        df_cdetail = pd.read_csv(c_detail_path)
        
        # Build detail lookup dictionary by normalized Name_clean
        df_cdetail["Name_clean"] = df_cdetail["Name"].astype(str).str.strip().str.lower()
        detail_map: Dict[str, dict] = {}
        for _, r in df_cdetail.iterrows():
            clean_k = r["Name_clean"]
            if clean_k and clean_k not in detail_map:
                detail_map[clean_k] = r.to_dict()

        stats["coursera_joined"] = len(df_cdata)
        
        for _, row in df_cdata.iterrows():
            orig_name = str(row.get("Name")).strip() if pd.notna(row.get("Name")) else ""
            link = str(row.get("Link")) if pd.notna(row.get("Link")) else (str(row.get("Url")) if pd.notna(row.get("Url")) else "")
            
            # Lookup detail metadata by normalized base name
            base_name_clean = re.sub(r'\s*\([^()]*\)\s*$', '', orig_name).strip().lower()
            detail_row = detail_map.get(base_name_clean)
            if not detail_row:
                detail_row = detail_map.get(orig_name.lower())
                
            rating = None
            diff = None
            raw_tags: List[str] = []
            
            if detail_row:
                rating = float(detail_row.get("Rating")) if pd.notna(detail_row.get("Rating")) else None
                diff = str(detail_row.get("Difficulty")).strip() if pd.notna(detail_row.get("Difficulty")) else None
                tags_raw_str = detail_row.get("Tags")
                if pd.notna(tags_raw_str):
                    try:
                        parsed = ast.literal_eval(str(tags_raw_str))
                        if isinstance(parsed, list):
                            raw_tags = [str(t).strip() for t in parsed if str(t).strip()]
                    except Exception:
                        pass
                    
            matched_skills: List[str] = []
            for tag in raw_tags:
                d = matcher.match_direct(tag)
                if d and d.skill not in matched_skills:
                    matched_skills.append(d.skill)
                    
            # Fallback title extract if matched_skills empty
            if not matched_skills and orig_name:
                extracted = matcher.extract_skills(orig_name)
                matched_skills = list(dict.fromkeys([m.skill for m in extracted]))
                
            doc = {
                "source": "coursera",
                "title": orig_name,
                "url": link,
                "is_paid": True,
                "instructor_names": "",
                "category": ", ".join(raw_tags),
                "headline": "",
                "num_subscribers": 0,
                "rating": rating,
                "num_reviews": 0,
                "instructional_level": diff,
                "skills_matched": matched_skills,
                "price": None,
                "tags_raw": raw_tags
            }
            all_courses.append(doc)

    # Insert into Mongo 'courses' collection
    collection = db["courses"]
    collection.delete_many({})
    if all_courses:
        chunk_size = 5000
        for i in range(0, len(all_courses), chunk_size):
            chunk = [dict(r) for r in all_courses[i : i + chunk_size]]
            for r in chunk:
                r.pop("_id", None)
            collection.insert_many(chunk)
            
        collection.create_index([("skills_matched", ASCENDING)])
        collection.create_index([("source", ASCENDING)])

    stats["total_courses"] = len(all_courses)
    courses_with_skills = sum(1 for c in all_courses if c["skills_matched"])
    stats["courses_with_skills_count"] = courses_with_skills
    stats["skill_coverage_pct"] = round((courses_with_skills / len(all_courses)) * 100, 2) if all_courses else 0.0

    return stats
