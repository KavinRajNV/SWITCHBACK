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
async def test_related_occupations_valid(client):
    response = await client.get("/api/roles/15-2051.00/related")
    assert response.status_code == 200
    data = response.json()
    assert data["soc_code"] == "15-2051.00"
    assert data["count"] > 0
    assert len(data["related_occupations"]) > 0
    first = data["related_occupations"][0]
    assert "onet_soc_code" in first
    assert "title" in first
    assert first["relatedness_tier"] == "Primary-Short"

@pytest.mark.anyio
async def test_related_occupations_empty(client):
    response = await client.get("/api/roles/99-9999.00/related")
    assert response.status_code == 200
    data = response.json()
    assert data["soc_code"] == "99-9999.00"
    assert data["count"] == 0
    assert data["related_occupations"] == []
