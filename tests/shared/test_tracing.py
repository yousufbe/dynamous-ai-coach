import pytest

from src.shared.tracing import build_tracer, noop_tracer


@pytest.mark.unit
def test_noop_tracer_span_runs_cleanly() -> None:
    tracer = noop_tracer()
    with tracer.span(name="noop-test", correlation_id="corr-1") as span:
        span.set_attribute("key", "value")
    assert tracer.enabled is False


@pytest.mark.unit
def test_disabled_langfuse_config_falls_back_to_noop() -> None:
    tracer = build_tracer(
        enabled=False,
        host=None,
        public_key=None,
        secret_key=None,
    )
    with tracer.span(name="disabled") as span:
        span.end()
    assert tracer.enabled is False
