import datetime as dt

import pytest

from src.agent.agent import ChatRequest, ChatResponse, RAGAgent
from src.rag_pipeline.schemas import IngestionResult, IngestionStatistics
from src.shared.config import Settings
from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_chat_returns_response() -> None:
    """RAGAgent.chat should return a ChatResponse with an answer."""
    settings = Settings(
        database_url="postgresql://localhost:5432/example",
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
        llm_model="Qwen/Qwen3-VL-8B-Instruct",
    )
    agent = RAGAgent(settings=settings)
    request = ChatRequest(query="Test query")

    response: ChatResponse = await agent.chat(request=request)

    assert isinstance(response, ChatResponse)
    assert response.answer
    assert isinstance(response.citations, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_ingestion_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent should expose the ingestion skill tool."""
    settings = Settings(
        database_url="postgresql://localhost:5432/example",
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
        llm_model="Qwen/Qwen3-VL-8B-Instruct",
    )
    now = dt.datetime.now(tz=dt.timezone.utc)
    ingestion_result = IngestionResult(
        started_at=now,
        completed_at=now,
        pipeline_id="demo",
        documents=[],
        stats=IngestionStatistics(
            documents_discovered=0,
            documents_ingested=0,
            documents_failed=0,
            chunks_created=0,
        ),
    )

    async def fake_tool(request: IngestionSkillRequest) -> IngestionSkillResponse:
        return IngestionSkillResponse(
            summary_text="ok",
            ingested_count=0,
            failed_count=0,
            duration_seconds=0.0,
            warnings=[],
            result=ingestion_result,
        )

    monkeypatch.setattr("src.agent.agent.ingestion_skill_tool", fake_tool)
    agent = RAGAgent(settings=settings)
    response = await agent.ingest_documents(IngestionSkillRequest())
    assert isinstance(response, IngestionSkillResponse)
    assert "ingestion_skill" in agent.tools
