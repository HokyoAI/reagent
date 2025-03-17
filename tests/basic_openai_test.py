import pytest
from dotenv import load_dotenv

from reagent.core.llms.messages import SystemMessage, UserMessage, aggregate_iterable
from reagent.llm_providers.openai import OpenAI
from reagent.types.configs import ModelConfig, create_config

from .settings import Settings


@pytest.fixture
def settings():
    load_dotenv(override=True)

    return Settings()  # pyright: ignore


@pytest.fixture
def openai(settings: Settings):
    return OpenAI(
        api_key=settings.openai_key,
    )


@pytest.fixture
def config():
    return create_config(model="gpt-4o", temperature=0)


messages = [
    SystemMessage("Be brief"),
    UserMessage("What is the difference between fat and protein in cooking?"),
]


# @pytest.mark.asyncio
# async def test_stream(openai: OpenAI, config: ModelConfig):

#     generator = await openai.stream(
#         model_config=config,
#         messages=messages,
#         tools=[],
#     )
#     async for chunk in generator:
#         print(chunk)
#         print()


# @pytest.mark.asyncio
# async def test_complete(openai: OpenAI, config: ModelConfig):

#     completion = await openai.complete(
#         model_config=config,
#         messages=messages,
#         tools=[],
#     )
#     print(completion)


# @pytest.mark.asyncio
# async def test_aggregate(openai: OpenAI, config: ModelConfig):

#     generator = await openai.stream(
#         model_config=config,
#         messages=messages,
#         tools=[],
#     )
#     completion = await aggregate_iterable(generator)
#     print(completion)
