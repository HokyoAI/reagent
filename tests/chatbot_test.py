import pytest
from dotenv import load_dotenv

from reagent.core.agent.agent import Agent, AgentInput, AgentOutput
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


@pytest.mark.asyncio
async def test(groq: Groq, config: ModelConfig):

    chatbot = Agent(
        provider=groq,
        model_config=config,
        input_model=AgentInput,
        output_model=AgentOutput,
        tools=[],
        delegates=[],
    )
