from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel

from .messages import Message
from .model_providers import ModelConfig, ModelProvider
from .tools import EndControl, Tool, create_tool


class AgentInput(BaseModel):
    message: str


class AgentState(BaseModel):
    message: str


class AgentOutput(BaseModel):
    message: str


@dataclass
class Agent:
    guid: str
    name: str
    description: str
    provider: ModelProvider
    model_config: ModelConfig
    input_model: type[AgentInput]
    output_model: type[AgentOutput]
    tools: List[Tool]
    delegates: List["Agent"]
    state_model: Optional[type[AgentState]] = None

    def __post_init__(self):
        self.model_config.tool.tool_choice = (
            "required"  # override tool choice to required
        )
        self.agent_response_tool = create_tool(
            guid=self.guid + "_respond",
            name="respond",
            input_model=self.output_model,
            output_model=EndControl(),
        )
        self.delegate_tools = [delegate._to_tool() for delegate in self.delegates]
        self.all_tools: List[Tool] = (
            self.tools + self.delegate_tools + [self.agent_response_tool]
        )
        self.tool_mapping = {}
        for tool in self.all_tools:
            if tool.name in self.tool_mapping:
                raise ValueError(
                    f"Tool with name {tool.name} already exists in agent {self.name}"
                )
            self.tool_mapping[tool.name] = tool.guid

    def _to_tool(self) -> Tool:
        return create_tool(
            guid=self.guid,
            name=self.name,
            description=self.description,
            input_model=self.input_model,
            output_model=self.output_model,
            forward=self.stream,
        )

    async def complete(self, messages: List[Message]):
        response = await self.provider.complete(
            model_config=self.model_config, messages=messages, tools=self.all_tools
        )

    async def stream(self, messages: List[Message]):
        return await self.provider.stream(
            model_config=self.model_config, messages=messages, tools=self.all_tools
        )
