from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Generic, TypeVar, get_type_hints

from pydantic import BaseModel, ConfigDict

T1 = TypeVar("T1", bound=BaseModel, covariant=True)
T2 = TypeVar("T2", bound=BaseModel, covariant=True)

tool_registry: Dict[str, "Tool[BaseModel, BaseModel]"] = {}


@dataclass
class Tool(Generic[T1, T2]):
    guid: str
    name: str
    description: str
    input_model: type[T1]
    output_model: type[T2]
    forward: Callable[[T1], Awaitable[T2]]
    requires_approval: bool = False

    def __post_init__(self):
        if self.guid in tool_registry:
            raise ValueError(f"Tool with guid {self.guid} already exists")
        else:
            tool_registry[self.guid] = self


def create_tool(
    guid: str,
    name: str,
    description: str,
    input_model: type[T1],
    output_model: type[T2],
    forward: Callable[[T1], Awaitable[T2]],
    requires_approval: bool = False,
) -> Tool[T1, T2]:
    return Tool[T1, T2](
        guid, name, description, input_model, output_model, forward, requires_approval
    )


def tool(
    guid: str, func: Callable[[T1], Awaitable[T2]], requires_approval=False
) -> Tool[T1, T2]:
    """
    Decorator that constructs a Tool from the given function.
    The tool name is the function name (lowercased),
    the description is the docstring,
    the input_model is the single argument type,
    and the output_model is the return type.
    """
    hints = get_type_hints(func)
    name = func.__name__.lower()
    description = (func.__doc__ or "").strip()

    # Pick the first parameter that isn't 'return'
    param = next(k for k in hints if k != "return")
    input_model = hints[param]
    output_model = hints["return"]

    return Tool(
        guid=guid,
        name=name,
        description=description,
        input_model=input_model,
        output_model=output_model,
        forward=func,
        requires_approval=requires_approval,
    )


async def execute_tool(guid: str, arguments: str) -> BaseModel:
    tool = tool_registry.get(guid)
    if tool is None:
        raise ValueError(f"Tool with guid {guid} not found")
    input = tool.input_model.model_validate_json(arguments)
    output = await tool.forward(input)
    return output


class EndControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
