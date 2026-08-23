import math
import numpy as np
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.api.session_store import get_session
from app.models.schemas import GoalProfile

router = APIRouter(prefix="/api/timeline", tags=["Timeline Simulation"])

HOURS_PER_COST_UNIT = 40.0  # Constant: 1.0 graph transition cost = 40 expected study hours
NUM_TRIALS = 2000
SIGMA = 0.35  # Lognormal spread parameter

class TimelineSimulateRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")

@router.post("/simulate")
async def simulate_timeline(req_data: TimelineSimulateRequest, request: Request):
    """
    Runs a 2,000-trial Monte Carlo stochastic simulation over the milestone path,
    sampling study hours per milestone from a lognormal distribution and computing P10, P50, and P90 completion weeks.
    """
    db = request.app.state.db

    sess = get_session(req_data.session_id, db=db)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{req_data.session_id}' not found.")

    gp_dict = sess.get("goal_profile", {})
    gp = GoalProfile(**gp_dict)
    hrs_per_wk = gp.hours_per_week or 15

    stored_path = sess.get("stored_path", [])
    if not stored_path:
        return {
            "session_id": req_data.session_id,
            "is_fully_qualified": True,
            "message": "Learner already possesses all required skills for target role. Estimated timeline: 0 weeks.",
            "optimistic_weeks": 0.0,
            "realistic_weeks": 0.0,
            "conservative_weeks": 0.0
        }

    # Expected hours per milestone
    expected_hours_list = [max(float(ms.get("cost", 0.5)) * HOURS_PER_COST_UNIT, 8.0) for ms in stored_path]
    mean_total_hours = sum(expected_hours_list)

    # Lognormal simulation parameters per milestone
    # mean of lognormal = exp(mu + sigma^2/2) -> mu = ln(expected_hours) - 0.5*sigma^2
    mu_list = [math.log(h) - 0.5 * (SIGMA ** 2) for h in expected_hours_list]

    # Run 2,000 simulation trials
    rng = np.random.default_rng(seed=42)  # Seeded for reproducible simulation results
    trial_total_hours = np.zeros(NUM_TRIALS)

    for mu in mu_list:
        milestone_samples = rng.lognormal(mean=mu, sigma=SIGMA, size=NUM_TRIALS)
        trial_total_hours += milestone_samples

    trial_weeks = trial_total_hours / float(hrs_per_wk)

    p10_weeks = float(np.percentile(trial_weeks, 10))
    p50_weeks = float(np.percentile(trial_weeks, 50))
    p90_weeks = float(np.percentile(trial_weeks, 90))

    return {
        "session_id": req_data.session_id,
        "num_trials": NUM_TRIALS,
        "hours_per_week": hrs_per_wk,
        "path_length": len(stored_path),
        "mean_expected_total_hours": round(mean_total_hours, 1),
        "optimistic_weeks_p10": round(p10_weeks, 1),
        "realistic_weeks_p50": round(p50_weeks, 1),
        "conservative_weeks_p90": round(p90_weeks, 1),
        "milestone_breakdown": [
            {
                "step": ms["step_number"],
                "skill": ms["skill"],
                "cost": ms["cost"],
                "expected_hours": round(expected_hours_list[i], 1)
            }
            for i, ms in enumerate(stored_path)
        ]
    }
