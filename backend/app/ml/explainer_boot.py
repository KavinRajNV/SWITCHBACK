"""Build a fresh SHAP TreeExplainer at startup.

The committed ``shap_explainer.joblib`` embeds numba-compiled code objects that
are bound to the exact interpreter/numba build they were created with. Loading it
on any other machine fails with::

    TypeError: code() argument 13 must be str, not int

A ``TreeExplainer`` over an already-fitted ``GradientBoostingRegressor`` rebuilds
in well under a tenth of a second and uses the same ``tree_path_dependent``
attribution semantics we rely on for per-skill contributions, so the API always
constructs it live rather than trusting the pickle.
"""
from typing import Any

import shap


def build_startup_explainer(salary_model: Any) -> shap.TreeExplainer:
    """Return a TreeExplainer for the loaded salary model.

    No background dataset is passed: for tree models SHAP then uses the model's
    own tree structure (``feature_perturbation="tree_path_dependent"``), which
    needs no MongoDB access and is deterministic.
    """
    return shap.TreeExplainer(salary_model)
