from abc import ABC, abstractmethod

from pydantic import BaseModel


class StateStore(ABC):

    @abstractmethod
    async def update_node_state(
        self, graph_id: str, node_guid: str, state: BaseModel
    ): ...

    @abstractmethod
    async def get_node_state(self, graph_id: str, node_guid: str) -> BaseModel: ...
