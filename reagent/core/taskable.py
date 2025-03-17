from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, TypedDict

from hatchet_sdk import Context
from hatchet_sdk.hatchet import Hatchet, step, workflow
from hatchet_sdk.workflow import WorkflowMeta
from pydantic import BaseModel, ConfigDict


class FnDict(TypedDict):
    original_fn: Callable
    execute_fn: Callable
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    workflow: Optional[WorkflowMeta]


class TaskableFnRegistry:
    _instance = None
    _registry: Dict[str, FnDict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(
        self,
        guid: str,
        fn: Callable,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
    ):
        """Register a function with the registry"""
        self._registry[guid] = {
            "input_model": input_model,
            "output_model": output_model,
            "original_fn": fn,
            "execute_fn": fn,
            "workflow": None,
        }

    def get(self, guid: str):
        return self._registry[guid]["execute_fn"]

    def convert(
        self,
        hatchet: Hatchet,
        fn: Callable[[BaseModel], Awaitable[BaseModel]],
        input_model: type[BaseModel],
        output_model: type[BaseModel],
    ) -> tuple[Callable[[BaseModel], Awaitable[BaseModel]], WorkflowMeta]:

        async def step_fn(
            self, ctx: Context
        ):  # needs self argument to be part of the workflow class
            input = input_model(**ctx.input)
            output = await fn(input)
            return output.model_dump()

        workflow_step = step("begin")(step_fn)
        workflow_name = f"{fn.__name__}_workflow"
        workflow_class = type(workflow_name, (), {workflow_name: workflow_step})
        workflow_ref = workflow()(workflow_class)

        @wraps(fn)
        async def execute_fn(input: BaseModel) -> BaseModel:
            # aio hatchet causes asyncio loop issues TODO: fix
            workflow_run = hatchet.admin.run_workflow(workflow_name, input.model_dump())
            result = await workflow_run.result()
            return output_model(
                **result["begin"]
            )  # hatchet returns a dict with the step name as key

        return execute_fn, workflow_ref


# Create the singleton instance
taskable_registry = TaskableFnRegistry()


class Taskable[_I: BaseModel, _O: BaseModel](BaseModel):
    """
    Maybe rate limits go here?
    A protocol that defines the interface for a Taskable.

    Taskables at the very least need to define a run method. The run method returns an async generator.
    Depending on how the taskable works this run method may take several forms.
    Aggregating the stream and completion should always end up with the same result.

    No streaming: Fill out complete and use default_stream and default_aggregate
        _CO = _AO
        Example: Basic HTTP calls
    Streaming native: Fill out stream and aggregate and use default_complete
        Example: Streaming HTTP calls
    Different streaming and complete behavior: Override all three methods.
        Use this when completion can be more efficient than streaming and aggregating.
        Example: Chat completions

    """

    guid: str
    fn: Callable[[_I], Awaitable[_O]]
    input_model: type[_I]
    output_model: type[_O]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def model_post_init(self, __context):
        result = super().model_post_init(__context)
        self._fn = self.fn
        return result

    @property
    def _fn(self) -> Callable[[_I], Awaitable[_O]]:
        # Always retrieve the current version from registry
        return taskable_registry.get(self.guid)

    @_fn.setter
    def _fn(self, function: Callable[[_I], Awaitable[_O]]):
        # Store the function and make it available in the registry
        taskable_registry.register(
            self.guid, function, self.input_model, self.output_model
        )

    async def __call__(self, input: _I) -> _O:
        return await self._fn(input)

    # input_model: type[_I]
    # chunk_output_model: type[_CO]
    # aggregate_output_model: type[_AO]

    # def __init_subclass__(cls):
    #     result = super().__init_subclass__()
    #     if hasattr(cls, "guid"):
    #         if cls.guid in taskable_registry:
    #             raise ValueError(f"Taskable with guid {cls.guid} already exists")
    #         taskable_registry[cls.guid] = cls
    #     return result

    # async def __call__(
    #     self, input: _I, stream: bool = False
    # ) -> Union[AsyncGenerator[_CO, None], _AO]:
    #     """
    #     Process the input and return the final output.

    #     Args:
    #         input: A Pydantic BaseModel containing the input data
    #         stream: Whether to stream the response
    #     """
    #     if stream:
    #         return await self.stream(input)
    #     else:
    #         return await self.complete(input)

    # @abstractmethod
    # async def stream(self, input: _I) -> AsyncGenerator[_CO, None]:
    #     """
    #     Process the input and yield chunks as an async generator.

    #     Args:
    #         input: A Pydantic BaseModel containing the input data

    #     Returns:
    #         An async generator that yields chunks of type ChunkT
    #     """
    #     ...

    # @abstractmethod
    # async def aggregate(self, chunks: AsyncIterable[_CO]) -> _AO:
    #     """
    #     Aggregate chunks produced by the stream method into a complete response.

    #     Args:
    #         chunks: A list of chunks produced by the stream method

    #     Returns:
    #         A complete response as a Pydantic BaseModel
    #     """
    #     ...

    # @abstractmethod
    # async def complete(self, input: _I) -> _AO:
    #     """
    #     Process the input directly and return the final output without streaming.
    #     This is a convenience method that internally uses stream and aggregate
    #     when not overridden with a more efficient implementation.

    #     Args:
    #         input: A Pydantic BaseModel containing the input data

    #     Returns:
    #         A complete response as a Pydantic BaseModel
    #     """
    #     ...


# async def default_stream[_I: AM, _AO: AM](
#     self: Taskable[_I, _AO, _AO], input: _I
# ) -> AsyncGenerator[_AO, None]:
#     async def gen():
#         result = await self.complete(input)
#         yield result

#     return gen()


# async def default_aggregate[_I: AM, _AO: AM](
#     self: Taskable[_I, _AO, _AO], chunks: list[_AO]
# ) -> _AO:
#     return chunks[0]


# async def default_complete[_I: AM, _CO: AM, _AO: AM](
#     self: Taskable[_I, _CO, _AO], input: _I
# ) -> _AO:
#     gen = await self.stream(input)
#     return await self.aggregate(gen)
