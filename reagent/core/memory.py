from abc import ABC, abstractmethod
from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel


class Memory(BaseModel):
    pass


class MemoryStore(BaseModel, ABC):
    """
    Memory is append only. Earlier memories can be marked as invalid, but never removed.
    This allows memory to be used for auditing, and also preserves more information.
    The info that something is incorrect is equally important as the correct info.
    Revisions can be used to update previous memories, but the original memory is still kept.
    Auto-revisioning memory only uses the store method, and detects when a stored piece of data should be used to revise a previous memory.
    Zep is an example of auto-revisioning memory where new information is tested against the knowledge graph.
    Redacted memories are not used in any future operations, but are kept for auditing purposes.
    Redaction can be used when data is more harmful than helpful.

    All memory has a scope, either generic, agent, thread, or task specific.
    Task specific memories are for one whole completion of a task, and cannot be accessed otherwise (like the task ledger).
    Thread specific memories carry across different task completions in the same thread (like conversation history).
    Agent specific memories are for that agent only (like lessons learned).
    Generic memories can be used across agents or even servers (like RAG documents).

    All memory has a namespace, which is used to separate memory on a higher security level.
    Namespaces can be used to separate memory for different users, or different organizations.
    """

    scope: ClassVar[Literal["generic", "agent", "thread", "task"]]
    auto_revision: ClassVar[bool]
    default_namesapce: str = "default"

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the database connection and setup.

        This method should be called before any other methods are used.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the database connection and release resources.

        This method should be called when the store is no longer needed.
        """
        pass

    @abstractmethod
    def save(
        self,
        *,
        info: BaseModel,
        namespace: Optional[str],
        metadata: Optional[BaseModel] = None,
    ) -> str:
        """Store data in memory and return a unique identifier."""
        pass

    @abstractmethod
    def revise(
        self,
        *,
        namespace: Optional[str],
        identifier: str,
        revision: str,
    ) -> None:
        """Add a revision to memory that updates, clarifies, or corrects the original data."""
        pass

    @abstractmethod
    def redact(
        self,
        *,
        namespace: Optional[str],
        identifier: str,
        reason: str,
    ) -> None:
        """Mark data in memory as invalid."""
        pass

    @abstractmethod
    def retrieve(
        self,
        *,
        namespace: Optional[str],
        identifier: str,
    ) -> BaseModel:
        """Retrieve data from memory using its identifier."""
        pass

    @abstractmethod
    def search(
        self,
        *,
        namespace: Optional[str],
        query: str,
        limit: Optional[int] = None,
    ) -> List[BaseModel]:
        """Search memory for relevant data based on query."""
        pass
