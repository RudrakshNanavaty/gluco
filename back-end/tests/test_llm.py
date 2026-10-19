import pytest
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


def test_tool_call_index_fix_assigns_distinct_indexes_and_preserves_stream_attrs():
    chunk = ChatCompletionChunk.model_validate(
        {
            "id": "chunk",
            "created": 0,
            "model": "test",
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 99,
                                "id": "call-a",
                                "type": "function",
                                "function": {},
                            },
                            {"index": 99, "type": "function", "function": {}},
                            {
                                "index": 99,
                                "id": "call-b",
                                "type": "function",
                                "function": {},
                            },
                        ]
                    },
                    "finish_reason": None,
                }
            ],
        }
    )
    stream = object()
    fixer = ToolCallIndexFix(stream)

    assert fixer.fix(chunk) is chunk
    assert [call.index for call in chunk.choices[0].delta.tool_calls or []] == [0, 0, 1]


def test_tool_call_index_fix_forwards_async_chunks():
    class Stream:
        def __init__(self):
            self.value = "stream-value"

        def __aiter__(self):
            async def iterate():
                yield ChatCompletionChunk.model_validate(
                    {
                        "id": "chunk",
                        "created": 0,
                        "model": "test",
                        "object": "chat.completion.chunk",
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 9,
                                            "id": "call",
                                            "type": "function",
                                            "function": {},
                                        }
                                    ]
                                },
                                "finish_reason": None,
                            }
                        ],
                    }
                )

            return iterate()

    async def collect():
        return [chunk async for chunk in ToolCallIndexFix(Stream())]

    import asyncio

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
