from typing import Any, Dict, List

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)

from ..messages import Completion, CompletionChunk, Message
from ..model_providers import ModelConfig, ModelProvider
from ..tools import Tool


class OpenAI(ModelProvider):

    def __init__(self, api_key: str, api_base: str):
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)

    def _prepare_model_config(self, config: ModelConfig) -> Dict[str, Any]:
        return config.model_dump()

    def _prepare_tools(self, tools: List[Tool]) -> List[ChatCompletionToolParam]:
        return tools  # type: ignore

    def _prepare_messages(self, messages) -> List[ChatCompletionMessageParam]:
        return_messages: List[ChatCompletionMessageParam] = []
        for message in messages:
            # have to do this because the openai library requires each message to have a literal role
            if message["role"] == "assistant":
                return_messages.append(
                    {"role": "assistant", "content": message["content"]}
                )
            elif message["role"] == "user":
                return_messages.append({"role": "user", "content": message["content"]})
            elif message["role"] == "system":
                return_messages.append(
                    {"role": "system", "content": message["content"]}
                )
            else:
                raise ValueError(f"Unknown role: {message['role']}")
        return return_messages

    def _format_completion(self, completion: ChatCompletion):
        return Completion(id=completion.id, choices=completion.choices)

    def _format_completion_chunk(self, chunk: ChatCompletionChunk):
        return CompletionChunk(id=chunk.id, choices=chunk.choices)

    async def complete(
        self,
        *,
        model_config: ModelConfig,
        messages: List[Message],
        tools: List[Tool],
    ):
        response = await self.client.chat.completions.create(
            stream=False,
            messages=self._prepare_messages(messages),
            tools=self._prepare_tools(tools),
            **self._prepare_model_config(config=model_config),
        )
        return self._format_completion(response)

    async def stream(
        self,
        *,
        model_config: ModelConfig,
        messages: List[Message],
        tools: List[Tool],
    ):
        async def _generator():
            response = await self.client.chat.completions.create(
                stream=True,
                messages=self._prepare_messages(messages),
                tools=self._prepare_tools(tools),
                **self._prepare_model_config(config=model_config),
            )
            async for chunk in response:
                yield self._format_completion_chunk(chunk)

        return _generator()


class Groq(OpenAI):
    def __init__(self, api_key, api_base="https://api.groq.com/openai/v1"):
        super().__init__(api_key, api_base)
