import pytest
from httpx import AsyncClient

async def test_health_endpoint(client: AsyncClient):
    """Test that the /health endpoint returns a 200 OK and reports healthy systems."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"
