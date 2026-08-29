import math
import pickle
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import joblib

from app.config import settings
from app.db.mongo_client import get_db
from app.data_pipeline.skill_matcher import SkillMatcher
from app.ml.features import load_feature_manifest, ARTIFACTS_DIR
from app.ml.explainer_boot import build_startup_explainer
from app.api import profile, path, qa, progress, dashboard, live, timeline, assistant

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager: Loads all model artifacts and database caches ONCE at startup into app.state.
    Never reloaded per-request.
    """
    print("======================================================================")
    print("STARTUP: Loading Switchback ML models, skill graph, & Mongo caches...")
    print("======================================================================")

    # 1. MongoDB handle
    db = get_db()
    app.state.db = db

    # 2. SkillMatcher
    matcher = SkillMatcher.from_mongo(db)
    app.state.matcher = matcher

    # 3. Feature manifest
    manifest = load_feature_manifest()
    app.state.manifest = manifest

    # 4. Salary Model (GradientBoostingRegressor)
    model_path = ARTIFACTS_DIR / "salary_model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Salary model artifact not found at: {model_path}")
    salary_model = joblib.load(model_path)
    app.state.salary_model = salary_model

    # 5. SHAP Explainer — always rebuilt from the salary model at startup.
    # The committed shap_explainer.joblib embeds interpreter-bound numba code
    # objects and fails to unpickle on other machines; a fresh TreeExplainer is
    # equivalent and builds in <0.1s with no database access.
    app.state.shap_explainer = build_startup_explainer(salary_model)
    print("  SHAP TreeExplainer built fresh from salary model (no pickle).")

    # 6. Pickled Skill Graph
    graph_path = ARTIFACTS_DIR / "skill_graph.pkl"
    if not graph_path.exists():
        raise FileNotFoundError(f"Skill graph artifact not found at: {graph_path}")
    with open(graph_path, "rb") as f:
        graph = pickle.load(f)
    app.state.graph = graph

    # 7. Occupations Dict cached in memory (1,016 documents)
    occ_docs = list(db.occupations_enriched.find({}, {"_id": 0}))
    occupations_dict = {d["onet_soc_code"]: d for d in occ_docs if d.get("onet_soc_code")}
    app.state.occupations_dict = occupations_dict

    # 7b. Market roles dict (Naukri-native, catalog_source='market')
    # Use synthetic IDs: 'market::<title_slug>'
    import re as _re
    def _market_id(title: str) -> str:
        return "market::" + _re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')

    market_docs = list(db.market_roles.find({}, {"_id": 0}))
    market_roles_dict = {}
    for d in market_docs:
        mid = _market_id(d["title"])
        d["market_role_id"] = mid
        market_roles_dict[mid] = d
    app.state.market_roles_dict = market_roles_dict
    print(f"  Loaded {len(market_roles_dict)} market-native roles from market_roles collection.")

    print(f"SUCCESS: Loaded {len(occupations_dict)} occupations, {graph.number_of_nodes()} graph nodes, {graph.number_of_edges()} edges, & 323D salary model.")

    # 8. Pre-compute IDF weights over UNIFIED catalog (O*NET + market roles)
    # IDF(skill) = log(N / df) across all role documents in the combined catalog
    all_role_docs = list(occupations_dict.values()) + list(market_roles_dict.values())
    N = len(all_role_docs)
    skill_df: dict = {}
    for occ in all_role_docs:
        for sk in occ.get("combined_required_skills", []):
            if isinstance(sk, str):
                key = sk.lower()
                skill_df[key] = skill_df.get(key, 0) + 1
    skill_idf: dict = {}
    for sk, df in skill_df.items():
        skill_idf[sk] = math.log(N / df)  # higher = rarer = more discriminative
    app.state.skill_idf_weights = skill_idf
    print(f"  IDF weights computed for {len(skill_idf)} unique skills across unified catalog ({N} roles).")

    yield
    print("SHUTDOWN: Cleaning up app resources.")

app = FastAPI(
    title="Switchback API Server",
    description="Personalized learning-path recommender backend API. "
                "Recommendations are deterministic and data-grounded; any LLM call is "
                "optional and never on the fact path.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS: explicit origin allow-list, no credentials (the API uses no cookies).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"[Global Exception Handler] Unhandled error on {request.method} {request.url}:")
    traceback.print_exc()
    body = {"error": "InternalServerError", "path": str(request.url.path)}
    if settings.APP_ENV == "development":
        body["detail"] = str(exc)
    return JSONResponse(status_code=500, content=body)

# Health endpoint
@app.get("/health", tags=["Health"])
async def health_check(request: Request):
    """
    Health check endpoint reporting backend artifact loading status.
    """
    has_db = hasattr(request.app.state, "db") and request.app.state.db is not None
    has_matcher = hasattr(request.app.state, "matcher") and request.app.state.matcher is not None
    has_model = hasattr(request.app.state, "salary_model") and request.app.state.salary_model is not None
    has_graph = hasattr(request.app.state, "graph") and request.app.state.graph is not None

    return {
        "status": "healthy" if (has_db and has_matcher and has_model and has_graph) else "degraded",
        "artifacts_loaded": {
            "mongodb": has_db,
            "skill_matcher": has_matcher,
            "salary_model": has_model,
            "shap_explainer": hasattr(request.app.state, "shap_explainer"),
            "skill_graph": has_graph,
            "occupations_count": len(getattr(request.app.state, "occupations_dict", {}))
        }
    }

# Mount API routers
app.include_router(profile.router)
app.include_router(path.router)
app.include_router(qa.router)
app.include_router(progress.router)
app.include_router(dashboard.router)
app.include_router(live.router)
app.include_router(timeline.router)
app.include_router(assistant.router)
