import asyncio
import logging
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Annotated, AsyncGenerator, Awaitable, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from hatchet_sdk import Hatchet
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette import EventSourceResponse

from reagent.core.dependencies.db import db
from reagent.core.dependencies.engine import close_async_engine, init_async_engine
from reagent.core.dependencies.migrator import get_migrator
from reagent.core.dependencies.registry import get_taskable_registry
from reagent.core.errors import NamespaceNotFoundError
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

    def __init__(
        self,
        hatchet: Optional[Hatchet] = None,
        migrate_on_finalize: bool = True,
        auto_create_namespace: bool = True,
    ):
        self.hatchet = hatchet
        self.finalized: bool = False
        self._taskable_catalog: dict[str, Taskable] = {}
        self.migrate_on_finalize = migrate_on_finalize
        self.auto_create_namespace = auto_create_namespace

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
        if self.migrate_on_finalize:
            migrator = get_migrator()
            migrator.migrate()
        self.finalized = True

    def router(
        self,
        *,
        http_authenticate: Callable[..., Awaitable[tuple[str | None, Labels] | None]],
    ):
        if not self.finalized:
            raise RuntimeError("Catalog is not finalized, cannot create router")

        # order matters !
        self._http_authenticate = http_authenticate
        self._create_dependency_functions()

        root_router = APIRouter(prefix="/tasks", tags=["tasks"])
        root_router.include_router(self._build_taskable_router())

        lifespan_func = self._build_lifespan_func()

        return root_router, lifespan_func

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
        self._require_db_dep = self._build_require_db_dependency()

    def _build_require_authentication_dependency(self):

        async def require_authentication(
            identity: Annotated[
                tuple[str | None, Labels] | None, Depends(self._http_authenticate)
            ],
        ):
            if identity is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return identity

        return require_authentication

    def _build_require_db_dependency(self):

        async def require_db(
            identity: Annotated[
                tuple[str | None, Labels], Depends(self._require_authentication_dep)
            ],
        ):
            try:
                async with db(
                    identity=identity,
                    auto_create_namespace=self.auto_create_namespace,
                ) as session:
                    yield session
            except NamespaceNotFoundError:
                raise HTTPException(status_code=404, detail="Resource not found")

        return require_db

    def _build_execute_taskable_handler(self, guid: str):
        taskable = self._taskable_catalog[guid]

        async def execute_taskable(
            input: taskable.input_model,  # type: ignore
            identity: Annotated[
                tuple[str | None, Labels], Depends(self._require_authentication_dep)
            ],
            session: Annotated[AsyncSession, Depends(self._require_db_dep)],
            stream: bool = False,
        ):
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

    def _build_lifespan_func(self):

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await init_async_engine()
            yield
            await close_async_engine()

        return lifespan
