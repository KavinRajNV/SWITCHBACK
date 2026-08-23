import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from pymongo.database import Database
import rapidfuzz
from rapidfuzz import fuzz, process

from app.config import settings

@dataclass
class MatchedSkill:
    skill: str          # Canonical skill name
    category: str       # Category name
    matched_text: str   # Text or alias that was matched
    score: float        # Rapidfuzz score (0.0 to 100.0)
    start: int          # Character start index
    end: int            # Character end index

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "category": self.category,
            "matched_text": self.matched_text,
            "score": float(self.score),
            "start": self.start,
            "end": self.end,
        }

class SkillMatcher:
    def __init__(self, vocabulary_records: List[dict]):
        """
        Initialize with a list of dicts, each containing:
        - canonical_skill (str)
        - category (str)
        - common_aliases (str or list of str)
        """
        self.canonical_to_category: Dict[str, str] = {}
        self.alias_to_canonical: Dict[str, str] = {}
        self.canonical_skills: Set[str] = set()
        
        # Build lookup tables
        for rec in vocabulary_records:
            canonical = str(rec.get("canonical_skill", "")).strip()
            category = str(rec.get("category", "")).strip()
            if not canonical:
                continue
                
            self.canonical_skills.add(canonical)
            self.canonical_to_category[canonical] = category
            
            # Canonical itself is an alias
            self.alias_to_canonical[canonical.lower()] = canonical
            
            aliases_raw = rec.get("common_aliases", "")
            if isinstance(aliases_raw, str):
                aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()]
            elif isinstance(aliases_raw, list):
                aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
            else:
                aliases = []
                
            for alias in aliases:
                self.alias_to_canonical[alias.lower()] = canonical

        # Precompute choices list for rapidfuzz
        self.choices: List[str] = list(self.alias_to_canonical.keys())
        
        # Sort choices by length descending for greedy scanning
        self.sorted_aliases: List[str] = sorted(self.choices, key=len, reverse=True)
        
        # Short aliases (len <= 3) that require strict word boundary / exact precision
        self.short_aliases: Set[str] = {
            alias for alias in self.choices if len(alias) <= 3
        }

    @classmethod
    def from_csv(cls, path: Optional[Path | str] = None) -> "SkillMatcher":
        csv_path = Path(path) if path else (settings.DATA_RAW_DIR / "curated_data" / "skill_vocabulary_seed_list.csv")
        if not csv_path.exists():
            raise FileNotFoundError(f"Skill vocabulary file not found at: {csv_path}")
            
        records = []
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        return cls(records)

    @classmethod
    def from_mongo(cls, db: Database) -> "SkillMatcher":
        coll = db["skill_vocabulary"]
        records = list(coll.find({}, {"_id": 0}))
        if not records:
            # Fallback to CSV if Mongo collection is empty
            return cls.from_csv()
        return cls(records)

    def match_direct(self, candidate: str, min_score: int = 90) -> Optional[MatchedSkill]:
        """
        Direct fuzzy match for a short, single candidate string.
        """
        if not candidate or not candidate.strip():
            return None
            
        cand_str = candidate.strip()
        cand_lower = cand_str.lower()
        
        # 1. Exact lookup
        if cand_lower in self.alias_to_canonical:
            canonical = self.alias_to_canonical[cand_lower]
            category = self.canonical_to_category.get(canonical, "Unknown")
            return MatchedSkill(
                skill=canonical,
                category=category,
                matched_text=cand_str,
                score=100.0,
                start=0,
                end=len(cand_str)
            )
            
        # 2. Rapidfuzz lookup
        match = process.extractOne(
            cand_lower,
            self.choices,
            scorer=fuzz.ratio,
            score_cutoff=min_score
        )
        if match:
            best_alias, score, _ = match
            canonical = self.alias_to_canonical[best_alias]
            category = self.canonical_to_category.get(canonical, "Unknown")
            return MatchedSkill(
                skill=canonical,
                category=category,
                matched_text=cand_str,
                score=float(score),
                start=0,
                end=len(cand_str)
            )
            
        return None

    def extract_skills(self, text: str, min_score: int = 85) -> List[MatchedSkill]:
        """
        Extract all vocabulary skills from a free-text string using fast substring matching
        with word boundary validation and language context checking for short ambiguous aliases.
        """
        if not text or not text.strip():
            return []
            
        text_lower = text.lower()
        n_text = len(text_lower)
        raw_matches: List[MatchedSkill] = []
        
        # Direct substring matching for all vocabulary aliases with word boundary checks
        for alias in self.sorted_aliases:
            if alias in text_lower:
                canonical = self.alias_to_canonical[alias]
                cat = self.canonical_to_category.get(canonical, "Unknown")
                alias_len = len(alias)
                
                pos = 0
                while True:
                    idx = text_lower.find(alias, pos)
                    if idx == -1:
                        break
                    
                    end_idx = idx + alias_len
                    # Check word boundary constraints
                    is_start_ok = (idx == 0) or not text_lower[idx - 1].isalnum()
                    is_end_ok = (end_idx == n_text) or not text_lower[end_idx].isalnum()
                    
                    if is_start_ok and is_end_ok:
                        # Special context check for single-letter alias 'r' to eliminate URL / path false positives
                        if alias == "r":
                            if (idx > 0 and text_lower[idx - 1] == '/') or (end_idx < n_text and text_lower[end_idx] == '/'):
                                pos = idx + 1
                                continue
                            surrounding = text_lower[max(0, idx - 20):min(n_text, end_idx + 20)]
                            has_lang_ctx = bool(re.search(r'\b(programming|language|studio|project|stats|analytics|python|sas|sql|coding|data science|using r|proficient in r|r,|r/)\b', surrounding))
                            if not has_lang_ctx:
                                pos = idx + 1
                                continue

                        raw_matches.append(MatchedSkill(
                            skill=canonical,
                            category=cat,
                            matched_text=text[idx:end_idx],
                            score=100.0,
                            start=idx,
                            end=end_idx
                        ))
                    pos = idx + 1

        # Deduplicate overlapping matches:
        # Sort by: score (desc), span length (desc), start (asc)
        raw_matches.sort(key=lambda m: (-m.score, -(m.end - m.start), m.start))
        
        selected: List[MatchedSkill] = []
        occupied_spans: List[Tuple[int, int]] = []
        
        for m in raw_matches:
            overlap = False
            for s_start, s_end in occupied_spans:
                if max(m.start, s_start) < min(m.end, s_end):
                    overlap = True
                    break
            if not overlap:
                selected.append(m)
                occupied_spans.append((m.start, m.end))
                
        return selected
