import pytest

from src.shared.config import Settings, get_settings


@pytest.mark.unit
def test_get_settings_uses_defaults_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_settings should populate default values when environment is empty."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("GPU_DEVICE", raising=False)

    settings: Settings = get_settings()

    assert settings.database_url == ""
    assert settings.embedding_model == "Qwen/Qwen3-Embedding-0.6B"
    assert settings.llm_model == "Qwen/Qwen3-VL-8B-Instruct"
    assert settings.gpu_device == "cuda:0"


@pytest.mark.unit
def test_get_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_settings should read configuration from environment variables."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://db.example/test")
    monkeypatch.setenv("EMBEDDING_MODEL", "Custom/Embedding")
    monkeypatch.setenv("LLM_MODEL", "Custom/LLM")
    monkeypatch.setenv("GPU_DEVICE", "cuda:2")

    settings: Settings = get_settings()

    assert settings.database_url == "postgresql://db.example/test"
    assert settings.embedding_model == "Custom/Embedding"
    assert settings.llm_model == "Custom/LLM"
    assert settings.gpu_device == "cuda:2"
