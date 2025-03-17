import logging
from asyncio import sleep
from contextlib import asynccontextmanager
from typing import AsyncIterable, ClassVar

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from reagent.core.catalog import Catalog
from reagent.core.dependencies.engine import close_engine, init_engine
from reagent.core.tool import tool
from tests.catalog import catalog

logger = logging.getLogger(__name__)

worker = catalog.worker()

if __name__ == "__main__":
    worker.start()
