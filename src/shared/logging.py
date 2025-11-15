from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol describing the logging interface used across the project."""

    def debug(self, event: str, **kwargs: object) -> None:
        """Log a debug event with structured context."""

    def info(self, event: str, **kwargs: object) -> None:
        """Log an informational event with structured context."""

    def warning(self, event: str, **kwargs: object) -> None:
        """Log a recoverable issue or unusual situation."""

    def error(self, event: str, **kwargs: object) -> None:
        """Log a non-fatal error."""

    def exception(self, event: str, **kwargs: object) -> None:
        """Log an exception with a full stack trace."""


@dataclass
class StructuredLogger:
    """Adapter that formats log events as structured JSON.

    This wrapper ensures all logs follow the same shape:
    a JSON object containing the event name plus any keyword arguments
    supplied by the caller. The wrapped standard logger is responsible
    for output formatting, log levels and handlers.

    Attributes:
        _logger: Underlying standard-library logger instance.
    """

    _logger: logging.Logger

    def debug(self, event: str, **kwargs: object) -> None:
        """Log a debug-level event."""
        self._logger.debug(self._format(event=event, fields=kwargs))

    def info(self, event: str, **kwargs: object) -> None:
        """Log an info-level event."""
        self._logger.info(self._format(event=event, fields=kwargs))

    def warning(self, event: str, **kwargs: object) -> None:
        """Log a warning-level event."""
        self._logger.warning(self._format(event=event, fields=kwargs))

    def error(self, event: str, **kwargs: object) -> None:
        """Log an error-level event."""
        self._logger.error(self._format(event=event, fields=kwargs))

    def exception(self, event: str, **kwargs: object) -> None:
        """Log an exception with a stack trace."""
        self._logger.exception(self._format(event=event, fields=kwargs))

    @staticmethod
    def _format(event: str, fields: dict[str, object]) -> str:
        """Format an event name and fields as a JSON string."""
        payload: dict[str, object] = {"event": event, **fields}
        return json.dumps(payload, default=str)


def _configure_root_logger() -> None:
    """Configure the root logger with sensible defaults.

    This setup is intentionally minimal: log records include timestamps,
    level names, logger names and the JSON-formatted message produced by
    StructuredLogger. Applications that need more advanced logging can
    extend this configuration without changing the StructuredLogger API.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> LoggerProtocol:
    """Return a structured logger for the given module name.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        LoggerProtocol implementation that logs JSON-formatted events using
        the standard logging infrastructure.
    """
    _configure_root_logger()
    base_logger: logging.Logger = logging.getLogger(name)
    return StructuredLogger(base_logger)
