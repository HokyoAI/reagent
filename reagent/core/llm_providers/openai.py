from typing import Any, Dict, List, TypedDict

from openai import NOT_GIVEN, AsyncOpenAI, pydantic_function_tool
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionToolParam,
)
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from pydantic import BaseModel

from reagent.reagent.core.messages import (
    Completion,
    CompletionChunk,
    Message,
    ToolCall,
    ToolCallChunk,
)
from reagent.reagent.core.model_providers import ModelConfig, ModelProvider

from ..tools import Tool


class OpenAI(ModelProvider):

    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)

    def _prepare_generic_config(self, config: ModelConfig) -> Dict[str, Any]:
        """
        Prepares the generic configuration for the model provider.

        Args:
            config (ModelConfig): The model configuration.

        Returns:
            Dict[str, Any]: A dictionary containing the configuration parameters.
        """
        return config.generic.model_dump()

    def _prepare_tool_params(
        self, tools: List[Tool[BaseModel, BaseModel]], config: ModelConfig
    ) -> Dict[str, Any]:
        """
        Prepares a list of tools to be sent to the OpenAI API.

        Args:
            tools (List[Tool]): The tools to be converted.

        Returns:
            List[ChatCompletionToolParam]: The appropriate format for OpenAI tools.
        """

        if tools:
            tool_params = {
                "tools": [
                    pydantic_function_tool(
                        tool.input_model, name=tool.name, description=tool.description
                    )
                    for tool in tools
                ],
                **config.tool.model_dump(),
            }
            return tool_params
        else:
            return {}

    def _prepare_messages(
        self, messages: List[Message]
    ) -> List[ChatCompletionMessageParam]:
        """
        Prepares a list of messages to be sent to the OpenAI API.

        Args:
            messages (List[Message]): The messages to be converted.

        Returns:
            List[ChatCompletionMessageParam]: The appropriate message format for OpenAI's API.
        """
        return_messages: List[ChatCompletionMessageParam] = []
        for message in messages:
            if message.role == "assistant":
                return_messages.append(
                    {"role": "assistant", "content": message.content}
                )
            elif message.role == "user":
                return_messages.append({"role": "user", "content": message.content})
            elif message.role == "system":
                return_messages.append({"role": "system", "content": message.content})
            elif message.role == "tool":
                return_messages.append(
                    {
                        "role": "tool",
                        "content": message.content,
                        "tool_call_id": message.tool_call_id,
                    }
                )
            else:
                raise ValueError(f"Unknown message type: {type(message)}")
        return return_messages

    def _format_tool_calls(
        self, tool_calls: List[ChatCompletionMessageToolCall]
    ) -> Dict[int, ToolCall]:
        """
        Converts OpenAI ChatCompletionMessageToolCall objects into internal ToolCall format.

        Args:
            tool_calls (List[ChatCompletionMessageToolCall]): List of tool calls from OpenAI's chat completion response.

        Returns:
            Dict[int, ToolCall]: Dictionary of tool call objects, with index as the key, containing:
                - index: Sequential position in the list (0-based)
                - id: Original tool call ID
                - arguments: Function arguments from the original tool call
                - name: Function name from the original tool call
        """
        return {
            i: ToolCall(
                index=i,
                id=tool_call.id,
                arguments=tool_call.function.arguments,
                name=tool_call.function.name,
            )
            for i, tool_call in enumerate(tool_calls)
        }

    def _format_completion(self, completion: ChatCompletion) -> Completion:
        """
        Formats the completion response to the generic completion response.

        Args:
            completion (ChatCompletion): The completion to be formatted.

        Returns:
            Completion: The libraries completion format.
        """
        choice = completion.choices[0]
        message = choice.message
        finish_reason = choice.finish_reason
        if (
            finish_reason == "function_call"
        ):  # pragma: no cover # deprecated OpenAI response
            finish_reason = "tool_calls"
        reasoning = None
        if message.model_extra:
            reasoning: str | None = message.model_extra.get("reasoning")
        return Completion(
            id=completion.id,
            content=message.content,
            refusal=message.refusal,
            tool_calls=(
                self._format_tool_calls(message.tool_calls)
                if message.tool_calls
                else None
            ),
            finish_reason=finish_reason,
            reasoning=reasoning,
        )

    def _format_tool_calls_chunk(
        self, tool_calls_chunk: List[ChoiceDeltaToolCall]
    ) -> Dict[int, ToolCallChunk]:
        """
        Converts streaming OpenAI ChoiceDeltaToolCall objects into internal ToolCallChunk format.

        This method processes chunks of tool calls received during streaming responses,
        where function arguments and names may be incomplete or None.

        Args:
            tool_calls_chunk (List[ChoiceDeltaToolCall]): List of partial tool calls from a streaming response chunk.

        Returns:
            Dict[int, ToolCallChunk]: dictionary of partial tool call objects, with index as the key, containing:
                - index: Original tool call index from the chunk
                - id: Tool call ID
                - arguments: Partial function arguments (None if function not present)
                - name: Partial function name (None if function not present)
        """
        return {
            tool_call.index: ToolCallChunk(
                index=tool_call.index,
                id=tool_call.id,
                arguments=tool_call.function.arguments if tool_call.function else None,
                name=tool_call.function.name if tool_call.function else None,
            )
            for tool_call in tool_calls_chunk
        }

    def _format_completion_chunk(self, chunk: ChatCompletionChunk) -> CompletionChunk:
        """
        Formats the OpenAI completion chunk response to the generic completion chunk response.

        Args:
            chunk (ChatCompletionChunk): The completion chunk to be formatted.

        Returns:
            CompletionChunk: The libraries completion format.
        """
        choice = chunk.choices[0]
        delta = choice.delta
        finish_reason = choice.finish_reason
        if (
            finish_reason == "function_call"
        ):  # pragma: no cover # deprecated OpenAI response
            finish_reason = "tool_calls"
        reasoning = None
        if delta.model_extra:
            reasoning: str | None = delta.model_extra.get("reasoning")
        return CompletionChunk(
            id=chunk.id,
            content=delta.content,
            refusal=delta.refusal,
            tool_calls=(
                self._format_tool_calls_chunk(delta.tool_calls)
                if delta.tool_calls
                else None
            ),
            finish_reason=finish_reason,
            reasoning=reasoning,
        )

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
            **self._prepare_tool_params(tools, model_config),
            **self._prepare_generic_config(config=model_config),
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
                **self._prepare_tool_params(tools, model_config),
                **self._prepare_generic_config(config=model_config),
            )
            async for chunk in response:
                yield self._format_completion_chunk(chunk)

        return _generator()
