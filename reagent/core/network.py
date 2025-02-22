from dataclasses import dataclass
from typing import AsyncGenerator, Awaitable, Callable, Generic, List, Literal, TypeVar

from pydantic import BaseModel

_I = TypeVar("_I", bound=BaseModel)
_O = TypeVar("_O", bound=BaseModel)
_S = TypeVar("_S", bound=BaseModel)


@dataclass
class BasicNode(Generic[_I, _O, _S]):
    guid: str
    name: str
    description: str
    input_model: _I
    return_model: _O
    state: type[_S]
    initial_state: _S
    complete: Callable[[_I, _S], Awaitable[tuple[_O, _S]]]
    requires_approval: bool = False


type Node = BasicNode[BaseModel, BaseModel, BaseModel]


@dataclass
class Graph:
    adjacency_list: dict[str, List[Node]]
    id: str = 



    def add_node(self, node: Node, next_nodes: List[Node]):
        if node.guid in self.adjacency_list:
            raise ValueError(f"Node with guid {node.guid} already exists")
        self.adjacency_list[node.guid] = next_nodes


class AgentNode(Node):
    pass


class ToolNode(Node):
    pass
