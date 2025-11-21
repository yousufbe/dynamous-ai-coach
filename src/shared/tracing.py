from __future__ import annotations

import contextlib
import datetime as dt
import os
from dataclasses import dataclass
from typing import Any, Iterator, Protocol

from src.shared.logging import get_logger

logger = get_logger(__name__)


class SpanProtocol(Protocol):
    """Minimal protocol for spans used by tracing helpers."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Attach an attribute to the span."""

    def end(self, **attributes: Any) -> None:
        """Mark the span as complete."""


class _NoOpSpan:
    def __init__(self, name: str, correlation_id: str | None) -> None:
        self.name = name
        self.correlation_id = correlation_id

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, exc_type: Any, exc: Any, _tb: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        logger.debug(
            "tracing_noop_attribute",
            span=self.name,
            correlation_id=self.correlation_id,
            key=key,
            value=value,
        )

    def end(self, **attributes: Any) -> None:
        logger.debug(
            "tracing_noop_end",
            span=self.name,
            correlation_id=self.correlation_id,
            attributes=attributes,
        )


class _NoOpTracer:
    def __init__(self) -> None:
        self.enabled = False

    @contextlib.contextmanager
    def span(
        self,
        *,
        name: str,
        correlation_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[SpanProtocol]:
        span = _NoOpSpan(name=name, correlation_id=correlation_id)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span
        span.end()


@dataclass(frozen=True)
class TracerConfig:
    """Configuration required to enable Langfuse traces."""

    enabled: bool
    host: str | None
    public_key: str | None
    secret_key: str | None


class Tracer:
    """Wrapper around Langfuse with a safe no-op fallback."""

    def __init__(self, config: TracerConfig) -> None:
        self._config = config
        self._client: Any | None = None
        self.enabled = False
        self._setup_client()

    def _setup_client(self) -> None:
        if not self._config.enabled:
            logger.info("tracing_disabled")
            return
        try:
            from langfuse import Langfuse  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            logger.warning("tracing_langfuse_import_failed")
            return
        host = self._config.host or "http://127.0.0.1:3000"
        public_key = self._config.public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = self._config.secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        if not public_key or not secret_key:
            logger.warning("tracing_langfuse_missing_keys")
            return
        try:
            self._client = Langfuse(
                host=host,
                public_key=public_key,
                secret_key=secret_key,
            )
            self.enabled = True
            logger.info("tracing_langfuse_enabled", host=host)
        except Exception:  # pragma: no cover - optional dependency
            logger.exception("tracing_langfuse_init_failed", host=host)
            self._client = None
            self.enabled = False

    @contextlib.contextmanager
    def span(
        self,
        *,
        name: str,
        correlation_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[SpanProtocol]:
        if not self.enabled or self._client is None:
            span = _NoOpSpan(name=name, correlation_id=correlation_id)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span
            span.end()
            return
        try:
            trace = self._client.trace(
                id=correlation_id,
                name=name,
                timestamp=dt.datetime.utcnow(),
                metadata=attributes or {},
            )
            span = trace.span(name=name, start_time=dt.datetime.utcnow())
        except Exception:  # pragma: no cover - defensive
            logger.exception("tracing_span_start_failed", span_name=name)
            span = _NoOpSpan(name=name, correlation_id=correlation_id)
        try:
            yield span
        except Exception as exc:
            try:
                span.set_attribute("error", str(exc))
            finally:
                span.end()
            raise
        else:
            span.end()


def build_tracer(
    *,
    enabled: bool,
    host: str | None,
    public_key: str | None,
    secret_key: str | None,
) -> Tracer:
    config = TracerConfig(
        enabled=enabled,
        host=host,
        public_key=public_key,
        secret_key=secret_key,
    )
    return Tracer(config=config)


def noop_tracer() -> Tracer:
    return Tracer(TracerConfig(enabled=False, host=None, public_key=None, secret_key=None))
