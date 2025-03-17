import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reagent.core.dependencies.engine import close_engine, init_engine
from tests.catalog import catalog

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


async def http_authenticate():
    return None


app.include_router(catalog.router(http_authenticate=http_authenticate))


def main(host: str, port: int):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main("0.0.0.0", 8000)
