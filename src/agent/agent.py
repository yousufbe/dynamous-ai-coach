from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from src.shared.config import Settings, get_settings
from src.shared.logging import LoggerProtocol, get_logger
from src.tools.ingestion_skill.schemas import IngestionSkillRequest, IngestionSkillResponse
from src.tools.ingestion_skill.tool import ingestion_skill_tool

logger: LoggerProtocol = get_logger(__name__)


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
    """Minimal RAG agent facade used by the API layer.

    The implementation is intentionally simple and synchronous with respect to
    dependencies. Retrieval and generation backends will be integrated in this
    class once the RAG pipeline and tools are implemented.

    Attributes:
        settings: Application configuration loaded from environment variables.
    """

    settings: Settings

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the RAG agent with configuration settings.

        Args:
            settings: Optional preconstructed Settings instance. When omitted,
                settings are loaded from environment variables.
        """
        self.settings = settings if settings is not None else get_settings()
        self.tools: dict[str, object] = {
            "ingestion_skill": ingestion_skill_tool,
        }
        logger.info(
            "rag_agent_initialized",
            llm_model=self.settings.llm_model,
            embedding_model=self.settings.embedding_model,
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Generate an answer for the given chat request.

        This placeholder implementation echoes the query to confirm the wiring
        between the HTTP API and the agent. Retrieval and generation logic
        will be added in future iterations.

        Args:
            request: ChatRequest containing the user query.

        Returns:
            ChatResponse with a placeholder answer and no citations.
        """
        logger.info(
            "chat_started",
            query_length=len(request.query),
        )
        answer: str = (
            "This is a placeholder answer. The RAG pipeline has not been "
            f"implemented yet, but I received your query: {request.query!r}"
        )
        response: ChatResponse = ChatResponse(answer=answer, citations=[])
        logger.info(
            "chat_completed",
            answer_length=len(response.answer),
            citations_count=len(response.citations),
        )
        return response

    async def ingest_documents(self, request: IngestionSkillRequest) -> IngestionSkillResponse:
        """Expose the ingestion skill via the agent API."""
        return await ingestion_skill_tool(request)
