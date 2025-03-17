import pytest
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from reagent.core.llms.messages import SystemMessage, UserMessage, aggregate_iterable
from reagent.core.tool import tool
from reagent.llm_providers.groq import Groq
from reagent.types.configs import ModelConfig, create_config

from .settings import Settings


@pytest.fixture
def settings():
    load_dotenv(override=True)

    return Settings()  # pyright: ignore


@pytest.fixture
def groq(settings: Settings):
    return Groq(
        api_key=settings.groq_key,
    )


@pytest.fixture
def config():
    return create_config(model="deepseek-r1-distill-llama-70b", temperature=0)


class WeatherInput(BaseModel):
    location: str = Field(description="The location to get the weather for")
    complement: str = Field(
        description="In order for the tool to work you must pay it a complement about how great it is"
    )


class WeatherOutput(BaseModel):
    weather: str


async def weather(input: WeatherInput) -> WeatherOutput:
    """Get the weather for a location"""
    return WeatherOutput(weather="50 degrees Fahrenheit and partially cloudy")


weather_tool = tool("weather_tool", weather)

messages = [
    SystemMessage(
        "You are a helpful assistant that can answer questions about the weather using the weather tool."
    ),
    UserMessage("what is the weather like in Paris?"),
]


@pytest.mark.asyncio
async def test_tool_stream(groq: Groq, config: ModelConfig):

    generator = await groq.stream(
        model_config=config,
        messages=messages,
        tools=[weather_tool],
    )
    async for chunk in generator:
        print(chunk)
        print()


@pytest.mark.asyncio
async def test_tools_complete(groq: Groq, config: ModelConfig):

    completion = await groq.complete(
        model_config=config,
        messages=messages,
        tools=[weather_tool],
    )
    print(completion)


@pytest.mark.asyncio
async def test_tool_aggregate(groq: Groq, config: ModelConfig):

    generator = await groq.stream(
        model_config=config,
        messages=messages,
        tools=[weather_tool],
    )
    completion = await aggregate_iterable(generator)
    print(completion)
