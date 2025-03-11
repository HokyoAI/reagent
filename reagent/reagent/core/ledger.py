from abc import abstractmethod
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    ParamSpec,
    Set,
    TypeVar,
    cast,
)

from pydantic import BaseModel

from .store import Store, StoreModel


class LedgerEntryV1(StoreModel):
    __search_fields__: ClassVar[Set[str]] = set(["task_id", "source", "type"])
    __version__: ClassVar[str] = "1.0"

    task_id: str  # task_id
    source: str  # node guid
    type: str  # the call made
    data: BaseModel


class LedgerModelV1(StoreModel):
    __search_fields__: ClassVar[Set[str]] = set()
    __version__: ClassVar[str] = "1.0"


class LedgerEntryRelV1(StoreModel):
    __search_fields__: ClassVar[Set[str]] = set(["entry_id", "ledger_id"])
    __version__: ClassVar[str] = "1.0"

    entry_id: str
    ledger_id: str
    index: int


class Ledger:

    def __init__(self, *, store: Store, namespace: Optional[str]):
        self.namespace = namespace

    async def add_entry(self, *, entry: LedgerEntryV1) -> None:
        """
        Add an entry to the ledger for a specific task.

        Args:
            task_id: The ID of the task this entry belongs to
            entry_type: Type of the entry (e.g., "plan", "execution", "result")
            data: The data to store in the entry
        """
        pass

    @abstractmethod
    async def stream_entry(
        self, *, entry_type: str, source: str, namespace: Optional[str], data: Any
    ):
        """
        Stream an entry to the ledger for a specific task.

        Allows for ledgers to be show as a UI in real-time.
        """
        pass

    @abstractmethod
    async def get_entries(
        self, *, namespace: Optional[str], entry_type: Optional[str] = None
    ) -> List[TimeStampedEntry]:
        """
        Retrieve entries for a task, optionally filtered by entry type.

        Args:
            task_id: The ID of the task
            entry_type: Optional filter for entry type

        Returns:
            List of entries for the task
        """
        pass

    @abstractmethod
    async def get_latest_entry(
        self, *, namespace: Optional[str], entry_type: Optional[str] = None
    ) -> Optional[TimeStampedEntry]:
        """
        Get the most recent entry for a task, optionally filtered by type.

        Args:
            task_id: The ID of the task
            entry_type: Optional filter for entry type

        Returns:
            The latest entry or None if no entries exist
        """
        pass


_P = ParamSpec("_P")
_R = TypeVar("_R")


def log_to_ledger(func: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
    """
    Decorator that logs function calls to a TaskLedger.
    It adds an entry before execution with the function name and inputs,
    and another entry after execution with the function name + '_finish' and the output.

    The decorated function must take a TaskLedger as a named parameter 'ledger'.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Skip self/cls parameter for logging
        instance: object | type = args[0] if args else None
        source: str | None = None
        if instance:
            source = cast(str | None, instance.__getattr__("guid"))
        if source is None:
            source = func.__class__.__name__
        args_to_log = args[1:] if args else []

        # Extract ledger from kwargs
        ledger = kwargs.get("ledger")
        if ledger is None:
            # Try to find ledger in positional args
            for arg in args_to_log:
                if isinstance(arg, Ledger):
                    ledger = arg
                    break

        namespace = kwargs.get("namespace", None)

        if ledger is None:
            raise ValueError(f"No TaskLedger found in arguments for {func.__name__}")

        # Create input data as a BaseModel
        class InputData(BaseModel):
            function_name: str = func.__name__
            arguments: Dict = {}

        input_model = InputData()

        # Add named arguments
        for k, v in kwargs.items():
            if k != "ledger" and not isinstance(v, Ledger):
                input_model.arguments[k] = v

        # Add positional arguments (excluding ledger and self/cls)
        for i, arg in enumerate(args_to_log):
            if not isinstance(arg, Ledger):
                input_model.arguments[f"arg_{i}"] = arg

        # Log start of execution
        await ledger.add_entry(
            entry_type=func.__name__,
            data=input_model,
            source=source,
            namespace=namespace,
        )

        # Execute the function
        result = await func(*args, **kwargs)
        if not isinstance(result, BaseModel):
            raise ValueError(
                f"Function {func.__name__} must return a BaseModel instance"
            )

        # Log completion with result
        class OutputData(BaseModel):
            function_name: str = func.__name__
            result: Optional[BaseModel]

        output_model = OutputData(result=result)
        await ledger.add_entry(
            entry_type=f"{func.__name__}_complete",
            data=output_model,
            source=source,
            namespace=namespace,
        )

        return result

    return wrapper
