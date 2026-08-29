"""NVIDIA NIM-backed extraction for natural-language career goals.

The key is read only on the server.  The parser intentionally returns a small,
validated JSON contract so model output cannot control database queries or UI
navigation.
"""
import json
import re
from typing import Any, Dict, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from app.config import settings


SYSTEM_PROMPT = """You extract a learner's career goal. Return JSON only, with exactly these keys:
target_role (string or null), timeframe_days (integer or null), hours_per_week (integer or null),
background_hint (string or null), and skills (array of objects with skill and confidence 1-10).
Only include skills explicitly claimed by the learner as already having; never infer skills from
the desired role. Keep skill names short and canonical (for example Python, SQL, Docker).
Convert months to 30 days, years to 365 days, and weeks to 7 days. Do not include markdown."""


def _json_from_content(content: str) -> Dict[str, Any]:
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S | re.I).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.S | re.I)
    if fenced:
        content = fenced.group(1).strip()
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("NVIDIA response did not contain a JSON object")
    value = json.loads(content[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("NVIDIA response was not a JSON object")
    return value


def extract_with_nvidia(goal_text: str) -> Optional[Dict[str, Any]]:
    """Call NVIDIA's OpenAI-compatible hosted endpoint when configured.

    Returns None when no key is configured or when the provider is unavailable;
    callers can then use the deterministic parser without breaking the flow.
    """
    if not settings.NVIDIA_API_KEY:
        return None

    payload = {
        "model": settings.NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": goal_text.strip()},
        ],
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 700,
        "stream": False,
    }
    req = urlrequest.Request(
        f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=settings.NVIDIA_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return _json_from_content(content)
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        print(f"[NVIDIA goal extraction] provider unavailable or invalid response: {exc}")
        return None
