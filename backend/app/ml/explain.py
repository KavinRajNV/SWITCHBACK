import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import joblib
from typing import Dict, Any, List, Tuple, Union, Optional, Set
import numpy as np
import shap

from app.db.mongo_client import get_db
from app.ml.features import load_feature_manifest, ARTIFACTS_DIR
from app.ml.train_salary_model import prepare_training_data

MODEL_PATH = ARTIFACTS_DIR / "salary_model.joblib"
EXPLAINER_PATH = ARTIFACTS_DIR / "shap_explainer.joblib"

def build_shap_explainer() -> Tuple[shap.TreeExplainer, List[Tuple[str, float]]]:
    """
    Fits shap.TreeExplainer on background training samples and saves to artifacts/shap_explainer.joblib.
    Computes global feature importance across test set and returns (explainer, top_25_features).
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Trained salary model not found at {MODEL_PATH}. Run train_salary_model.py first.")

    model = joblib.load(MODEL_PATH)
    db = get_db()
    manifest = load_feature_manifest()

    X, y, _, _ = prepare_training_data(db, manifest, include_b1_b2=True)

    # Use 300 background samples for TreeExplainer
    np.random.seed(42)
    bg_indices = np.random.choice(len(X), min(300, len(X)), replace=False)
    X_background = X[bg_indices]

    print(f"[SHAP Explain] Fitting TreeExplainer on {len(X_background)} background samples...")
    explainer = shap.TreeExplainer(model, X_background)

    # Compute SHAP values on test sample (500 rows)
    test_indices = np.random.choice(len(X), min(500, len(X)), replace=False)
    X_test_sample = X[test_indices]
    shap_values = explainer.shap_values(X_test_sample)

    # Global feature importance: mean absolute SHAP value per feature
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feature_names = manifest["feature_names"]

    feature_importances = [(name, float(imp)) for name, imp in zip(feature_names, mean_abs_shap)]
    feature_importances.sort(key=lambda x: x[1], reverse=True)
    top_25_features = feature_importances[:25]

    print("======================================================================")
    print("TOP 25 GLOBAL SHAP FEATURE IMPORTANCES (v2 Model with Seniority & Company):")
    for rank, (name, imp) in enumerate(top_25_features, 1):
        print(f"  {rank:2d}. {name:<35} : {imp:.4f} SHAP impact")
    print("======================================================================")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(explainer, EXPLAINER_PATH)
    print(f"[SHAP Explain] Saved explainer to: {EXPLAINER_PATH}")

    return explainer, top_25_features

def get_skill_contributions(
    feature_vector: np.ndarray,
    user_skills: Optional[Union[Set[str], List[str], Dict[str, Any]]] = None,
    manifest: Optional[Dict[str, Any]] = None,
    shap_explainer: Optional[Any] = None
) -> Dict[str, float]:
    """
    Computes per-skill SHAP contributions for a single input feature vector.
    Returns dict mapping skill_name -> SHAP contribution (float).
    Execution time: < 0.05s.
    """
    # Defensive check: if manifest passed as 2nd positional argument
    if isinstance(user_skills, dict) and "feature_names" in user_skills:
        manifest = user_skills
        user_skills = None

    if manifest is None:
        manifest = load_feature_manifest()

    if shap_explainer is None:
        if not EXPLAINER_PATH.exists():
            explainer, _ = build_shap_explainer()
        else:
            explainer = joblib.load(EXPLAINER_PATH)
    else:
        explainer = shap_explainer

    if feature_vector.ndim == 1:
        X_in = feature_vector.reshape(1, -1)
    else:
        X_in = feature_vector

    shap_vals = explainer.shap_values(X_in)[0]
    feature_names = manifest["feature_names"]

    if user_skills is not None:
        target_skills = set(user_skills)
    else:
        target_skills = set(manifest["skills_ordered"])

    contributions = {}
    for name, val in zip(feature_names, shap_vals):
        if name in target_skills:
            contributions[name] = round(float(val), 4)

    return contributions

if __name__ == "__main__":
    build_shap_explainer()
