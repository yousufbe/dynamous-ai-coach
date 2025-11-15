from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: PostgreSQL connection string used for RAG storage.
        embedding_model: Identifier for the embedding model used to create
            dense vectors for documents and queries.
        llm_model: Identifier or path for the primary assistant language
            model used to answer user questions.
    """

    database_url: str
    embedding_model: str
    llm_model: str


def get_settings() -> Settings:
    """Load application settings from environment variables.

    Defaults are chosen to match the recommendations in the project
    documentation so that a fresh environment behaves sensibly without
    additional configuration.

    Returns:
        Settings instance containing the current configuration values.
    """
    database_url: str = os.getenv("DATABASE_URL", "")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL",
        "Qwen/Qwen3-Embedding-0.6B",
    )
    llm_model: str = os.getenv(
        "LLM_MODEL",
        "Qwen/Qwen3-VL-8B-Instruct",
    )
    return Settings(
        database_url=database_url,
        embedding_model=embedding_model,
        llm_model=llm_model,
    )

