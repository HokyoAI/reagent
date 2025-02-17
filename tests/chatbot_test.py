import pytest
from dotenv import load_dotenv

from reagent.agent import Agent, AgentInput, AgentOutput
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
async def test(groq):
    config = ModelConfig(model="deepseek-r1-distill-llama-70b", temperature=0.2)

    chatbot = Agent(
        provider=groq,
        model_config=config,
        input_model=AgentInput,
        output_model=AgentOutput,
        tools=[],
        delegates=[],
    )
