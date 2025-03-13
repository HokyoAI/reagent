from typing import AsyncIterable, Dict, List, Literal, Optional, TypeVar

from pydantic import BaseModel

_T = TypeVar("_T")


class HasContent(BaseModel):
    content: str


class UserMessage(HasContent):
    role: Literal["user"] = "user"


class AssistantMessage(HasContent):
    role: Literal["assistant"] = "assistant"


class SystemMessage(HasContent):
    role: Literal["system"] = "system"


class ToolMessage(HasContent):
    tool_call_id: str
    role: Literal["tool"] = "tool"


type Message = UserMessage | AssistantMessage | SystemMessage | ToolMessage


class MessageList(BaseModel):
    messages: List[Message]


type FinishReason = Literal["stop", "length", "tool_calls", "content_filter"]


class ToolCall(BaseModel):
    index: int
    id: str
    arguments: str
    name: str


class Completion(BaseModel):
    id: str
    content: Optional[str]
    refusal: Optional[str]
    finish_reason: FinishReason
    reasoning: Optional[str]
    tool_calls: Optional[Dict[int, ToolCall]]


class ToolCallChunk(BaseModel):
    index: int
    id: Optional[str]
    arguments: Optional[str]
    name: Optional[str]


class CompletionChunk(BaseModel):
    id: str
    content: Optional[str]
    refusal: Optional[str]
    finish_reason: Optional[FinishReason]
    reasoning: Optional[str]
    tool_calls: Optional[Dict[int, ToolCallChunk]]


async def aggregate_chunk(
    aggregate: CompletionChunk, addition: CompletionChunk
) -> CompletionChunk:
    """Aggregate two completion chunks into a single chunk."""

    def _aggregate_unique(aggregate: _T | None, addition: _T | None) -> _T | None:
        if aggregate is None:
            return addition
        else:
            if addition != aggregate:
                raise ValueError(
                    f"Multiple of unique value: {aggregate} and {addition} in chunks"
                )
            return aggregate

    def _aggregate_string_property(
        aggregate: str | None, addition: str | None
    ) -> str | None:
        if addition:
            if aggregate is None:
                return addition
            return aggregate + addition
        else:
            return aggregate

    def _aggregate_tool_calls(
        aggregate: Dict[int, ToolCallChunk] | None,
        addition: Dict[int, ToolCallChunk] | None,
    ) -> Dict[int, ToolCallChunk] | None:
        if addition:
            if aggregate is None:
                return addition
            else:
                result: Dict[int, ToolCallChunk] = {}
                for index, chunk in addition.items():
                    if index in aggregate:
                        result[index] = ToolCallChunk(
                            index=index,
                            id=_aggregate_unique(chunk.id, aggregate[index].id),
                            arguments=_aggregate_string_property(
                                chunk.arguments, aggregate[index].arguments
                            ),
                            name=_aggregate_string_property(
                                chunk.name, aggregate[index].name
                            ),  # this could be a unique property instead, if llm guaranteed to send entire name in one chunk
                        )
                    else:
                        result[index] = chunk
                return result
        else:
            return aggregate

    id = _aggregate_unique(aggregate.id, addition.id)
    finish_reason: FinishReason | None = _aggregate_unique(
        aggregate.finish_reason, addition.finish_reason
    )
    content = _aggregate_string_property(aggregate.content, addition.content)
    refusal = _aggregate_string_property(aggregate.refusal, addition.refusal)
    reasoning = _aggregate_string_property(aggregate.reasoning, addition.reasoning)
    tool_calls = _aggregate_tool_calls(aggregate.tool_calls, addition.tool_calls)

    if id is None:
        raise ValueError("Neither chunk had an id")

    return CompletionChunk(
        id=id,
        content=content,
        refusal=refusal,
        finish_reason=finish_reason,
        reasoning=reasoning,
        tool_calls=tool_calls,
    )


async def complete_aggregate(aggregate: CompletionChunk) -> Completion:
    """Validate that a completion chunk is complete and return the overall completion."""

    def _complete_tool_call_chunk(
        chunk: ToolCallChunk,
    ) -> ToolCall:
        if not (
            chunk.id is not None
            and chunk.name is not None
            and chunk.arguments is not None
        ):
            raise ValueError(f"Incomplete tool call chunk: {chunk}")
        return ToolCall(
            index=chunk.index,
            id=chunk.id,
            name=chunk.name,
            arguments=chunk.arguments,
        )

    if not aggregate.id:
        raise ValueError("Complete aggregate has no id")
    if not aggregate.finish_reason:
        raise ValueError("Complete aggregate has no finish reason")
    tool_calls = None
    if aggregate.tool_calls is not None:
        tool_calls = {
            index: _complete_tool_call_chunk(chunk)
            for index, chunk in aggregate.tool_calls.items()
        }

    return Completion(
        id=aggregate.id,
        content=aggregate.content,
        refusal=aggregate.refusal,
        finish_reason=aggregate.finish_reason,
        reasoning=aggregate.reasoning,
        tool_calls=tool_calls,
    )


async def aggregate_completion_chunk_aiterable(
    chunks: AsyncIterable[CompletionChunk],
) -> Completion:
    """Aggregate multiple completion chunks into a single completion."""
    aggregate: CompletionChunk | None = None
    async for chunk in chunks:
        if aggregate is None:
            aggregate = chunk
        else:
            aggregate = await aggregate_chunk(aggregate, chunk)

    if aggregate is None:
        raise ValueError("No chunks to aggregate")
    return await complete_aggregate(aggregate)
