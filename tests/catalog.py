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
from reagent.core.dependencies.hatchet import get_hatchet
from reagent.core.tool import tool

logger = logging.getLogger(__name__)


class LocationInput(BaseModel):
    location: str


class WeatherOutput(BaseModel):
    temperature: float
    humidity: float


class LocationOutput(WeatherOutput):
    landmarks: list[str]


@tool()
async def search_weather(input: LocationInput) -> WeatherOutput:
    await sleep(3)
    return WeatherOutput(temperature=72.0, humidity=0.5)


@tool()
async def location_details(input: LocationInput) -> LocationOutput:
    await sleep(2)
    weather = await search_weather(input)
    return LocationOutput(
        temperature=weather.temperature,
        humidity=weather.humidity,
        landmarks=["Statue of Liberty", "Empire State Building"],
    )


hatchet = get_hatchet()
catalog = Catalog(hatchet=hatchet)
catalog.add_taskable(taskable=search_weather)
catalog.add_taskable(taskable=location_details)
catalog.finalize()
