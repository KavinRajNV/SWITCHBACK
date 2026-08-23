import math
import pickle
import pytest
import numpy as np

from app.db.mongo_client import get_db
from app.ml.features import build_feature_manifest, load_feature_manifest, vectorize, ARTIFACTS_DIR
from app.ml.explain import get_skill_contributions
from app.ml.path_sequencer import generate_path, get_graph

@pytest.fixture(scope="module")
def db():
    return get_db()

@pytest.fixture(scope="module")
def manifest(db):
    try:
        return load_feature_manifest()
    except FileNotFoundError:
        return build_feature_manifest(db)

@pytest.fixture(scope="module")
def graph():
    return get_graph()

def test_vectorize_shape_and_determinism(manifest):
    skills = {"Python", "SQL", "Machine Learning"}
    exp_min, exp_max = 2.0, 5.0
    locations = ["Bengaluru", "Remote"]
    company = "PWC"
    job_title = "Senior Data Scientist"

    vec1 = vectorize(skills, exp_min, exp_max, locations, company, job_title, manifest)
    vec2 = vectorize(skills, exp_min, exp_max, locations, company, job_title, manifest)

    assert isinstance(vec1, np.ndarray)
    assert vec1.shape == (manifest["num_total_features"],)
    assert manifest["manifest_version"] == 2
    assert manifest["num_total_features"] == 323
    assert np.array_equal(vec1, vec2), "Vectorization must be deterministic for identical inputs"

def test_get_skill_contributions(manifest):
    vec = vectorize({"Python", "SQL"}, 1.0, 3.0, ["Bengaluru"], "PWC", "Senior Data Scientist", manifest)
    contribs = get_skill_contributions(vec, manifest)

    assert isinstance(contribs, dict)
    assert len(contribs) == manifest["num_skills"]

    valid_skills = set(manifest["skills_ordered"])
    for skill_name, shap_val in contribs.items():
        assert skill_name in valid_skills, f"Skill '{skill_name}' not in manifest"
        assert isinstance(shap_val, float)
        assert math.isfinite(shap_val), f"SHAP value for '{skill_name}' must be finite"

def test_generate_path_behavior(db, graph):
    occ = db.occupations_enriched.find_one({"title": {"$regex": "Data Scientist", "$options": "i"}})
    assert occ is not None, "Target occupation 'Data Scientist' must exist in occupations_enriched"

    soc_code = occ["onet_soc_code"]
    combined_skills = occ["combined_required_skills"]

    # 1. When current_skills already covers required_skills -> return []
    full_skills = set(combined_skills)
    path_empty = generate_path(full_skills, soc_code, graph)
    assert path_empty == [], "Expected empty path when learner already possesses all required skills"

    # 2. When current_skills has a gap -> return ordered non-empty list
    partial_skills = {"Excel", "SQL"}
    path = generate_path(partial_skills, soc_code, graph)
    assert isinstance(path, list)
    assert len(path) > 0

    # 3. Path should never include any skill already in current_skills (including canonical synonyms)
    path_skill_names = {m["skill"] for m in path}
    assert "Microsoft Excel" not in path_skill_names, "Input 'Excel' should map to 'Microsoft Excel' and exclude it as a milestone"

    # 4. Step numbers should be sequential 1..N
    step_nums = [m["step_number"] for m in path]
    assert step_nums == list(range(1, len(path) + 1))

def test_graph_pickle_load_and_counts(graph):
    assert graph is not None
    num_skill_nodes = sum(1 for n, d in graph.nodes(data=True) if d.get("node_type") == "skill")
    num_occ_nodes = sum(1 for n, d in graph.nodes(data=True) if d.get("node_type") == "occupation")

    assert num_skill_nodes == 265
    assert num_occ_nodes == 1016
    assert graph.number_of_nodes() == 1281
    assert graph.number_of_edges() == 21137
