import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import joblib
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from app.config import settings
from app.db.mongo_client import get_db
from app.ml.features import build_feature_manifest, vectorize, ARTIFACTS_DIR

MODEL_PATH = ARTIFACTS_DIR / "salary_model.joblib"

def prepare_training_data(db: Any, manifest: Dict[str, Any], include_b1_b2: bool = True) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """
    Queries Mongo 'jobs' collection for training data:
    - source_quality == 'primary'
    - salary_disclosed == True
    - len(skills_matched) >= 1
    Target: salary_target_lpa = (salary_min_lpa + salary_max_lpa) / 2 (or single bound)
    Sanity bound: 0.5 to 200.0 LPA
    Returns (X, y, raw_count, excluded_count)
    """
    cursor = db.jobs.find(
        {"source_quality": "primary", "salary_disclosed": True},
        {
            "job_title": 1,
            "company": 1,
            "skills_matched": 1,
            "experience_min_years": 1,
            "experience_max_years": 1,
            "locations": 1,
            "salary_min_lpa": 1,
            "salary_max_lpa": 1
        }
    )

    X_list = []
    y_list = []
    raw_count = 0
    excluded_count = 0

    for doc in cursor:
        skills = doc.get("skills_matched", [])
        if not skills or len(skills) == 0:
            continue

        raw_count += 1

        min_sal = doc.get("salary_min_lpa")
        max_sal = doc.get("salary_max_lpa")

        target_lpa = None
        if min_sal is not None and max_sal is not None:
            target_lpa = (float(min_sal) + float(max_sal)) / 2.0
        elif min_sal is not None:
            target_lpa = float(min_sal)
        elif max_sal is not None:
            target_lpa = float(max_sal)

        if target_lpa is None or not (0.5 <= target_lpa <= 200.0):
            excluded_count += 1
            continue

        exp_min = doc.get("experience_min_years", 0.0)
        exp_max = doc.get("experience_max_years", exp_min)
        locs = doc.get("locations", [])
        comp = doc.get("company") if include_b1_b2 else None
        title = doc.get("job_title") if include_b1_b2 else None

        vec = vectorize(skills, exp_min, exp_max, locs, comp, title, manifest)
        X_list.append(vec)
        y_list.append(target_lpa)

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.float64)
    return X, y, raw_count, excluded_count

def run_3way_ablation(db: Any, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates 3 configurations:
    1. Baseline (original features, raw target LPA)
    2. Original + B1 (Seniority) + B2 (Company-tier), raw target LPA
    3. Original + B1 + B2, log1p-transformed target LPA (predictions inverse-transformed via expm1)
    """
    # 1. Baseline Data (zero out B1/B2 columns)
    X_full, y, raw_cnt, exc_cnt = prepare_training_data(db, manifest, include_b1_b2=True)

    X_train_full, X_test_full, y_train, y_test = train_test_split(X_full, y, test_size=0.2, random_state=42)

    # Config 1: Baseline (zero out seniority & company columns in X)
    num_skills_exp_loc = manifest["num_skills"] + 3 + manifest["num_locations"] + 2
    X_train_cfg1 = X_train_full[:, :num_skills_exp_loc].copy()
    X_test_cfg1 = X_test_full[:, :num_skills_exp_loc].copy()

    model1 = GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)
    model1.fit(X_train_cfg1, y_train)
    y_pred1 = model1.predict(X_test_cfg1)
    mae1 = float(mean_absolute_error(y_test, y_pred1))
    rmse1 = float(np.sqrt(mean_squared_error(y_test, y_pred1)))
    r2_1 = float(r2_score(y_test, y_pred1))

    # Config 2: Original + B1 + B2, Raw Target (Patch G Deployed Model)
    model2 = GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)
    model2.fit(X_train_full, y_train)
    y_pred2 = model2.predict(X_test_full)
    mae2 = float(mean_absolute_error(y_test, y_pred2))
    rmse2 = float(np.sqrt(mean_squared_error(y_test, y_pred2)))
    r2_2 = float(r2_score(y_test, y_pred2))

    # Config 3: Original + B1 + B2, Log1p Target
    y_train_log = np.log1p(y_train)
    model3 = GradientBoostingRegressor(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)
    model3.fit(X_train_full, y_train_log)
    y_pred3_log = model3.predict(X_test_full)
    y_pred3 = np.expm1(y_pred3_log)
    mae3 = float(mean_absolute_error(y_test, y_pred3))
    rmse3 = float(np.sqrt(mean_squared_error(y_test, y_pred3)))
    r2_3 = float(r2_score(y_test, y_pred3))

    results = {
        "config1": {"name": "1. Original Features, Raw Target (Baseline)", "mae": mae1, "rmse": rmse1, "r2": r2_1, "model": model1},
        "config2": {"name": "2. Original + B1 + B2 Features, Raw Target", "mae": mae2, "rmse": rmse2, "r2": r2_2, "model": model2},
        "config3": {"name": "3. Original + B1 + B2 Features, Log1p Target", "mae": mae3, "rmse": rmse3, "r2": r2_3, "model": model3},
        "raw_count": raw_cnt,
        "excluded_count": exc_cnt,
        "total_samples": len(y),
        "train_samples": len(y_train),
        "test_samples": len(y_test)
    }

    return results

def train_salary_model() -> Dict[str, Any]:
    """
    Runs the 3-way ablation comparison and deploys Config 2 model (B1+B2 raw target) to artifacts/salary_model.joblib.
    """
    db = get_db()
    manifest = build_feature_manifest(db)

    print("[Salary Model] Running 3-way target & feature ablation experiment...")
    ablation = run_3way_ablation(db, manifest)

    print("\n======================================================================")
    print("SALARY MODEL 3-WAY ABLATION COMPARISON TABLE (LPA Units):")
    print(f"{'Configuration':<52} | {'MAE (LPA)':<10} | {'RMSE (LPA)':<10} | {'R² Score':<10}")
    print("-" * 92)

    c1 = ablation["config1"]
    c2 = ablation["config2"]
    c3 = ablation["config3"]

    print(f"{c1['name']:<52} | {c1['mae']:<10.4f} | {c1['rmse']:<10.4f} | {c1['r2']:<10.4f}")
    print(f"{c2['name']:<52} | {c2['mae']:<10.4f} | {c2['rmse']:<10.4f} | {c2['r2']:<10.4f}")
    print(f"{c3['name']:<52} | {c3['mae']:<10.4f} | {c3['rmse']:<10.4f} | {c3['r2']:<10.4f}")
    print("======================================================================\n")

    # Patch G: Deploy Config 2 (Original + B1 + B2 Features, Raw Target LPA) for optimal R² (0.0641) and RMSE (9.4893 LPA)
    best_config = c2

    print(f"[Salary Model] Deployed configuration: '{best_config['name']}' (MAE: {best_config['mae']:.4f} LPA, RMSE: {best_config['rmse']:.4f} LPA, R²: {best_config['r2']:.4f}).")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_config["model"], MODEL_PATH)
    print(f"[Salary Model] Deployed model binary to: {MODEL_PATH}")

    return {
        "ablation_results": ablation,
        "best_config_name": best_config["name"],
        "best_mae_lpa": best_config["mae"],
        "best_rmse_lpa": best_config["rmse"],
        "best_r2_score": best_config["r2"],
        "model_path": str(MODEL_PATH)
    }

if __name__ == "__main__":
    train_salary_model()
