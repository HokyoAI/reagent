from abc import ABC, abstractmethod
from typing import AsyncGenerator, AsyncIterable, ClassVar, Dict, List, Literal, Type

from pydantic import BaseModel

from ..taskable import Taskable
from ..tool import Tool
from .messages import (
    Completion,
    CompletionChunk,
    Message,
    MessageList,
    aggregate_completion_chunk_aiterable,
)

__llm_provider_registry: Dict[str, Type["LlmProvider"]] = {}


def llm_provider_factory(provider_name: str, **kwargs) -> "LlmProvider":
    """
    Factory method to create a model provider instance.

    Args:
        provider_name (str): Name of the provider to create.
        **kwargs: Configuration parameters for the provider.

    Returns:
        ModelProvider: An instance of the requested provider.

    Raises:
        ValueError: If the provider name is not registered.
    """
    provider_cls = __llm_provider_registry.get(provider_name)
    if provider_cls is None:
        raise ValueError(f"Unknown provider '{provider_name}'. ")
    return provider_cls(**kwargs)


class ToolConfig(BaseModel):
    tool_choice: Literal["auto", "none", "required"] = "auto"
    parallel_tool_calls: bool = False


class GenericConfig(BaseModel):
    model: str
    temperature: float


class LlmConfig(BaseModel):
    generic: GenericConfig
    tool: ToolConfig


# Convenience factory function
def create_llm_config(
    model: str,
    temperature: float = 0,
    tool_choice: Literal["auto", "none", "required"] = "auto",
    parallel_tool_calls: bool = False,
) -> LlmConfig:
    """Create a LlmConfig with sensible defaults."""
    return LlmConfig(
        generic=GenericConfig(
            model=model,
            temperature=temperature,
        ),
        tool=ToolConfig(
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
        ),
    )


class LlmProvider(ABC):
    """
    Abstract base class defining the interface for AI model providers.

    This class serves as a template for implementing different model providers
    like OpenAI, Anthropic, etc. It defines the required methods that all
    model providers must implement.
    """

    provider_name: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        """Register provider classes when they are defined."""
        super().__init_subclass__(**kwargs)
        if not cls.provider_name:
            cls.provider_name = cls.__name__.lower()
        __llm_provider_registry[cls.provider_name] = cls

    @abstractmethod
    async def complete(
        self,
        *,
        config: LlmConfig,
        messages: List[Message],
        tools: List[Tool],
    ) -> Completion:
        """
        Performs an asynchronous completion request to the model.

        Args:
            model_config (LlmConfig): The model configuration to be used for the completion.
            messages (List[Message]): The input message to send to the model.
            tools (List[Tool]): The tools available to the model.

        Returns:
            Completion: The model's response.
        """
        pass

    @abstractmethod
    async def stream(
        self,
        *,
        config: LlmConfig,
        messages: List[Message],
        tools: List[Tool],
    ) -> AsyncGenerator[CompletionChunk, None]:
        """
        Performs an asynchronous streaming completion request to the model.

        Args:
            model_config (ModelConfig): The model configuration to be used for the completion.
            messages (List[Message]): The input message to send to the model.
            tools (List[Tool]): The tools available to the model.

        Returns:
            AsyncGenerator[CompletionChunk, None]: An async generator that yields response chunks.
        """
        pass


class ModelCall(MessageList):
    tools: List[Tool]


class Llm(BaseModel):
    provider_name: str
    config: LlmConfig

    def __post_init__(self):
        self.provider = llm_provider_factory(self.provider_name)

    async def stream(self, input: ModelCall) -> AsyncGenerator[CompletionChunk, None]:
        generator = await self.provider.stream(
            config=self.config, messages=input.messages, tools=input.tools
        )
        return generator

    async def complete(self, input: ModelCall) -> Completion:
        return await self.provider.complete(
            config=self.config, messages=input.messages, tools=input.tools
        )

    async def aggregate(self, chunks: AsyncIterable[CompletionChunk]) -> Completion:
        return await aggregate_completion_chunk_aiterable(chunks)
