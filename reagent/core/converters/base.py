"""
A converter is something that takes a regular function and converts it into a Hatchet Workflow.
Right now, Reagent supports using the library without Hatchet and uses converters to switch when Hatchet is available.
However, in the future it may be desirable to make Hatchet a hard requirement for Reagent.
In that case converters will be used to make the library more developer friendly by supplying tools as familiar functions.
"""

from abc import ABC, abstractmethod


class Converter(ABC):
    """
    Abstract base class for a converter that converts a function into a Hatchet Workflow.
    """

    @abstractmethod
    def convert(self):
        """
        Convert the function into a Hatchet Workflow.
        """
        ...
