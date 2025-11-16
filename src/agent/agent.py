from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Sequence

from pydantic import BaseModel

from src.agent.llm_client import LLMClient, LLMConfig, LLMResult
from src.rag_pipeline.config import get_rag_ingestion_config
from src.rag_pipeline.embeddings import QwenEmbeddingClient
from src.rag_pipeline.persistence import PsycopgDatabaseClient, SupabaseStore
from src.rag_pipeline.retrieval import DatabaseRetriever, NullRetriever, RetrievedChunk, RetrieverProtocol
from src.shared.config import Settings, get_settings
from src.shared.logging import LoggerProtocol, get_logger
from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse
from src.tools.ingestion_skill.tool import ingestion_skill_tool


class ChatRequest(BaseModel):
    """Request payload for chat interactions with the RAG agent.

    Attributes:
        query: Natural language query from the user.
    """

    query: str


class Citation(BaseModel):
    """Reference to a retrieved document chunk used in an answer.

    Attributes:
        source: Human-readable source identifier (file path, URL, etc.).
        chunk_id: Optional unique identifier for the chunk in storage.
        score: Optional relevance score returned by the retriever.
    """

    source: str
    chunk_id: str | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    """Response produced by the RAG agent.

    Attributes:
        answer: Assistant answer generated from retrieved context.
        citations: List of document references supporting the answer.
    """

    answer: str
    citations: list[Citation]


@dataclass
class RAGAgent:
    """RAG agent facade that wires retrieval and generation together.

    Attributes:
        settings: Application configuration loaded from environment variables.
        retriever: Service used to fetch relevant context chunks.
        llm_client: Client used to generate grounded answers.
    """

    settings: Settings
    retriever: RetrieverProtocol
    llm_client: LLMClient

    def __init__(
        self,
        settings: Settings | None = None,
        retriever: RetrieverProtocol | None = None,
        llm_client: LLMClient | None = None,
        logger: LoggerProtocol | None = None,
    ) -> None:
        """Initialize the RAG agent with configuration settings.

        Args:
            settings: Optional preconstructed Settings instance. When omitted,
                settings are loaded from environment variables.
            retriever: Optional retrieval service override for testing.
            llm_client: Optional LLM client override for testing.
            logger: Optional logger override.
        """
        self.settings = settings if settings is not None else get_settings()
        self._logger = logger or get_logger(__name__)
        self.tools: dict[str, object] = {
            "ingestion_skill": ingestion_skill_tool,
        }
        self._db_client: PsycopgDatabaseClient | None = None
        self._embedding_client: QwenEmbeddingClient | None = None
        self.retriever = retriever or self._build_retriever()
        self.llm_client = llm_client or self._build_llm_client()
        self._logger.info(
            "rag_agent_initialized",
            llm_model=self.settings.llm_model,
            embedding_model=self.settings.embedding_model,
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Generate an answer for the given chat request.

        Retrieval and generation are orchestrated here: the retriever fetches
        relevant chunks, and the LLM client produces a grounded answer.

        Args:
            request: ChatRequest containing the user query.

        Returns:
            ChatResponse with a grounded answer and associated citations.
        """
        self._logger.info(
            "chat_started",
            query_length=len(request.query),
        )
        retrieved_chunks = await self.retriever.retrieve(
            request.query,
            top_k=self.settings.retrieval_top_k,
            min_score=self.settings.retrieval_min_score,
        )
        context_blocks: list[str] = [self._format_context(chunk) for chunk in retrieved_chunks]
        llm_result: LLMResult = await asyncio.to_thread(
            self.llm_client.generate_answer,
            system_prompt=(
                "You are a company assistant. Answer using only the provided context. "
                "Cite sources by name, keep answers concise, and avoid speculation."
            ),
            query=request.query,
            context=context_blocks,
        )
        answer_text = llm_result.content
        citations = self._build_citations(retrieved_chunks)
        response: ChatResponse = ChatResponse(answer=answer_text, citations=citations)
        self._logger.info(
            "chat_completed",
            answer_length=len(response.answer),
            citations_count=len(response.citations),
        )
        return response

    async def ingest_documents(self, request: IngestionSkillRequest) -> IngestionSkillResponse:
        """Expose the ingestion skill via the agent API."""
        return await ingestion_skill_tool(request)

    def _build_retriever(self) -> RetrieverProtocol:
        if not self.settings.rag_database_url:
            self._logger.warning("retriever_disabled_missing_database_url")
            return NullRetriever()
        try:
            config = get_rag_ingestion_config()
            merged_config = replace(
                config,
                database_url=self.settings.rag_database_url,
                embedding_model=self.settings.embedding_model,
            )
            self._embedding_client = QwenEmbeddingClient.from_config(
                config=merged_config,
                api_key=self.settings.qwen_api_key,
            )
            self._db_client = PsycopgDatabaseClient(merged_config.database_url)
            store = SupabaseStore(db=self._db_client, config=merged_config)
            return DatabaseRetriever(
                embedding_client=self._embedding_client,
                store=store,
                logger=self._logger,
            )
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "retriever_initialization_failed",
                error=str(exc),
            )
            return NullRetriever()

    def _build_llm_client(self) -> LLMClient:
        config = LLMConfig(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
        )
        return LLMClient(config=config, logger=self._logger)

    @staticmethod
    def _format_context(chunk: RetrievedChunk) -> str:
        source = chunk.document_name or chunk.source_id
        prefix = f"Source: {source} (score={chunk.score:.3f})"
        return f"{prefix}\n{chunk.content}"

    @staticmethod
    def _build_citations(chunks: Sequence[RetrievedChunk]) -> list[Citation]:
        citations: list[Citation] = []
        for chunk in chunks:
            source = chunk.document_name or chunk.source_id
            citations.append(
                Citation(
                    source=source,
                    chunk_id=chunk.chunk_id,
                    score=chunk.score,
                ),
            )
        return citations
