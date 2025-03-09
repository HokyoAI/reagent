import pytest
from dotenv import load_dotenv

from reagent.core.messages import SystemMessage, UserMessage, aggregate_iterable
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


messages = [
    SystemMessage("Be brief"),
    UserMessage("What is the difference between fat and protein in cooking?"),
]


@pytest.mark.asyncio
async def test_stream(groq: Groq, config: ModelConfig):

    generator = await groq.stream(
        model_config=config,
        messages=messages,
        tools=[],
    )
    async for chunk in generator:
        print(chunk)
        print()


@pytest.mark.asyncio
async def test_complete(groq: Groq, config: ModelConfig):

    completion = await groq.complete(
        model_config=config,
        messages=messages,
        tools=[],
    )
    print(completion)


@pytest.mark.asyncio
async def test_aggregate(groq: Groq, config: ModelConfig):

    generator = await groq.stream(
        model_config=config,
        messages=messages,
        tools=[],
    )
    completion = await aggregate_iterable(generator)
    print(completion)
