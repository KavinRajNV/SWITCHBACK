import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import httpx
from fastapi import Request
from app.main import app, lifespan
from app.api.live import get_live_jobs

async def run_step0b_test():
    print("======================================================================")
    print("STEP 0B ADZUNA MOCK TIMEOUT / FAILURE SIMULATION")
    print("======================================================================")

    async with lifespan(app):
        mock_req = MagicMock(spec=Request)
        mock_req.app.state.db = app.state.db
        mock_req.app.state.occupations_dict = app.state.occupations_dict

        # Simulate timeout exception during outbound HTTP call to Adzuna
        with patch.object(httpx.AsyncClient, "get", side_effect=httpx.ConnectTimeout("Simulated Adzuna Timeout")):
            response_data = await get_live_jobs(request=mock_req, role="SimulatedUncachedRole123")
            
            print("HTTP Response Data:", response_data)
            print("Status Field:", response_data.get("status"))
            print("Jobs Array Count:", len(response_data.get("jobs", [])))
            print("Source Field:", response_data.get("source"))
            
            assert response_data["status"] == "unavailable"
            assert response_data["jobs"] == []
            assert response_data["source"] == "fallback"

        print("======================================================================")
        print("STEP 0B ADZUNA TIMEOUT SIMULATION CONFIRMED 100% SUCCESSFUL!")
        print("======================================================================")

if __name__ == "__main__":
    asyncio.run(run_step0b_test())
