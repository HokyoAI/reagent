from abc import abstractmethod
from typing import (
    AsyncGenerator,
    AsyncIterable,
    Dict,
    Protocol,
    Union,
    runtime_checkable,
)

from reagent.core.types import AM

taskable_registry: Dict[str, "type[Taskable]"] = {}


@runtime_checkable
class Taskable[_I: AM, _CO: AM, _AO: AM](Protocol):
    """
    Maybe rate limits go here?
    A protocol that defines the interface for a Taskable.

    Taskables at the very least need to define a run method. The run method returns an async generator.
    Depending on how the taskable works this run method may take several forms.
    Aggregating the stream and completion should always end up with the same result.

    No streaming: Fill out complete and use default_stream and default_aggregate
        _CO = _AO
        Example: Basic HTTP calls
    Streaming native: Fill out stream and aggregate and use default_complete
        Example: Streaming HTTP calls
    Different streaming and complete behavior: Override all three methods.
        Use this when completion can be more efficient than streaming and aggregating.
        Example: Chat completions

    Alternatively, for higher order taskables, __call__ can be overridden directly.
    """

    guid: str
    description: str
    input_model: type[_I]
    chunk_output_model: type[_CO]
    aggregate_output_model: type[_AO]

    def __init_subclass__(cls):
        result = super().__init_subclass__()
        if hasattr(cls, "guid"):
            if cls.guid in taskable_registry:
                raise ValueError(f"Taskable with guid {cls.guid} already exists")
            taskable_registry[cls.guid] = cls
        return result

    async def __call__(
        self, input: _I, stream: bool = False
    ) -> Union[AsyncGenerator[_CO, None], _AO]:
        """
        Process the input and return the final output.

        Args:
            input: A Pydantic BaseModel containing the input data
            stream: Whether to stream the response
        """
        if stream:
            return await self.stream(input)
        else:
            return await self.complete(input)

    @abstractmethod
    async def stream(self, input: _I) -> AsyncGenerator[_CO, None]:
        """
        Process the input and yield chunks as an async generator.

        Args:
            input: A Pydantic BaseModel containing the input data

        Returns:
            An async generator that yields chunks of type ChunkT
        """
        ...

    @abstractmethod
    async def aggregate(self, chunks: AsyncIterable[_CO]) -> _AO:
        """
        Aggregate chunks produced by the stream method into a complete response.

        Args:
            chunks: A list of chunks produced by the stream method

        Returns:
            A complete response as a Pydantic BaseModel
        """
        ...

    @abstractmethod
    async def complete(self, input: _I) -> _AO:
        """
        Process the input directly and return the final output without streaming.
        This is a convenience method that internally uses stream and aggregate
        when not overridden with a more efficient implementation.

        Args:
            input: A Pydantic BaseModel containing the input data

        Returns:
            A complete response as a Pydantic BaseModel
        """
        ...


async def default_stream[_I: AM, _AO: AM](
    self: Taskable[_I, _AO, _AO], input: _I
) -> AsyncGenerator[_AO, None]:
    async def gen():
        result = await self.complete(input)
        yield result

    return gen()


async def default_aggregate[_I: AM, _AO: AM](
    self: Taskable[_I, _AO, _AO], chunks: list[_AO]
) -> _AO:
    return chunks[0]


async def default_complete[_I: AM, _CO: AM, _AO: AM](
    self: Taskable[_I, _CO, _AO], input: _I
) -> _AO:
    gen = await self.stream(input)
    return await self.aggregate(gen)
