from typing import List

from pydantic import BaseModel

from .messages import Message
from .model_providers import ModelConfig, ModelProvider
from .tools import RespondTool, Tool


class AgentInput(BaseModel):
    message: str


class AgentOutput(BaseModel):
    message: str


class Agent:
    def _to_tool(self) -> Tool:
        return Tool()

    def __init__(
        self,
        *,
        provider: ModelProvider,
        model_config: ModelConfig,
        input_model: type[AgentInput],
        output_model: type[AgentOutput],
        tools: List[Tool],
        delegates: List["Agent"]
    ):

        self.provider = provider
        self.model_config = model_config
        self.model_config.tool_choice = "required"  # override tool choice to required

        self.input_model = input_model
        self.output_model = output_model

        self.provided_tools = tools
        self.delegates = delegates
        self.delegate_tools = [delegate._to_tool() for delegate in self.delegates]
        self.all_tools: List[Tool] = list(
            set(self.provided_tools) | set(self.delegate_tools) | set([RespondTool()])
        )

    async def complete(self, messages: List[Message]):
        return await self.provider.complete(
            model_config=self.model_config, messages=messages, tools=self.all_tools
        )

    async def stream(self, messages: List[Message]):
        return await self.provider.stream(
            model_config=self.model_config, messages=messages, tools=self.all_tools
        )
