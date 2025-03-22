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

        workflow_step = step("begin")(step_fn)  # hatchet step decorator
        workflow_name = f"{fn.__name__}_workflow"
        workflow_class = type(workflow_name, (), {workflow_name: workflow_step})
        workflow_ref = workflow()(workflow_class)  # hatchet workflow decorator

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
    Taskables are simply functions with some metadata.
    GOTCHA: Functions must be set after instantiation. This is because agents must generate their fn.
    Depending on the context, a taskable may need different code to run with the same signature.
    The registry provides a way for us to achieve that.
    """

    guid: str
    description: str
    input_model: type[_I]
    output_model: type[_O]
    function: Optional[Callable[[_I], Awaitable[_O]]]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def model_post_init(self, __context):
        super().model_post_init(__context)
        if self.function is not None:
            self.fn = self.function  # Set the function if provided during instantiation

    @property
    def fn(self) -> Callable[[_I], Awaitable[_O]]:
        # Always retrieve the current version from registry
        try:
            return taskable_registry.get(self.guid)
        except:
            raise ValueError(
                f"Taskable with guid '{self.guid}' not found in registry. Must assign a function to it before calling."
            )

    @fn.setter
    def fn(self, function: Callable[[_I], Awaitable[_O]]):
        # Store the function and make it available in the registry
        taskable_registry.register(
            self.guid, function, self.input_model, self.output_model
        )

    async def __call__(self, input: _I) -> _O:
        return await self.fn(input)


def checkpoint(*args, checkpoint_name: str):
    pass


async def call_taskable[_I: BaseModel, _O: BaseModel](
    taskable: Taskable[_I, _O], input: _I
) -> _O:
    return await taskable(input)
