from typing import Literal

from pydantic import BaseModel


class ToolConfig(BaseModel):
    tool_choice: Literal["auto", "none", "required"] = "auto"
    parallel_tool_calls: bool = False


class GenericConfig(BaseModel):
    model: str
    temperature: float


class ModelConfig(BaseModel):
    generic: GenericConfig
    tool: ToolConfig


# Convenience factory function
def create_config(
    model: str,
    temperature: float = 0.7,
    tool_choice: Literal["auto", "none", "required"] = "auto",
    parallel_tool_calls: bool = False,
) -> ModelConfig:
    """Create a ModelConfig with sensible defaults."""
    return ModelConfig(
        generic=GenericConfig(
            model=model,
            temperature=temperature,
        ),
        tool=ToolConfig(
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
        ),
    )
