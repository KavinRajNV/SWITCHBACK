import re
from typing import List, Dict, Tuple, Set, Any
from app.data_pipeline.skill_matcher import SkillMatcher

def segment_concatenated(raw: str, matcher: SkillMatcher) -> Dict[str, List[str]]:
    """
    Segment concatenated or raw skill strings into matched canonical skill names
    and a list of unmatched leftover tokens.
    
    Returns:
        {
            "matched_skills": list[str], # Canonical skill names in order
            "leftover": list[str]        # Unmatched substrings/tokens
        }
    """
    if not raw or not str(raw).strip():
        return {"matched_skills": [], "leftover": []}

    text = str(raw).strip()
    
    # 1. Pre-process camelCase boundaries: insert space between lowercase/digit and Uppercase letter
    text_spaced = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)
    
    # 2. Check if text has explicit delimiters
    if re.search(r'[,;|\/\n\t]', text_spaced):
        tokens = [t.strip() for t in re.split(r'[,;|\/\n\t]+', text_spaced) if t.strip()]
        matched_skills: List[str] = []
        leftover: List[str] = []
        seen_matched: Set[str] = set()

        for tok in tokens:
            direct = matcher.match_direct(tok)
            if direct:
                if direct.skill not in seen_matched:
                    seen_matched.add(direct.skill)
                    matched_skills.append(direct.skill)
            else:
                extracted = matcher.extract_skills(tok)
                if extracted:
                    for m in extracted:
                        if m.skill not in seen_matched:
                            seen_matched.add(m.skill)
                            matched_skills.append(m.skill)
                else:
                    leftover.append(tok)
                    
        return {"matched_skills": matched_skills, "leftover": leftover}

    # 3. For concatenated non-delimited strings: perform fast candidate-filtered greedy longest-match scan
    text_lower = text_spaced.lower()
    n = len(text_lower)
    
    # Pre-filter candidate aliases present in text_lower
    candidate_aliases = [alias for alias in matcher.sorted_aliases if alias in text_lower]
    
    pos = 0
    matched_spans: List[Tuple[int, int, str]] = []
    
    while pos < n:
        match_found = False
        for alias in candidate_aliases:
            alias_len = len(alias)
            if pos + alias_len <= n and text_lower[pos : pos + alias_len] == alias:
                # Check word boundaries for short aliases
                is_start_ok = (pos == 0) or not text_lower[pos - 1].isalnum()
                is_end_ok = (pos + alias_len == n) or not text_lower[pos + alias_len].isalnum()
                if alias_len <= 3 and not (is_start_ok and is_end_ok):
                    continue
                    
                canonical = matcher.alias_to_canonical[alias]
                matched_spans.append((pos, pos + alias_len, canonical))
                pos += alias_len
                match_found = True
                break
                
        if not match_found:
            pos += 1

    # Extract matched skills in order
    matched_skills: List[str] = []
    seen: Set[str] = set()
    for _, _, canonical in matched_spans:
        if canonical not in seen:
            seen.add(canonical)
            matched_skills.append(canonical)
            
    # Find leftover spans
    leftover: List[str] = []
    last_end = 0
    for start, end, _ in sorted(matched_spans, key=lambda x: x[0]):
        if start > last_end:
            span_text = text_spaced[last_end:start].strip()
            if span_text:
                leftover.append(span_text)
        last_end = max(last_end, end)
        
    if last_end < n:
        span_text = text_spaced[last_end:n].strip()
        if span_text:
            leftover.append(span_text)

    # Fallback heuristics for leftover spans
    final_leftover: List[str] = []
    for span in leftover:
        sub_tokens = span.split()
        for tok in sub_tokens:
            direct = matcher.match_direct(tok)
            if direct:
                if direct.skill not in seen:
                    seen.add(direct.skill)
                    matched_skills.append(direct.skill)
            else:
                final_leftover.append(tok)

    return {
        "matched_skills": matched_skills,
        "leftover": final_leftover
    }
