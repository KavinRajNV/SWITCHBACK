import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field
import httpx

from app.api.session_store import get_session, update_session
from app.models.schemas import SkillEvidence
from app.config import settings

router = APIRouter(prefix="/api/live", tags=["Live Integrations"])

CACHE_COLLECTION = "adzuna_cache"

class GitHubVerifyRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    github_username: str = Field(..., description="GitHub username to verify")

@router.get("/jobs")
async def get_live_jobs(
    request: Request,
    session_id: Optional[str] = Query(default=None, description="Optional session ID"),
    role: Optional[str] = Query(default=None, description="Job title / keyword search"),
    location: Optional[str] = Query(default="India", description="Location filter")
):
    """
    Fetches live job postings from Adzuna Job Search API with strict 3.5s timeout and MongoDB caching (30-min TTL).
    Falls back gracefully to empty cached shape on timeout or error without crashing.
    """
    db = request.app.state.db

    # Determine query role from session if not explicitly passed
    search_role = role
    if not search_role and session_id:
        sess = get_session(session_id, db=db)
        if sess:
            target_soc = sess.get("target_occupation_soc_code", "15-2051.00")
            occ = request.app.state.occupations_dict.get(target_soc)
            search_role = occ.get("title") if occ else "Data Scientist"

    if not search_role:
        search_role = "Data Scientist"

    loc_clean = location or "India"
    cache_key = f"{search_role.strip().lower()}__in"

    # 1. Check MongoDB cache first
    cached_doc = db[CACHE_COLLECTION].find_one({"cache_key": cache_key})
    if cached_doc:
        cached_at = cached_doc.get("cached_at")
        if cached_at and (datetime.now() - cached_at) < timedelta(minutes=30):
            return {
                "status": "success",
                "source": "cache",
                "query_role": search_role,
                "count": len(cached_doc.get("jobs", [])),
                "jobs": cached_doc.get("jobs", [])
            }

    # 2. Make outbound API call to Adzuna
    app_id = settings.ADZUNA_APP_ID or os.getenv("ADZUNA_APP_ID")
    app_key = settings.ADZUNA_APP_KEY or os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        return {
            "status": "unavailable",
            "source": "fallback",
            "message": "Adzuna API credentials not configured in environment.",
            "jobs": []
        }

    url = f"https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": search_role,
        "results_per_page": 10
    }

    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                raw_results = data.get("results", [])
                jobs_formatted = [
                    {
                        "job_id": str(j.get("id")),
                        "title": j.get("title", "").replace("<strong>", "").replace("</strong>", ""),
                        "company": j.get("company", {}).get("display_name", "Unknown Employer"),
                        "location": j.get("location", {}).get("display_name", "India"),
                        "description": j.get("description", "")[:250] + "...",
                        "redirect_url": j.get("redirect_url", "#"),
                        "salary_min": j.get("salary_min"),
                        "salary_max": j.get("salary_max"),
                        "created": j.get("created")
                    }
                    for j in raw_results
                ]

                # Store in MongoDB cache
                db[CACHE_COLLECTION].update_one(
                    {"cache_key": cache_key},
                    {"$set": {
                        "cache_key": cache_key,
                        "query_role": search_role,
                        "cached_at": datetime.now(),
                        "jobs": jobs_formatted
                    }},
                    upsert=True
                )

                return {
                    "status": "success",
                    "source": "live_api",
                    "query_role": search_role,
                    "count": len(jobs_formatted),
                    "jobs": jobs_formatted
                }

    except Exception as e:
        print(f"[Adzuna Integration Warning] Live request failed: {e}")

    # Fallback to expired cache or empty list if API call failed/timed out
    if cached_doc:
        return {
            "status": "degraded",
            "source": "expired_cache",
            "query_role": search_role,
            "count": len(cached_doc.get("jobs", [])),
            "jobs": cached_doc.get("jobs", [])
        }

    return {
        "status": "unavailable",
        "source": "fallback",
        "message": "Adzuna Job Search API currently unreachable or timed out.",
        "jobs": []
    }

@router.post("/github-verify")
async def verify_github_skills(req_data: GitHubVerifyRequest, request: Request):
    """
    Calls GitHub REST API to extract public repositories and language metrics,
    mapping programming languages to canonical skills and setting confidence = 9 (github_verified tier).
    """
    db = request.app.state.db
    matcher = request.app.state.matcher
    token = settings.GITHUB_TOKEN or os.getenv("GITHUB_TOKEN")

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    username = req_data.github_username.strip()
    user_url = f"https://api.github.com/users/{username}/repos"

    verified_skills: List[str] = []
    language_counts: Dict[str, int] = {}

    try:
        async with httpx.AsyncClient(timeout=3.5) as client:
            resp = await client.get(user_url, headers=headers, params={"type": "owner", "per_page": 20})
            if resp.status_code == 200:
                repos = resp.json()
                for repo in repos:
                    lang = repo.get("language")
                    if lang:
                        language_counts[lang] = language_counts.get(lang, 0) + 1

    except Exception as e:
        print(f"[GitHub Verification Warning] API call failed: {e}")
        return {
            "status": "unavailable",
            "message": f"GitHub API request failed or timed out: {e}",
            "verified_skills": []
        }

    if not language_counts:
        return {
            "status": "no_data",
            "message": f"No public repositories or language data found for GitHub user '{username}'.",
            "verified_skills": []
        }

    # Map extracted GitHub languages to canonical vocabulary skills
    curr_skills = set(sess.get("current_skills", []))
    lp_dict = sess.get("learner_profile", {})
    extracted_skills = lp_dict.get("extracted_skills", [])
    skill_map = {e["skill"]: e for e in extracted_skills}

    for lang, repo_cnt in language_counts.items():
        d = matcher.match_direct(lang)
        canon_sk = d.skill if d else lang

        verified_skills.append(canon_sk)
        curr_skills.add(canon_sk)

        if canon_sk in skill_map:
            skill_map[canon_sk]["confidence"] = 9  # github_verified tier
            if "GITHUB_VERIFIED" not in skill_map[canon_sk]["found_in_sections"]:
                skill_map[canon_sk]["found_in_sections"].append("GITHUB_VERIFIED")
        else:
            new_ev = SkillEvidence(
                skill=canon_sk,
                category="Programming Languages",
                confidence=9,
                mention_count=repo_cnt,
                found_in_sections=["GITHUB_VERIFIED"]
            )
            extracted_skills.append(new_ev.model_dump())

    lp_dict["extracted_skills"] = extracted_skills

    update_session(req_data.session_id, {
        "current_skills": list(curr_skills),
        "learner_profile": lp_dict
    }, db=db)

    return {
        "status": "success",
        "github_username": username,
        "languages_detected": language_counts,
        "verified_skills": verified_skills,
        "total_current_skills": len(curr_skills)
    }
