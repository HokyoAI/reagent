from typing import Iterable, List, Optional

from pydantic import BaseModel

from ..memory.base import MemoryStore
from ..taskable import Taskable


class Space[T]:
    """
    A wrapper around a set to store objects.
    """

    def __init__(self, elements: Optional[Iterable[T]] = None):
        """
        Initialize a Space with optional elements.

        Args:
            elements: An iterable of elements to add to the Space (default: None)
        """
        self.elements = set(elements or [])

    def __len__(self):
        """
        Return the number of elements in the Space.
        """
        return len(self.elements)

    def add(self, element: T):
        """
        Add an element to the Space.
        """
        self.elements.add(element)

    def remove(self, element: T):
        """
        Remove an element from the Space if it exists.
        """
        if element in self.elements:
            self.elements.remove(element)

    def __contains__(self, element: T):
        """
        Check if an element is in the Space.
        """
        return element in self.elements

    def __add__(self, other: "SpaceDiff[T]") -> "Space[T]":
        """
        Add a SpaceDiff to this Space, returning a new Space.

        Args:
            other: A SpaceDiff object to apply to this Space

        Returns:
            A new Space with the SpaceDiff applied
        """
        if not isinstance(other, SpaceDiff):
            raise TypeError("Can only add a SpaceDiff to a Space")

        # Create a new Space with the same elements
        result = Space(self.elements)

        # Apply the SpaceDiff
        for element, polarity in other.elements.items():
            if polarity > 0:  # Positive polarity: add if not in Space
                if element not in self.elements:
                    result.add(element)
            elif polarity < 0:  # Negative polarity: remove if in Space
                if element in self.elements:
                    result.remove(element)

        return result

    def __sub__(self, other: "Space[T]") -> "SpaceDiff[T]":
        """
        Subtract another Space from this Space, returning a SpaceDiff.

        Args:
            other: Another Space object

        Returns:
            A SpaceDiff representing the difference between the spaces
        """
        if not isinstance(other, Space):
            raise TypeError("Can only subtract a Space from a Space")

        # Create a new SpaceDiff
        diff = SpaceDiff()

        # Elements in self but not in other: add with positive polarity
        for element in self.elements:
            if element not in other.elements:
                diff.add_positive(element)

        # Elements in other but not in self: add with negative polarity
        for element in other.elements:
            if element not in self.elements:
                diff.add_negative(element)

        return diff

    def __repr__(self):
        """
        String representation of the Space.
        """
        return f"Space({self.elements})"


class SpaceDiff[T]:
    """
    A difference set for Space objects, with elements having polarity.
    """

    def __init__(self):
        """
        Initialize an empty SpaceDiff.
        """
        # Store elements as a dict mapping element -> polarity
        self.elements: dict[T, int] = {}

    def __len__(self):
        """
        Return the number of elements in the SpaceDiff.
        """
        return len(self.elements)

    def add(self, element: T, polarity: int = 1):
        """
        Add an element to the SpaceDiff with a specified polarity.

        Args:
            element: The element to add
            polarity: The polarity value (positive or negative)
        """
        # Update polarity if the element already exists
        if element in self.elements:
            self.elements[element] += polarity
            # Remove element if polarity becomes zero
            if self.elements[element] == 0:
                del self.elements[element]
        else:
            # Add new element with specified polarity
            if polarity != 0:
                self.elements[element] = polarity

    def add_positive(self, element: T):
        """
        Add an element with positive polarity.
        """
        self.add(element, 1)

    def add_negative(self, element: T):
        """
        Add an element with negative polarity.
        """
        self.add(element, -1)

    def __repr__(self):
        """
        String representation of the SpaceDiff.
        """
        positives = [e for e, p in self.elements.items() if p > 0]
        negatives = [e for e, p in self.elements.items() if p < 0]
        return f"SpaceDiff(+{positives}, -{negatives})"


ActionSpaceDiff = SpaceDiff[Taskable]


class ActionSpace(Space[Taskable]):

    async def filter(
        self,
        *,
        input: BaseModel,
    ) -> "ActionSpace":
        """
        TODO
        Returns a new ActionSpace with only the tools and agents that can be used for the task
        """
        return self

    async def diff(
        self, *, input: BaseModel, memory_space_diff: "MemorySpaceDiff"
    ) -> ActionSpaceDiff:
        """
        TODO
        Returns a new ActionSpaceDiff with the tools and agents that will be useful given the memory space diff
        """
        return ActionSpaceDiff()


MemorySpaceDiff = SpaceDiff["Memory"]


class MemorySpace(Space["Memory"]):

    @classmethod
    async def populate(
        cls,
        *,
        input: BaseModel,
        action_space: ActionSpace,
        memory_stores: List[MemoryStore],
    ) -> "MemorySpace":
        """
        TODO
        Returns a new MemorySpace with the memories that will be useful given the action space and memory stores
        """
        return cls()

    async def diff(
        self,
        *,
        input: BaseModel,
        action_space_diff: ActionSpaceDiff,
        memory_stores: List[MemoryStore],
    ) -> "MemorySpaceDiff":
        """
        TODO
        Returns a new MemorySpaceDiff with the memories that will be useful given the action space diff
        """
        return MemorySpaceDiff()

    async def store(
        self,
    ):
        pass
