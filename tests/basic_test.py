import pytest
from dotenv import load_dotenv

from reagent.messages import Message
from reagent.model_providers import ModelConfig
from reagent.providers.openai import Groq


@pytest.fixture
def settings():
    load_dotenv(override=True)
    from reagent.settings import Settings

    return Settings()  # pyright: ignore


@pytest.fixture
def groq(settings):
    return Groq(
        api_key=settings.api_key,
    )


@pytest.mark.asyncio
async def test_stream(groq):

    generator = await groq.stream(
        model_config=ModelConfig(model="deepseek-r1-distill-llama-70b", temperature=0),
        messages=[
            {
                "role": "system",
                "content": "Be brief",
            },
            {"role": "user", "content": "Say Hello"},
        ],
        tools=[],
    )
    async for chunk in generator:
        print(chunk)
        print()


@pytest.mark.asyncio
async def test_complete(groq):

    completion = await groq.complete(
        model_config=ModelConfig(model="deepseek-r1-distill-llama-70b", temperature=0),
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that can answer basic questions. Anything too complicated should be refused.",
            },
            {"role": "user", "content": "explain quantum physics to me please."},
        ],
        tools=[],
    )
    print(completion)
