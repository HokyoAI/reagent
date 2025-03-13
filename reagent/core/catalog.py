import asyncio
import logging
from enum import StrEnum
from typing import Annotated, Awaitable, Callable, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from hatchet_sdk import Hatchet
from pydantic import ValidationError
from sse_starlette import EventSourceResponse

from reagent.core.taskable import Taskable
from reagent.core.types import Labels

logger = logging.getLogger(__name__)


class Catalog:

    def __init__(self):
        self.finalized: bool = False
        self._taskable_registry: dict[str, type[Taskable]] = {}

    def add_taskable(self, *, taskable: type[Taskable]):
        if self.finalized:
            raise RuntimeError("Catalog is finalized, cannot add more taskables")
        if taskable.guid in self._taskable_registry:
            raise ValueError(f"Integration {taskable.guid} already exists")

        self._taskable_registry[taskable.guid] = taskable

    def finalize(self):
        if self.finalized:
            raise RuntimeError("Catalog is already finalized")
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
        taskable = self._taskable_registry[guid]

        async def execute_taskable(input: taskable.input_model, stream: bool = False):  # type: ignore
            result = await taskable()(input, stream=stream)
            if stream:
                return EventSourceResponse(result)
            else:
                return result

        return execute_taskable

    def _build_taskable_router(self):
        router = APIRouter()

        for guid in self._taskable_registry:
            router.post("/" + guid)(self._build_execute_taskable_handler(guid))

        return router
