from fastapi.testclient import TestClient
import pytest

from src.main import app


client: TestClient = TestClient(app)


@pytest.mark.unit
def test_health_returns_ok() -> None:
    """Health endpoint should return an OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_chat_endpoint_responds() -> None:
    """Chat endpoint should return a non-empty answer."""
    payload = {"query": "How do I use this assistant?"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["answer"], str)
    assert data["answer"]
    assert isinstance(data["citations"], list)

