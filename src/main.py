from uuid import uuid4

from fastapi import FastAPI

from src.agent.agent import ChatRequest, ChatResponse, RAGAgent
from src.shared.config import get_settings
from src.shared.logging import LoggerProtocol, get_logger


logger: LoggerProtocol = get_logger(__name__)
app: FastAPI = FastAPI(title="Local RAG AI Assistant")
_settings = get_settings()
_agent: RAGAgent = RAGAgent(settings=_settings)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary containing a simple status indicator.
    """
    logger.info("health_check_completed", status="ok")
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat endpoint that forwards queries to the RAG agent.

    Args:
        request: Chat request payload containing the user query.

    Returns:
        ChatResponse produced by the RAG agent.
    """
    correlation_id = uuid4().hex
    logger.info(
        "chat_request_received",
        query_length=len(request.query),
        correlation_id=correlation_id,
    )
    response: ChatResponse = await _agent.chat(request=request, correlation_id=correlation_id)
    logger.info(
        "chat_response_sent",
        answer_length=len(response.answer),
        citations_count=len(response.citations),
        correlation_id=correlation_id,
    )
    return response
