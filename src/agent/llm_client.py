from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter, sleep
from typing import Sequence

import requests

from src.shared.logging import LoggerProtocol, get_logger
from src.shared.tracing import Tracer, noop_tracer


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Configuration for invoking the LLM endpoint.

    Attributes:
        model: Identifier for the target model.
        base_url: Base URL for the chat/completions API. When empty, the
            client falls back to a deterministic local response.
        api_key: Optional token used for authorization.
        timeout_seconds: HTTP request timeout for each attempt.
        max_retries: Number of retries for transient failures.
        retry_backoff_seconds: Base backoff used between retries.
    """

    model: str
    base_url: str
    api_key: str | None
    timeout_seconds: int = 30
    max_retries: int = 1
    retry_backoff_seconds: float = 1.0


@dataclass(frozen=True, slots=True)
class LLMResult:
    """LLM response content."""

    content: str


class LLMClient:
    """Minimal OpenAI-compatible chat client with retry/backoff."""

    def __init__(
        self,
        config: LLMConfig,
        *,
        session: requests.Session | None = None,
        logger: LoggerProtocol | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()
        self._logger = logger or get_logger(__name__)
        self._tracer = tracer or noop_tracer()

    def generate_answer(
        self,
        *,
        system_prompt: str,
        query: str,
        context: Sequence[str],
        correlation_id: str | None = None,
    ) -> LLMResult:
        """Generate an answer grounded in the provided context.

        Falls back to a deterministic templated response when no base URL is
        configured to keep local development working without an LLM endpoint.

        Args:
            system_prompt: Instruction to guide the model behaviour.
            query: Original user query.
            context: Ordered list of context strings derived from retrieval.

        Returns:
            LLMResult containing the generated content.
        """
        if not self._config.base_url:
            combined_context = "\n".join(context)
            content = (
                "LLM endpoint not configured; returning summarized context. "
                f"Query: {query}\nContext:\n{combined_context}"
            ).strip()
            return LLMResult(content=content)

        url = f"{self._config.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._format_prompt(query=query, context=context)},
        ]
        attempt = 0
        start = perf_counter()
        last_error: str | None = None
        with self._tracer.span(
            name="llm_call",
            correlation_id=correlation_id,
            attributes={"model": self._config.model, "temperature": 0.2},
        ):
            while attempt <= self._config.max_retries:
                try:
                    response = self._session.post(
                        url,
                        json={"model": self._config.model, "messages": messages, "temperature": 0.2},
                        headers=headers,
                        timeout=self._config.timeout_seconds,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    duration_ms = (perf_counter() - start) * 1000.0
                    self._logger.info(
                        "llm_call_completed",
                        duration_ms=duration_ms,
                        retry_count=attempt,
                        correlation_id=correlation_id,
                    )
                    return LLMResult(content=str(content))
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    self._logger.warning(
                        "llm_call_failed",
                        attempt=attempt,
                        error=last_error,
                        correlation_id=correlation_id,
                    )
                    attempt += 1
                    if attempt > self._config.max_retries:
                        break
                    backoff = self._config.retry_backoff_seconds * max(1, attempt) * random.uniform(0.5, 1.5)
                    sleep(backoff)
        fallback_content = (
            "Unable to reach the LLM endpoint at this time. "
            f"Latest error: {last_error or 'unknown'}"
        )
        return LLMResult(content=fallback_content)

    @staticmethod
    def _format_prompt(*, query: str, context: Sequence[str]) -> str:
        context_lines = "\n\n".join(context)
        return (
            "Answer the user query using only the provided context. "
            "Cite sources explicitly and avoid inventing details.\n\n"
            f"Context:\n{context_lines}\n\n"
            f"User query: {query}"
        )
