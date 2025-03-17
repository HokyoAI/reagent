import asyncio
import logging
from enum import StrEnum
from typing import Annotated, Awaitable, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from hatchet_sdk import Hatchet
from pydantic import BaseModel, ValidationError
from sse_starlette import EventSourceResponse

from reagent.core.dependencies.registry import get_taskable_registry
from reagent.core.taskable import Taskable
from reagent.core.types import Labels

logger = logging.getLogger(__name__)


class TestInput(BaseModel):
    multiplier: int


class IntChunk(BaseModel):
    chunk: int


class IntSum(BaseModel):
    aggregate: int


class Catalog:

    def __init__(self, hatchet: Optional[Hatchet] = None):
        self.hatchet = hatchet
        self.finalized: bool = False
        self._taskable_catalog: dict[str, Taskable] = {}

    def add_taskable(self, *, taskable: Taskable):
        if self.finalized:
            raise RuntimeError("Catalog is finalized, cannot add more taskables")
        if taskable.guid in self._taskable_catalog:
            raise ValueError(f"Integration {taskable.guid} already exists")

        self._taskable_catalog[taskable.guid] = taskable

    def finalize(self):
        if self.finalized:
            raise RuntimeError("Catalog is already finalized")
        if self.hatchet is not None:
            registry = get_taskable_registry()
            for guid in registry._registry:
                new_fn, workflow_ref = registry.convert(
                    self.hatchet,
                    fn=registry._registry[guid]["original_fn"],
                    input_model=registry._registry[guid]["input_model"],
                    output_model=registry._registry[guid]["output_model"],
                )
                registry._registry[guid]["execute_fn"] = new_fn
                registry._registry[guid]["workflow"] = workflow_ref
        self.finalized = True

    def router(
        self,
        *,
        http_authenticate: Callable[..., Awaitable[tuple[str, Labels] | None]],
    ) -> APIRouter:
        if not self.finalized:
            raise RuntimeError("Catalog is not finalized, cannot create router")

        # order matters !
        self._http_authenticate = http_authenticate
        self._create_dependency_functions()

        root_router = APIRouter(prefix="/tasks", tags=["tasks"])
        root_router.include_router(self._build_taskable_router())

        return root_router

    def worker(self):
        if not self.finalized:
            raise RuntimeError("Catalog is not finalized, cannot create worker")
        if self.hatchet is None:
            raise RuntimeError("Hatchet is required to create worker")
        worker = self.hatchet.worker("reagent_worker")
        registry = get_taskable_registry()
        for guid in registry._registry:
            workflow = registry._registry[guid]["workflow"]
            if workflow is not None:
                worker.register_workflow(
                    workflow()
                )  # have to instantiate workflow class () otherwise will get generic namespace error
        return worker

    def _create_dependency_functions(self):
        self._require_authentication_dep = (
            self._build_require_authentication_dependency()
        )

    def _build_require_authentication_dependency(self):

        async def require_authentication(
            identity: Annotated[
                tuple[str, Labels] | None, Depends(self._http_authenticate)
            ],
        ):
            if identity is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return identity

        return require_authentication

    def _build_execute_taskable_handler(self, guid: str):
        taskable = self._taskable_catalog[guid]

        async def execute_taskable(input: taskable.input_model, stream: bool = False):  # type: ignore
            result = await taskable(input)
            if stream:
                return EventSourceResponse(result)
            else:
                return result

        return execute_taskable, taskable.output_model

    def _build_taskable_router(self):
        router = APIRouter()

        for guid in self._taskable_catalog:
            handler, output_model = self._build_execute_taskable_handler(guid)
            router.post("/" + guid, response_model=output_model)(handler)

        return router
