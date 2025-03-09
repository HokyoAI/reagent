from pydantic import BaseModel

from reagent.core.memory import StateStore


class LocalStateStore(StateStore):

    def __init__(self):
        self.store = {}

    async def update_node_state(self, graph_id: str, node_guid: str, state: BaseModel):
        if graph_id not in self.store:
            self.store[graph_id] = {}

        if node_guid not in self.store[graph_id]:
            self.store[graph_id][node_guid] = {}

        self.store[graph_id][node_guid] = state.model_dump()

    async def get_node_state(self, graph_id: str, node_guid: str) -> BaseModel:
        if graph_id not in self.store:
            raise ValueError(f"Graph with id {graph_id} does not exist")

        if node_guid not in self.store[graph_id]:
            raise ValueError(
                f"Node with guid {node_guid} does not exist in graph {graph_id}"
            )

        return self.store[graph_id][node_guid]
