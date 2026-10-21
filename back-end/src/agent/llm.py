"""The LLM connection: the one module that knows which provider is behind the SDK.

Today that is OpenRouter's OpenAI-compatible endpoint, with model slugs such as
`z-ai/glm-4.7-flash:floor` (the `:floor` suffix picks the cheapest host). Callers
configure it once at startup and ask `is_ready()`; nothing else names the
provider. With a single provider live this is a module, not a seam; add an
adapter only if a second provider ever runs alongside it.
"""

from collections.abc import AsyncIterator
from functools import cached_property
from typing import Any, Literal

from agents import (
    Model,
    ModelSettings,
    OpenAIChatCompletionsModel,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from openai.resources.chat import AsyncChat
from openai.resources.chat.completions import AsyncCompletions
from openai.types.chat import ChatCompletionChunk
from pydantic import SecretStr

from agent.config import Settings


class ToolCallIndexFix:
    """Gives every streamed tool call its own index.

    Gemini's OpenAI-compatible stream (also behind OpenRouter) sends parallel tool
    calls under the same index; the SDK groups deltas by index and would merge two
    calls into one with unparseable arguments ('{...}{...}'), which Gemini then
    rejects. A delta that carries a new call id starts a new index; deltas without
    an id continue the current call.
    """

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._indexes: dict[str, int] = {}
        self._current: int | None = None

    def fix(self, chunk: ChatCompletionChunk) -> ChatCompletionChunk:
        for choice in chunk.choices:
            for call in choice.delta.tool_calls or []:
                if call.id:
                    self._current = self._indexes.setdefault(
                        call.id, len(self._indexes)
                    )
                if self._current is not None:
                    call.index = self._current
        return chunk

    def __aiter__(self) -> AsyncIterator[ChatCompletionChunk]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[ChatCompletionChunk]:
        async for chunk in self._stream:
            yield self.fix(chunk)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _Completions(AsyncCompletions):
    async def create(self, **kwargs: Any) -> Any:  # type: ignore[override]
        response = await super().create(**kwargs)
        return ToolCallIndexFix(response) if kwargs.get("stream") is True else response


class _Chat(AsyncChat):
    @cached_property
    def completions(self) -> AsyncCompletions:  # type: ignore[override]
        return _Completions(self._client)


class ChatCompletionsClient(AsyncOpenAI):
    """AsyncOpenAI with the tool-call index fix applied to streamed completions."""

    @cached_property
    def chat(self) -> AsyncChat:  # type: ignore[override]
        return _Chat(self)


class LlmConnection:
    """The connection to the OpenAI-compatible provider: builds models, the per-call
    routing settings and configures the Agents SDK once at startup.
    """

    def __init__(
        self,
        api_key: SecretStr | None,
        base_url: str,
        require_parameters: bool = True,
        data_collection: Literal["allow", "deny"] = "deny",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._require_parameters = require_parameters
        self._data_collection = data_collection
        self._client: ChatCompletionsClient | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "LlmConnection":
        return cls(
            settings.llm_api_key,
            settings.llm_base_url,
            settings.llm_require_parameters,
            settings.llm_data_collection,
        )

    def model(self, name: str) -> Model | str:
        """The SDK model for a slug such as `z-ai/glm-4.7-flash:floor`.

        A plain string would make the SDK read `z-ai/` as a provider prefix and
        refuse it, so the slug is wrapped around this connection's client. Before
        `configure()` (or with no key) the bare name comes back; nothing can run
        without a client anyway.
        """
        if self._client is None:
            return name
        return OpenAIChatCompletionsModel(model=name, openai_client=self._client)

    def model_settings(self) -> ModelSettings:
        """Per-call provider routing, shared by the agent and the guardrails."""
        provider = {
            "require_parameters": self._require_parameters,
            "data_collection": self._data_collection,
        }
        return ModelSettings(extra_body={"provider": provider})

    def is_ready(self) -> bool:
        """True when a key is configured; never contacts the provider."""
        return self._api_key is not None

    def configure(self) -> None:
        """Point the Agents SDK at the provider. Call once, before any run."""
        # SDK tracing uploads tool outputs (person-level health data) to OpenAI.
        set_tracing_disabled(True)
        # The OpenAI-compat layer speaks Chat Completions, not Responses.
        set_default_openai_api("chat_completions")
        if self._api_key is not None:
            self._client = ChatCompletionsClient(
                api_key=self._api_key.get_secret_value(), base_url=self._base_url
            )
            set_default_openai_client(self._client, use_for_tracing=False)
