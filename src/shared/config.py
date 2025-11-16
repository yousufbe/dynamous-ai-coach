from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    """Fetch an integer from environment variables.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        Parsed integer value.
    """
    raw: str | None = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _get_float(name: str, default: float) -> float:
    """Fetch a float from environment variables.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        Parsed float value.
    """
    raw: str | None = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid float for {name}: {raw}") from exc


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: PostgreSQL connection string used for ingestion storage.
        rag_database_url: Optional override for Supabase/PGVector retrieval.
        embedding_model: Identifier for the embedding model used to create
            dense vectors for documents and queries.
        qwen_api_key: Optional token for Qwen embedding calls.
        llm_model: Identifier or path for the primary assistant language
            model used to answer user questions.
        llm_base_url: HTTP endpoint for chat/completions requests.
        llm_api_key: Optional token for the configured LLM endpoint.
        retrieval_top_k: Maximum number of chunks returned per query.
        retrieval_min_score: Minimum similarity score for retrieved chunks.
    """

    database_url: str
    rag_database_url: str
    embedding_model: str
    qwen_api_key: str | None
    llm_model: str
    llm_base_url: str
    llm_api_key: str | None
    retrieval_top_k: int
    retrieval_min_score: float


def get_settings() -> Settings:
    """Load application settings from environment variables.

    Defaults are chosen to match the recommendations in the project
    documentation so that a fresh environment behaves sensibly without
    additional configuration.

    Returns:
        Settings instance containing the current configuration values.
    """
    database_url: str = os.getenv("DATABASE_URL", "")
    rag_database_url: str = os.getenv("RAG_DATABASE_URL", database_url)
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "Qwen/Qwen3-Embedding-0.6B",
    )
    qwen_api_key: str | None = os.getenv("QWEN_API_KEY")
    llm_model: str = os.getenv(
        "LLM_MODEL",
        "Qwen/Qwen3-VL-8B-Instruct",
    )
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    retrieval_top_k: int = _get_int("RETRIEVAL_TOP_K", default=5)
    retrieval_min_score: float = _get_float("RETRIEVAL_MIN_SCORE", default=0.2)
    return Settings(
        database_url=database_url,
        rag_database_url=rag_database_url,
        embedding_model=embedding_model,
        qwen_api_key=qwen_api_key,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        retrieval_top_k=retrieval_top_k,
        retrieval_min_score=retrieval_min_score,
    )
