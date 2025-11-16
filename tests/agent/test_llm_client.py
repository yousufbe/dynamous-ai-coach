import pytest

from src.agent.llm_client import LLMClient, LLMConfig, LLMResult


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, json: dict[str, object], headers: dict[str, str], timeout: int) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": "llm response content",
                        },
                    },
                ],
            },
        )


@pytest.mark.unit
def test_llm_client_fallback_without_endpoint() -> None:
    config = LLMConfig(model="demo", base_url="", api_key=None)
    client = LLMClient(config=config)

    result: LLMResult = client.generate_answer(
        system_prompt="test system",
        query="hello",
        context=["ctx"],
    )

    assert "hello" in result.content
    assert "Context" in result.content


@pytest.mark.unit
def test_llm_client_uses_session_post() -> None:
    session = _FakeSession()
    config = LLMConfig(model="demo", base_url="http://llm.local", api_key="token", max_retries=0)
    client = LLMClient(config=config, session=session)

    result = client.generate_answer(system_prompt="sys", query="hi", context=["ctx1", "ctx2"])

    assert result.content == "llm response content"
    assert session.calls
    call = session.calls[0]
    assert call["url"] == "http://llm.local/v1/chat/completions"
    assert call["json"]["model"] == "demo"
    assert call["json"]["messages"][1]["content"].startswith("Answer the user query")
    assert call["headers"]["Authorization"] == "Bearer token"
