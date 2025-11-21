import datetime as dt

import pytest

from src.agent.agent import ChatRequest, ChatResponse, RAGAgent
from src.agent.llm_client import LLMResult
from src.rag_pipeline.retrieval import RetrievedChunk, RetrieverProtocol
from src.rag_pipeline.schemas import IngestionResult, IngestionStatistics
from src.shared.config import Settings
from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse


def _build_settings() -> Settings:
    return Settings(
        database_url="postgresql://localhost:5432/example",
        rag_database_url="postgresql://localhost:5432/example",
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
        qwen_api_key=None,
        llm_model="Qwen/Qwen3-VL-8B-Instruct",
        llm_base_url="",
        llm_api_key=None,
        retrieval_top_k=3,
        retrieval_min_score=0.2,
        langfuse_enabled=False,
        langfuse_host=None,
        langfuse_public_key=None,
        langfuse_secret_key=None,
        gpu_device="cuda:0",
    )


class FakeRetriever(RetrieverProtocol):
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, float]] = []

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int,
        min_score: float,
        correlation_id: str | None = None,
    ) -> list[RetrievedChunk]:
        self.calls.append((query, top_k, min_score))
        return [
            RetrievedChunk(
                chunk_id="chunk-1",
                source_id="source-1",
                document_name="doc-one",
                content="First chunk content",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk-2",
                source_id="source-2",
                document_name="doc-two",
                content="Second chunk content",
                score=0.8,
                metadata={},
            ),
        ]


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[str]]] = []

    def generate_answer(
        self,
        *,
        system_prompt: str,
        query: str,
        context: list[str],
        correlation_id: str | None = None,
    ) -> LLMResult:
        self.calls.append((system_prompt, query, context))
        return LLMResult(content=f"Answer for {query} with {len(context)} contexts")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_chat_uses_retrieval_and_llm() -> None:
    """RAGAgent.chat should request retrieval and surface citations."""
    settings = _build_settings()
    retriever = FakeRetriever()
    llm_client = FakeLLMClient()
    agent = RAGAgent(settings=settings, retriever=retriever, llm_client=llm_client)
    request = ChatRequest(query="Test query")

    response: ChatResponse = await agent.chat(request=request)

    assert isinstance(response, ChatResponse)
    assert response.answer.startswith("Answer for Test query")
    assert len(response.citations) == 2
    assert retriever.calls == [("Test query", settings.retrieval_top_k, settings.retrieval_min_score)]
    assert llm_client.calls and llm_client.calls[0][1] == "Test query"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_agent_ingestion_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Agent should expose the ingestion skill tool."""
    settings = _build_settings()
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
