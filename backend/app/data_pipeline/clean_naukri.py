import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from pymongo.database import Database
from pymongo import TEXT, ASCENDING

from app.config import settings
from app.data_pipeline.skill_matcher import SkillMatcher
from app.data_pipeline.segment_concatenated import segment_concatenated

ACRONYMS = {"SQL", "AI", "ML", "BI", "AWS", "GCP", "ETL", "NLP", "CV", "LLM", "RAG", "QA", "HR", "IT", "UI", "UX", "API", "SDK"}

def normalize_job_title(title_str: Optional[str]) -> str:
    if not title_str or pd.isna(title_str):
        return ""
    words = str(title_str).strip().split()
    norm_words = []
    for w in words:
        w_clean = re.sub(r'[^\w\+\#\.-]', '', w)
        w_upper = w_clean.upper()
        if w_upper in ACRONYMS:
            norm_words.append(w_upper)
        else:
            norm_words.append(w.capitalize())
    return " ".join(norm_words)

def parse_experience(exp_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not exp_str or pd.isna(exp_str):
        return None, None
    s = str(exp_str).strip()
    m_range = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', s)
    if m_range:
        return float(m_range.group(1)), float(m_range.group(2))
    m_single = re.search(r'(\d+(?:\.\d+)?)', s)
    if m_single:
        val = float(m_single.group(1))
        return val, val
    return None, None

def parse_salary(salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float], bool]:
    if not salary_str or pd.isna(salary_str):
        return None, None, False
    s = str(salary_str).strip()
    s_lower = s.lower()
    
    if any(k in s_lower for k in ["not disclosed", "unpaid", "best in", "disclosed by recruiter"]):
        return None, None, False
        
    m_lacs = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(?:lacs|lakhs|lac|lakh)', s_lower)
    if m_lacs:
        return float(m_lacs.group(1)), float(m_lacs.group(2)), True
        
    m_lac_single = re.search(r'(\d+(?:\.\d+)?)\s*(?:lacs|lakhs|lac|lakh)', s_lower)
    if m_lac_single:
        val = float(m_lac_single.group(1))
        return val, val, True

    m_num_range = re.search(r'([\d,]+)\s*-\s*([\d,]+)', s)
    if m_num_range:
        n1 = float(m_num_range.group(1).replace(",", ""))
        n2 = float(m_num_range.group(2).replace(",", ""))
        if n1 > 1000:
            n1 = round(n1 / 100000.0, 2)
            n2 = round(n2 / 100000.0, 2)
        return n1, n2, True

    return None, None, False

def parse_locations(loc_str: Optional[str]) -> List[str]:
    if not loc_str or pd.isna(loc_str):
        return []
    parts = re.split(r'[,;/|]+', str(loc_str))
    return [p.strip() for p in parts if p.strip()]

def parse_post_date(date_str: Optional[str]) -> Tuple[Optional[datetime], Optional[str]]:
    if not date_str or pd.isna(date_str):
        return None, None
    raw_s = str(date_str).strip()
    try:
        dt = pd.to_datetime(raw_s, errors='coerce')
        if pd.notna(dt):
            return dt.to_pydatetime(), raw_s
    except Exception:
        pass
    return None, raw_s

def clean_naukri_datasets(db: Database, matcher: SkillMatcher) -> Dict[str, Any]:
    """
    Cleans all 4 Naukri source files, normalizes schemas, and loads into Mongo collection 'jobs'.
    """
    data_dir = settings.DATA_RAW_DIR
    data1_dir = data_dir / "Data1"
    data2_dir = data_dir / "Data2"
    
    file_configs = [
        {
            "path": data1_dir / "Naukri_Data_Scientist_and_Data_Analytics_Jobs_Data.csv",
            "quality": "primary",
            "cols": {
                "title": "Job Titles", "company": "Company Names", "exp": "Experience Required",
                "pkg": "Package", "loc": "Locations", "skills": "Skills",
                "url": None, "date": None
            }
        },
        {
            "path": data1_dir / "NaukriData_data analytics.csv",
            "quality": "primary",
            "cols": {
                "title": "Job_Titles", "company": "Company_Names", "exp": "Experience_Required",
                "pkg": "Package_Details", "loc": "Locations", "skills": "Skills",
                "url": "Post_Url", "date": "Post_Time"
            }
        },
        {
            "path": data1_dir / "NaukriData_Data Science.csv",
            "quality": "primary",
            "cols": {
                "title": "Job_Titles", "company": "Company_Names", "exp": "Experience_Required",
                "pkg": "Package_Details", "loc": "Locations", "skills": "Skills",
                "url": "Post_Url", "date": "Post_Time"
            }
        },
        {
            "path": data2_dir / "naukri_com-job_sample.csv",
            "quality": "supplementary",
            "cols": {
                "title": "jobtitle", "company": "company", "exp": "experience",
                "pkg": "payrate", "loc": "joblocation_address", "skills": "skills",
                "url": None, "date": "postdate", "desc": "jobdescription"
            }
        }
    ]
    
    all_documents: List[dict] = []
    stats: Dict[str, Any] = {
        "files_processed": 0,
        "total_raw_rows": 0,
        "total_deduped_rows": 0,
        "dedup_details": {},
        "top_unmatched_terms": {}
    }
    
    unmatched_term_counts: Dict[str, int] = {}

    for cfg in file_configs:
        file_path = cfg["path"]
        if not file_path.exists():
            print(f"[Naukri Cleaner Warning] File not found: {file_path}")
            continue
            
        filename = file_path.name
        df = pd.read_csv(file_path)
        raw_count = len(df)
        stats["total_raw_rows"] += raw_count
        
        # Deduplication step
        df_clean = df.drop_duplicates().copy()
        deduped_count = len(df_clean)
        dropped_dupes = raw_count - deduped_count
        stats["dedup_details"][filename] = {
            "raw": raw_count,
            "deduped": deduped_count,
            "dropped_duplicates": dropped_dupes
        }
        stats["total_deduped_rows"] += deduped_count
        
        cols = cfg["cols"]
        for _, row in df_clean.iterrows():
            job_title_raw = row.get(cols["title"]) if cols["title"] else None
            job_title = normalize_job_title(job_title_raw)
            company = str(row.get(cols["company"])).strip() if cols["company"] and pd.notna(row.get(cols["company"])) else None
            
            exp_raw = row.get(cols["exp"]) if cols["exp"] else None
            exp_min, exp_max = parse_experience(exp_raw)
            
            pkg_raw = row.get(cols["pkg"]) if cols["pkg"] else None
            sal_min, sal_max, sal_disclosed = parse_salary(pkg_raw)
            
            loc_raw = row.get(cols["loc"]) if cols["loc"] else None
            locations = parse_locations(loc_raw)
            
            skills_raw = str(row.get(cols["skills"])).strip() if cols["skills"] and pd.notna(row.get(cols["skills"])) else ""
            
            # Extract skills using segment_concatenated
            seg_res = segment_concatenated(skills_raw, matcher)
            matched_skills = seg_res["matched_skills"]
            leftover_terms = seg_res["leftover"]
            
            # If skills_raw gave no matched skills, fallback to extracting from job_title or jobdescription
            if not matched_skills and (job_title or ("desc" in cols and row.get(cols["desc"]))):
                fallback_text = job_title
                if "desc" in cols and pd.notna(row.get(cols["desc"])):
                    fallback_text += " " + str(row.get(cols["desc"]))
                fallback_matches = matcher.extract_skills(fallback_text)
                matched_skills = [m.skill for m in fallback_matches]

            for term in leftover_terms:
                t_clean = term.strip().lower()
                if len(t_clean) > 2:
                    unmatched_term_counts[t_clean] = unmatched_term_counts.get(t_clean, 0) + 1

            date_raw = row.get(cols["date"]) if cols["date"] and pd.notna(row.get(cols["date"])) else None
            post_date_dt, post_date_str = parse_post_date(date_raw)
            
            doc = {
                "source_file": filename,
                "source_quality": cfg["quality"],
                "job_title": job_title,
                "company": company,
                "experience_min_years": exp_min,
                "experience_max_years": exp_max,
                "salary_min_lpa": sal_min,
                "salary_max_lpa": sal_max,
                "salary_disclosed": sal_disclosed,
                "locations": locations,
                "skills_raw": skills_raw,
                "skills_matched": matched_skills,
                "post_date_parsed": post_date_dt,
                "post_date_raw": post_date_str,
            }
            if cfg["quality"] == "supplementary":
                doc["payrate_raw"] = str(pkg_raw) if pd.notna(pkg_raw) else None

            all_documents.append(doc)
            
        stats["files_processed"] += 1

    # Insert into Mongo 'jobs' collection
    collection = db["jobs"]
    collection.delete_many({})
    if all_documents:
        # Insert in chunks of 5000
        chunk_size = 5000
        for i in range(0, len(all_documents), chunk_size):
            collection.insert_many(all_documents[i : i + chunk_size])
            
        # Create indices
        collection.create_index([("job_title", TEXT)])
        collection.create_index([("skills_matched", ASCENDING)])
        collection.create_index([("source_quality", ASCENDING)])

    # Top unmatched terms
    top_unmatched = sorted(unmatched_term_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    stats["top_unmatched_terms"] = top_unmatched
    stats["inserted_count"] = len(all_documents)
    
    # Calculate coverage
    jobs_with_skills = sum(1 for d in all_documents if d["skills_matched"])
    stats["jobs_with_skills_count"] = jobs_with_skills
    stats["skill_coverage_pct"] = round((jobs_with_skills / len(all_documents)) * 100, 2) if all_documents else 0.0

    return stats
