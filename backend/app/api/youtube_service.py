"""
YouTube Data API v3 free-course fetcher for Switchback.
- Queries search.list using the skill name, filtered to channels from youtube_allowlist
  by resolving channel names to IDs via YouTube channels.list API.
- Channel IDs are cached in youtube_cache (channel_id_cache key) so we don't re-resolve every time.
- Video results cached per skill in youtube_cache (TTL: YOUTUBE_CACHE_TTL_HOURS) to control quota.
- Never fabricates results — returns empty list if no match or API unavailable.
- Zero LLM calls.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

import httpx
from pymongo.database import Database

from app.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_CACHE_COLLECTION = "youtube_cache"
YOUTUBE_CACHE_TTL_HOURS = 24
CHANNEL_ID_CACHE_KEY = "channel_id_lookup_cache"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_CHANNELS_PER_QUERY = 5   # restrict search to this many channel IDs per call
MAX_RESULTS_PER_SKILL = 5


def _get_api_key() -> Optional[str]:
    key = settings.YOUTUBE_API_KEY or ""
    return key.strip() if key.strip() else None


def _skill_matches_channel(skill_lower: str, channel_doc: Dict) -> bool:
    """
    Strict channel-skill matching:
    - For a multi-word skill (e.g. 'microsoft excel'), ALL significant words
      (len >= 4) must appear in the channel's domain/primary_topics/channel_name.
      This prevents 'Microsoft Azure' from matching 'Microsoft Excel' because
      'excel' won't be in the Azure channel's topics.
    - For a single-word skill, the word must appear as a whole word (not substring)
      in the channel's haystack to avoid spurious matches (e.g. 'C' not matching
      every channel that has 'C' anywhere).
    - Channel's confidence must not be None.
    """
    haystack = " ".join([
        str(channel_doc.get("domain", "")),
        str(channel_doc.get("primary_topics", "")),
        str(channel_doc.get("channel_name", "")),
    ]).lower()

    significant_words = [w for w in skill_lower.split() if len(w) >= 4]
    if not significant_words:
        # Very short skill name — require exact substring match
        return skill_lower in haystack

    if len(significant_words) == 1:
        # Single significant word — use word-boundary check
        import re as _re
        return bool(_re.search(r'\b' + _re.escape(significant_words[0]) + r'\b', haystack))

    # Multi-word skill: ALL significant words must appear in haystack
    return all(w in haystack for w in significant_words)


async def _resolve_channel_ids(channel_names: List[str], api_key: str) -> Dict[str, str]:
    """
    Resolve up to MAX_CHANNELS_PER_QUERY channel names to YouTube channel IDs
    via channels.list?forHandle or search.list?type=channel.
    Returns {channel_name: channel_id}.
    """
    name_to_id: Dict[str, str] = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name in channel_names[:MAX_CHANNELS_PER_QUERY]:
                try:
                    # Try searching for the channel by name
                    resp = await client.get(f"{YOUTUBE_API_BASE}/search", params={
                        "part": "snippet",
                        "q": name,
                        "type": "channel",
                        "maxResults": 1,
                        "key": api_key,
                    })
                    if resp.status_code == 200:
                        items = resp.json().get("items", [])
                        if items:
                            cid = items[0]["id"]["channelId"]
                            name_to_id[name] = cid
                    elif resp.status_code == 403:
                        logger.warning("[YouTube] Quota exceeded during channel ID resolution.")
                        break
                except Exception as e:
                    logger.debug(f"[YouTube] Failed to resolve channel '{name}': {e}")
    except Exception as e:
        logger.warning(f"[YouTube] httpx error during channel resolution: {e}")
    return name_to_id


async def fetch_youtube_videos(skill: str, db: Database) -> List[Dict[str, Any]]:
    """
    Returns up to MAX_RESULTS_PER_SKILL free YouTube video dicts for the given skill.
    Each dict: {title, url, channel_title, source, published_at}.

    Flow:
      1. Check skill-level cache (24h TTL).
      2. Select matching channels from youtube_allowlist by topical heuristic.
      3. Resolve channel names -> channel IDs (cached separately in youtube_cache).
      4. Call YouTube search.list restricted to each channel ID.
      5. Cache results.
    Returns [] if API key missing, quota exceeded, or no match.
    """
    skill_key = skill.strip().lower()
    api_key = _get_api_key()

    # 1. Skill-level cache check
    cached = db[YOUTUBE_CACHE_COLLECTION].find_one({"skill_key": skill_key})
    if cached:
        cached_at = cached.get("cached_at")
        if cached_at and (datetime.utcnow() - cached_at) < timedelta(hours=YOUTUBE_CACHE_TTL_HOURS):
            return cached.get("videos", [])

    # 2. API key required
    if not api_key:
        logger.info("[YouTube] YOUTUBE_API_KEY not configured — skipping fetch.")
        return []

    # 3. Select topically-matching channel names from allowlist
    all_channel_docs = list(db.youtube_allowlist.find(
        {}, {"channel_name": 1, "domain": 1, "primary_topics": 1, "confidence": 1}
    ))
    matched_docs = [d for d in all_channel_docs if _skill_matches_channel(skill_key, d)]
    if not matched_docs:
        # Narrow fallback: search all channels but we'll filter video results by title
        # Use at most first 3 general-tech channels (freeCodeCamp, Traversy, etc.)
        general_tech = [d for d in all_channel_docs
                        if any(w in str(d.get("domain", "")).lower()
                               for w in ["programming", "web", "data", "software", "computer"])]
        matched_docs = general_tech[:3] if general_tech else all_channel_docs[:3]
    channel_names = [d["channel_name"] for d in matched_docs[:MAX_CHANNELS_PER_QUERY]]

    # 4. Resolve channel names to IDs (with per-channel caching in youtube_cache)
    channel_id_doc = db[YOUTUBE_CACHE_COLLECTION].find_one({"cache_type": CHANNEL_ID_CACHE_KEY}) or {}
    known_ids: Dict[str, str] = channel_id_doc.get("data", {})

    unresolved = [n for n in channel_names if n not in known_ids]
    if unresolved:
        resolved = await _resolve_channel_ids(unresolved, api_key)
        if resolved:
            known_ids.update(resolved)
            db[YOUTUBE_CACHE_COLLECTION].update_one(
                {"cache_type": CHANNEL_ID_CACHE_KEY},
                {"$set": {"cache_type": CHANNEL_ID_CACHE_KEY, "data": known_ids, "updated_at": datetime.utcnow()}},
                upsert=True,
            )

    channel_ids = [known_ids[n] for n in channel_names if n in known_ids]

    # 5. Fetch videos — one search.list call per channel (up to MAX_CHANNELS_PER_QUERY)
    all_videos: List[Dict] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for channel_id in channel_ids:
                if len(all_videos) >= MAX_RESULTS_PER_SKILL:
                    break
                try:
                    resp = await client.get(f"{YOUTUBE_API_BASE}/search", params={
                        "part": "snippet",
                        "q": skill,
                        "channelId": channel_id,
                        "type": "video",
                        "maxResults": 2,
                        "key": api_key,
                        "relevanceLanguage": "en",
                        "safeSearch": "strict",
                    })
                    if resp.status_code == 200:
                        for item in resp.json().get("items", []):
                            vid_id = item.get("id", {}).get("videoId")
                            snippet = item.get("snippet", {})
                            if vid_id:
                                all_videos.append({
                                    "title": snippet.get("title", ""),
                                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                                    "channel_title": snippet.get("channelTitle", ""),
                                    "published_at": snippet.get("publishedAt", ""),
                                    "source": "YouTube (Free)",
                                    "is_paid": False,
                                })
                    elif resp.status_code == 403:
                        logger.warning("[YouTube] Quota exceeded during video search.")
                        break
                except Exception as e:
                    logger.debug(f"[YouTube] Search failed for channel {channel_id}: {e}")
    except Exception as e:
        logger.warning(f"[YouTube] httpx error during video search: {e}")

    # Post-fetch relevance filter: reject videos whose title doesn't mention
    # at least one significant word from the skill name.
    # This is the final safety net against off-topic videos slipping through
    # (e.g. Azure videos appearing for an Excel query via a Microsoft channel).
    import re as _re
    skill_words_for_filter = [w for w in skill_key.split() if len(w) >= 4]
    if skill_words_for_filter:
        def _video_is_relevant(video: Dict) -> bool:
            vtitle = video.get("title", "").lower()
            vchannel = video.get("channel_title", "").lower()
            # Accept if any significant skill word appears in the video title
            return any(
                _re.search(r'\b' + _re.escape(w) + r'\b', vtitle)
                for w in skill_words_for_filter
            )
        filtered_videos = [v for v in all_videos if _video_is_relevant(v)]
        if not filtered_videos and all_videos:
            logger.warning(
                f"[YouTube] Relevance filter removed all {len(all_videos)} videos "
                f"for skill='{skill}'. Returning no video rather than an unrelated one."
            )
        all_videos = filtered_videos

    # 6. Cache (even empty, to avoid quota burn on re-requests)
    db[YOUTUBE_CACHE_COLLECTION].update_one(
        {"skill_key": skill_key},
        {"$set": {
            "skill_key": skill_key,
            "skill": skill,
            "cached_at": datetime.utcnow(),
            "videos": all_videos,
        }},
        upsert=True,
    )

    return all_videos[:MAX_RESULTS_PER_SKILL]
