from fastapi.testclient import TestClient
import pytest

from src.agent.agent import ChatRequest, ChatResponse, Citation
from src.main import app


client: TestClient = TestClient(app)


@pytest.mark.unit
def test_health_returns_ok() -> None:
    """Health endpoint should return an OK status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_chat_endpoint_responds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chat endpoint should return a grounded answer shape."""

    class FakeAgent:
        async def chat(self, request: ChatRequest, *, correlation_id: str | None = None) -> ChatResponse:
            return ChatResponse(
                answer=f"Echo: {request.query}",
                citations=[Citation(source="doc-one", chunk_id="1", score=0.9)],
            )

    monkeypatch.setattr("src.main._agent", FakeAgent())
    payload = {"query": "How do I use this assistant?"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"].startswith("Echo")
    assert data["citations"] == [{"source": "doc-one", "chunk_id": "1", "score": 0.9}]
