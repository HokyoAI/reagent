from typing import List, Literal, TypedDict


class Message(TypedDict):
    role: Literal["assistant", "user", "system"]
    content: str


class Completion(TypedDict):
    id: str
    choices: List


class CompletionChunk(TypedDict):
    id: str
    choices: List


def aggregate_chunks(chunks: List[CompletionChunk]) -> Completion:  # type: ignore
    pass
