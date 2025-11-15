from fastapi import FastAPI

from src.agent.agent import ChatRequest, ChatResponse, RAGAgent
from src.shared.logging import LoggerProtocol, get_logger


logger: LoggerProtocol = get_logger(__name__)
app: FastAPI = FastAPI(title="Local RAG AI Assistant")
_agent: RAGAgent = RAGAgent()


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
    logger.info("chat_request_received", query_length=len(request.query))
    response: ChatResponse = await _agent.chat(request=request)
    logger.info(
        "chat_response_sent",
        answer_length=len(response.answer),
        citations_count=len(response.citations),
    )
    return response

