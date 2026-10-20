import asyncio

import pytest
from agents import OpenAIChatCompletionsModel
from agents.models import _openai_shared
from openai.types.chat import ChatCompletionChunk
from pydantic import SecretStr

from agent.config import Settings
from agent.llm import LlmConnection, ToolCallIndexFix

BASE = "https://example.test/v1/"


@pytest.fixture(autouse=True)
def restore_sdk_globals(monkeypatch):
    monkeypatch.setattr(_openai_shared, "_default_openai_client", None)
    monkeypatch.setattr(_openai_shared, "_use_responses_by_default", True)


def test_is_ready_follows_key_presence_without_network():
    assert LlmConnection(SecretStr("k"), BASE).is_ready() is True
    assert LlmConnection(None, BASE).is_ready() is False


def test_configure_points_the_sdk_at_the_provider_over_chat_completions():
    LlmConnection(SecretStr("k"), BASE).configure()
    client = _openai_shared.get_default_openai_client()
    assert client is not None
    assert str(client.base_url) == BASE
    assert _openai_shared.get_use_responses_by_default() is False


def test_configure_without_key_installs_no_client():
    LlmConnection(None, BASE).configure()
    assert _openai_shared.get_default_openai_client() is None


def test_model_settings_carry_the_provider_routing_preferences():
    default = LlmConnection(SecretStr("k"), BASE).model_settings()
    assert default.extra_body == {
        "provider": {"require_parameters": True, "data_collection": "deny"}
    }
    relaxed = LlmConnection(SecretStr("k"), BASE, False, "allow").model_settings()
    assert relaxed.extra_body == {
        "provider": {"require_parameters": False, "data_collection": "allow"}
    }


def test_settings_default_to_openrouter_and_ignore_gemini_variables(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL", "z-ai/glm-4.7-flash:floor")
    monkeypatch.setenv("GEMINI_API_KEY", "old-gemini-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://gemini.test/")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.llm_api_key is None
    assert settings.llm_base_url == "https://openrouter.ai/api/v1"
    connection = LlmConnection.from_settings(settings)
    assert connection.is_ready() is False


def test_settings_read_the_llm_variables(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL", "m")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_DATA_COLLECTION", "allow")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert LlmConnection.from_settings(settings).is_ready() is True
    assert settings.llm_data_collection == "allow"


def test_model_wraps_a_vendor_slug_around_the_providers_client():
    connection = LlmConnection(SecretStr("k"), BASE)
    assert connection.model("z-ai/glm-4.7-flash:floor") == "z-ai/glm-4.7-flash:floor"
    connection.configure()
    model = connection.model("z-ai/glm-4.7-flash:floor")
    assert isinstance(model, OpenAIChatCompletionsModel)
    assert model.model == "z-ai/glm-4.7-flash:floor"


def _chunk(*calls: dict) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_validate(
        {
            "id": "chunk",
            "created": 0,
            "model": "test",
            "object": "chat.completion.chunk",
            "choices": [
                {"index": 0, "delta": {"tool_calls": calls}, "finish_reason": None}
            ],
        }
    )


def test_tool_call_index_fix_assigns_distinct_indexes():
    chunk = _chunk(
        {"index": 99, "id": "call-a", "type": "function", "function": {}},
        {"index": 99, "type": "function", "function": {}},
        {"index": 99, "id": "call-b", "type": "function", "function": {}},
    )
    fixer = ToolCallIndexFix(object())

    assert fixer.fix(chunk) is chunk
    assert [call.index for call in chunk.choices[0].delta.tool_calls or []] == [0, 0, 1]


def test_tool_call_index_fix_forwards_async_chunks_and_stream_attrs():
    class Stream:
        value = "stream-value"

        def __aiter__(self):
            async def iterate():
                yield _chunk(
                    {"index": 9, "id": "call", "type": "function", "function": {}}
                )

            return iterate()

    async def collect():
        return [chunk async for chunk in ToolCallIndexFix(Stream())]

    chunks = asyncio.run(collect())
    calls = chunks[0].choices[0].delta.tool_calls
    assert calls is not None
    assert calls[0].index == 0
    assert ToolCallIndexFix(Stream()).value == "stream-value"


def test_settings_build_conninfo_and_choose_explicit_backend():
    settings = Settings(
        agent_model="test",
        data_backend="postgres",
        pghost="db.example",
        pgport=5432,
        pgdatabase="gluco",
        pguser="reader",
        pgpassword=SecretStr("secret"),
        pgsslmode="require",
    )
    conninfo = settings.database_conninfo
    assert conninfo is not None
    assert "host=db.example" in conninfo
    assert "dbname=gluco" in conninfo
    assert settings.effective_backend == "postgres"
    assert settings.effective_guardrail_model == "test"
