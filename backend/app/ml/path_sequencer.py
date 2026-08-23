import sys
import pickle
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Union
import networkx as nx

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.ml.features import ARTIFACTS_DIR
from app.data_pipeline.skill_matcher import SkillMatcher

GRAPH_PATH = ARTIFACTS_DIR / "skill_graph.pkl"

_CACHED_GRAPH: Optional[nx.DiGraph] = None

def get_graph() -> nx.DiGraph:
    """
    Loads and caches the pickled skill graph from artifacts/skill_graph.pkl.
    """
    global _CACHED_GRAPH
    if _CACHED_GRAPH is None:
        if not GRAPH_PATH.exists():
            raise FileNotFoundError(f"Skill graph pickle not found at {GRAPH_PATH}. Run build_graph.py first.")
        with open(GRAPH_PATH, "rb") as f:
            _CACHED_GRAPH = pickle.load(f)
    return _CACHED_GRAPH

def generate_path(
    current_skills: Union[Set[str], List[str]],
    target_occupation_soc_code: str,
    graph: Optional[nx.DiGraph] = None,
    occupations_enriched: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generates a personalized multi-skill learning path using greedy nearest-fringe expansion (Dijkstra-driven).
    Returns list of ordered Milestone dicts:
    [
      {
        "skill": str,
        "step_number": int,
        "cost": float,
        "reachable_via": str | None,
        "is_essential": bool
      }
    ]
    """
    if graph is None:
        graph = get_graph()

    # Defensive input skill canonicalization (Patch E)
    db = get_db()
    matcher = SkillMatcher.from_mongo(db)

    canonical_current = set()
    for s in current_skills:
        if not s or not isinstance(s, str):
            continue
        d = matcher.match_direct(s)
        if d:
            canonical_current.add(d.skill)
        else:
            extracted = matcher.extract_skills(s)
            if extracted:
                canonical_current.add(extracted[0].skill)
            else:
                canonical_current.add(s)
                print(f"[Path Sequencer Debug] Unmatched input skill string kept as-is: '{s}'")

    # Resolve target occupation data
    if occupations_enriched is None:
        occ_doc = db.occupations_enriched.find_one({"onet_soc_code": target_occupation_soc_code})
        if not occ_doc:
            occ_doc = db.occupations_enriched.find_one({"title": {"$regex": target_occupation_soc_code, "$options": "i"}})
        if not occ_doc:
            raise ValueError(f"Target occupation '{target_occupation_soc_code}' not found in occupations_enriched.")
    else:
        occ_doc = occupations_enriched

    required_skills = set(occ_doc.get("combined_required_skills", []))
    essential_skills = set(ts["skill"] for ts in occ_doc.get("taxonomy_required_skills", []))

    # Gap = required_skills - canonical_current
    remaining_gap = set(required_skills) - canonical_current
    if not remaining_gap:
        return []

    acquired = set(canonical_current)
    milestones: List[Dict[str, Any]] = []
    step_num = 1

    while remaining_gap:
        best_candidate: Optional[str] = None
        best_cost: float = float("inf")
        best_parent: Optional[str] = None

        # 1. Evaluate fringe transitions from acquired skills to remaining gap skills
        for target_skill in remaining_gap:
            if target_skill not in graph:
                # If target skill not in graph, set default cold start cost
                if 2.0 < best_cost:
                    best_cost = 2.0
                    best_candidate = target_skill
                    best_parent = None
                continue

            for source_skill in acquired:
                if source_skill in graph and graph.has_edge(source_skill, target_skill):
                    weight = graph[source_skill][target_skill].get("weight", 0.5)
                    if weight < best_cost:
                        best_cost = weight
                        best_candidate = target_skill
                        best_parent = source_skill

            # Cold start fallback if no edge exists from acquired set
            if best_candidate is None:
                default_cost = 2.0
                if default_cost < best_cost:
                    best_cost = default_cost
                    best_candidate = target_skill
                    best_parent = None

        # If no valid candidate selected, pick arbitrary remaining gap skill
        if best_candidate is None:
            best_candidate = next(iter(remaining_gap))
            best_cost = 2.0
            best_parent = None

        acquired.add(best_candidate)
        remaining_gap.remove(best_candidate)

        milestones.append({
            "skill": best_candidate,
            "step_number": step_num,
            "cost": float(best_cost),
            "reachable_via": best_parent,
            "is_essential": best_candidate in essential_skills
        })
        step_num += 1

    return milestones
