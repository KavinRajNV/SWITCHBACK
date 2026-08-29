import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app, lifespan

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def client():
    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

@pytest.mark.anyio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["artifacts_loaded"]["mongodb"] is True
    assert data["artifacts_loaded"]["salary_model"] is True
    assert data["artifacts_loaded"]["skill_graph"] is True

@pytest.mark.anyio
async def test_full_happy_path_flow(client):
    # 1. Post manual skills
    res_prof = await client.post("/api/profile/manual-skills", json={
        "skills": ["Microsoft Excel", "SQL", "Business Analysis"]
    })
    assert res_prof.status_code == 200
    data_prof = res_prof.json()
    session_id = data_prof["session_id"]
    assert session_id is not None

    # 2. Generate learning path for Data Scientist (15-2051.00)
    res_path = await client.post("/api/path/generate", json={
        "session_id": session_id,
        "target_occupation_soc_code": "15-2051.00"
    })
    assert res_path.status_code == 200
    data_path = res_path.json()
    assert data_path["is_fully_qualified"] is False
    assert len(data_path["milestones"]) > 0
    assert len(data_path["elevation_profile"]) > 0
    first_ms = data_path["milestones"][0]["skill"]

    # 3. Complete a milestone
    res_prog = await client.post("/api/progress/complete-milestone", json={
        "session_id": session_id,
        "skill": first_ms,
        "evidence_type": "project_log",
        "project_description": f"Built a project using {first_ms}"
    })
    assert res_prog.status_code == 200
    data_prog = res_prog.json()
    assert data_prog["completed_skill"] == first_ms
    assert data_prog["confidence_assigned"] == 7
    assert data_prog["new_path_length"] < data_path["path_length"]

    # 4. Fetch dashboard
    res_dash = await client.get(f"/api/dashboard?session_id={session_id}")
    assert res_dash.status_code == 200
    data_dash = res_dash.json()
    assert data_dash["progress"]["completed_milestones_count"] == 1
    assert len(data_dash["elevation_profile"]) > 0

    # 5. Run Monte Carlo timeline simulation
    res_sim = await client.post("/api/timeline/simulate", json={"session_id": session_id})
    assert res_sim.status_code == 200
    data_sim = res_sim.json()
    assert data_sim["optimistic_weeks_p10"] <= data_sim["realistic_weeks_p50"] <= data_sim["conservative_weeks_p90"]

@pytest.mark.anyio
async def test_invalid_session_404(client):
    fake_id = "non-existent-uuid-12345"
    res1 = await client.post("/api/path/generate", json={"session_id": fake_id})
    assert res1.status_code == 404

    res2 = await client.post("/api/qa/ask", json={"session_id": fake_id, "question_id": "why_this_role"})
    assert res2.status_code == 404

    res3 = await client.post("/api/progress/complete-milestone", json={"session_id": fake_id, "skill": "Python", "evidence_type": "self_report"})
    assert res3.status_code == 404

    res4 = await client.get(f"/api/dashboard?session_id={fake_id}")
    assert res4.status_code == 404

@pytest.mark.anyio
async def test_qa_unknown_question_400(client):
    res_prof = await client.post("/api/profile/manual-skills", json={"skills": ["Python"]})
    session_id = res_prof.json()["session_id"]

    res_qa = await client.post("/api/qa/ask", json={"session_id": session_id, "question_id": "invalid_question_name"})
    assert res_qa.status_code == 400
    assert "Unknown question_id" in res_qa.json()["detail"]

@pytest.mark.anyio
async def test_qa_all_eight_questions(client):
    res_prof = await client.post("/api/profile/manual-skills", json={"skills": ["Python", "SQL"]})
    session_id = res_prof.json()["session_id"]

    # Generate path first
    await client.post("/api/path/generate", json={"session_id": session_id, "target_occupation_soc_code": "15-2051.00"})

    questions = [
        "why_this_skill",
        "how_long_will_this_take",
        "what_if_i_already_know_x",
        "show_free_alternatives",
        "why_this_role",
        "am_i_qualified_already",
        "what_skills_do_i_already_have",
        "explain_confidence_score"
    ]

    # what_if_i_already_know_x requires an explicit skill to test (no silent default).
    extra = {"what_if_i_already_know_x": {"extra_skill": "AWS"}}
    for q_id in questions:
        payload = {"session_id": session_id, "question_id": q_id}
        payload.update(extra.get(q_id, {}))
        res = await client.post("/api/qa/ask", json=payload)
        assert res.status_code == 200, f"Question '{q_id}' failed with status {res.status_code}"
        assert res.json()["question_id"] == q_id
        assert len(res.json()["answer_text"]) > 0

    # And confirm it *does* reject a missing skill rather than inventing one.
    res_missing = await client.post(
        "/api/qa/ask", json={"session_id": session_id, "question_id": "what_if_i_already_know_x"}
    )
    assert res_missing.status_code == 422

@pytest.mark.anyio
async def test_live_jobs_endpoint(client):
    res = await client.get("/api/live/jobs?role=Data%20Scientist")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["success", "cache", "degraded", "unavailable"]

@pytest.mark.anyio
async def test_github_verify_endpoint(client):
    res_prof = await client.post("/api/profile/manual-skills", json={"skills": ["Python"]})
    session_id = res_prof.json()["session_id"]

    res = await client.post("/api/live/github-verify", json={
        "session_id": session_id,
        "github_username": "torvalds"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["success", "no_data", "unavailable"]
