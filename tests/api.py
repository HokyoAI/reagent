import logging
from contextlib import asynccontextmanager
from typing import AsyncIterable, ClassVar

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reagent.core.catalog import Catalog
from reagent.core.dependencies.engine import close_engine, init_engine
from reagent.core.taskable import (
    Taskable,
    default_aggregate,
    default_complete,
    default_stream,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_engine()
        yield
    finally:
        await close_engine()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from pydantic import BaseModel


class TestInput(BaseModel):
    test: str


class IntChunk(BaseModel):
    chunk: int


class IntSum(BaseModel):
    aggregate: int


class StreamingNativeTaskable(Taskable):
    guid = "test"
    description = "Test Taskable"
    input_model = TestInput
    chunk_output_model = IntChunk
    aggregate_output_model = IntSum

    async def stream(self, input: TestInput):
        async def generator():
            for i in range(10):
                yield IntChunk(chunk=i)

        return generator()

    async def aggregate(self, chunks: AsyncIterable[IntChunk]):
        result = 0
        async for chunk in chunks:
            result += chunk.chunk
        return IntSum(aggregate=result)


StreamingNativeTaskable.complete = default_complete


catalog = Catalog()
catalog.add_taskable(taskable=StreamingNativeTaskable)
catalog.finalize()


async def http_authenticate():
    return None


app.include_router(catalog.router(http_authenticate=http_authenticate))


def main(host: str, port: int):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main("0.0.0.0", 8000)
