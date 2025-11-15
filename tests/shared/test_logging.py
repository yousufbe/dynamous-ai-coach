import logging

import pytest

from src.shared.logging import LoggerProtocol, StructuredLogger, get_logger


@pytest.mark.unit
def test_get_logger_returns_structured_logger() -> None:
    """get_logger should return a StructuredLogger instance implementing LoggerProtocol."""
    logger = get_logger("test_logger")
    assert isinstance(logger, StructuredLogger)
    assert isinstance(logger, LoggerProtocol)


@pytest.mark.unit
def test_structured_logger_emits_json(caplog: pytest.LogCaptureFixture) -> None:
    """StructuredLogger should serialize events and fields as JSON."""
    base_logger = logging.getLogger("structured_test")
    structured_logger = StructuredLogger(base_logger)

    with caplog.at_level(logging.INFO):
        structured_logger.info("test_event", key="value")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert '{"event": "test_event", "key": "value"}' in record.getMessage()

