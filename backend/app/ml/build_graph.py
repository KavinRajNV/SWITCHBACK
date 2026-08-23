import sys
import pickle
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter
import networkx as nx
from pymongo.database import Database

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.mongo_client import get_db
from app.ml.features import ARTIFACTS_DIR
from app.ml.build_skill_edges import build_skill_edges

GRAPH_PATH = ARTIFACTS_DIR / "skill_graph.pkl"

def build_skill_occupation_graph() -> Dict[str, Any]:
    """
    Constructs the directed skill/occupation networkx graph (networkx.DiGraph).
    Saves graph pickle to artifacts/skill_graph.pkl and metadata to Mongo collection 'graph_metadata'.
    """
    db = get_db()
    G = nx.DiGraph()

    print("[Build Graph] Adding canonical skill nodes...")
    vocab_docs = list(db.skill_vocabulary.find({}))
    for doc in vocab_docs:
        skill = doc.get("canonical_skill")
        cat = doc.get("category", "General")
        if skill:
            G.add_node(
                skill,
                node_type="skill",
                title=skill,
                category=cat
            )

    print(f"[Build Graph] Added {len(vocab_docs)} skill nodes.")

    print("[Build Graph] Adding enriched occupation nodes and 'requires' edges...")
    occ_docs = list(db.occupations_enriched.find({}))

    requires_edge_count = 0

    for doc in occ_docs:
        soc_code = doc.get("onet_soc_code")
        title = doc.get("title", "")
        desc = doc.get("description", "")
        salary = doc.get("market_median_salary_lpa")
        posting_cnt = doc.get("market_posting_count", 0)

        if not soc_code:
            continue

        G.add_node(
            soc_code,
            node_type="occupation",
            title=title,
            description=desc,
            market_median_salary_lpa=salary,
            market_posting_count=posting_cnt
        )

        tax_skills = {ts["skill"]: ts.get("importance", 3.0) for ts in doc.get("taxonomy_required_skills", [])}
        market_skills = {ms["skill"]: ms.get("frequency", 1) for ms in doc.get("market_verified_skills", [])}

        combined_skills = doc.get("combined_required_skills", [])

        for skill in combined_skills:
            if skill not in G:
                G.add_node(skill, node_type="skill", title=skill, category="General")

            # Calculate edge weight based on evidence strength
            tax_imp = tax_skills.get(skill, 0.0)
            mkt_freq = market_skills.get(skill, 0)

            if tax_imp >= 4.0 or mkt_freq >= 10:
                weight = 0.3
            elif tax_imp >= 3.0 or mkt_freq >= 3:
                weight = 0.5
            else:
                weight = 0.8

            G.add_edge(
                soc_code,
                skill,
                relation="requires",
                weight=float(weight)
            )
            requires_edge_count += 1

    print(f"[Build Graph] Added {len(occ_docs)} occupation nodes and {requires_edge_count} 'requires' edges.")

    print("[Build Graph] Merging skill-skill transition edges...")
    skill_edges = build_skill_edges()

    related_edge_count = 0
    for edge in skill_edges:
        u = edge["source"]
        v = edge["target"]
        w = edge["weight"]
        src_type = edge["source_type"]

        if u not in G:
            G.add_node(u, node_type="skill", title=u, category="General")
        if v not in G:
            G.add_node(v, node_type="skill", title=v, category="General")

        G.add_edge(
            u,
            v,
            relation="related_to",
            weight=float(w),
            source_type=src_type
        )
        related_edge_count += 1

    print(f"[Build Graph] Added {related_edge_count} 'related_to' skill edges.")

    # Calculate Graph Statistics
    num_skill_nodes = sum(1 for n, d in G.nodes(data=True) if d.get("node_type") == "skill")
    num_occ_nodes = sum(1 for n, d in G.nodes(data=True) if d.get("node_type") == "occupation")
    num_total_nodes = G.number_of_nodes()
    num_total_edges = G.number_of_edges()

    avg_degree = round(num_total_edges / num_total_nodes, 4) if num_total_nodes else 0.0
    num_wcc = nx.number_weakly_connected_components(G)

    # Top 10 highest degree skill nodes
    skill_degrees = [(n, G.degree(n)) for n, d in G.nodes(data=True) if d.get("node_type") == "skill"]
    skill_degrees.sort(key=lambda x: x[1], reverse=True)
    top_10_skills = skill_degrees[:10]

    print("======================================================================")
    print("SKILL / OCCUPATION GRAPH SUMMARY STATISTICS:")
    print(f"  - Skill Nodes: {num_skill_nodes}")
    print(f"  - Occupation Nodes: {num_occ_nodes}")
    print(f"  - Total Nodes: {num_total_nodes}")
    print(f"  - 'requires' Edges: {requires_edge_count}")
    print(f"  - 'related_to' Edges: {related_edge_count}")
    print(f"  - Total Edges: {num_total_edges}")
    print(f"  - Average Node Degree: {avg_degree}")
    print(f"  - Weakly Connected Components: {num_wcc}")
    print("  - Top 10 Highest Degree Skill Nodes:")
    for rank, (sk, deg) in enumerate(top_10_skills, 1):
        print(f"      {rank:2d}. {sk:<30} : degree {deg}")
    print("======================================================================")

    # Save Graph Pickle
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"[Build Graph] Saved pickled graph to: {GRAPH_PATH}")

    # Save summary metadata to Mongo 'graph_metadata'
    meta_doc = {
        "num_skill_nodes": num_skill_nodes,
        "num_occupation_nodes": num_occ_nodes,
        "num_total_nodes": num_total_nodes,
        "num_requires_edges": requires_edge_count,
        "num_related_to_edges": related_edge_count,
        "num_total_edges": num_total_edges,
        "avg_degree": avg_degree,
        "num_weakly_connected_components": num_wcc,
        "top_10_highest_degree_skills": [{"skill": sk, "degree": deg} for sk, deg in top_10_skills],
        "graph_path": str(GRAPH_PATH)
    }

    meta_coll = db["graph_metadata"]
    meta_coll.delete_many({})
    meta_coll.insert_one(meta_doc)

    return meta_doc

if __name__ == "__main__":
    build_skill_occupation_graph()
