import inspect
from typing import Awaitable, Callable, Optional, cast

from pydantic import BaseModel

from reagent.core.taskable import Taskable


class Tool[_I: BaseModel, _O: BaseModel](Taskable[_I, _O]):
    requires_approval: bool


def tool(guid: Optional[str] = None, requires_approval=False):
    """
    If not provided the tool guid is the function name lowercased,
    The description is the docstring,
    The input_model is the single argument type,
    The output_model is the return type.
    """

    def decorator[_I: BaseModel, _O: BaseModel](
        fn: Callable[[_I], Awaitable[_O]],
    ) -> Tool[_I, _O]:

        signature = inspect.signature(fn)

        parameters = list(signature.parameters.values())
        if len(parameters) != 1:
            raise ValueError("Tool functions must have exactly one parameter")
        param = parameters[0]
        input_model = param.annotation
        if not issubclass(input_model, BaseModel):
            raise ValueError("Tool input must be a Pydantic BaseModel")
        output_model = signature.return_annotation
        if not issubclass(output_model, BaseModel):
            raise ValueError("Tool output must be a Pydantic BaseModel")

        input_model = cast(type[_I], input_model)
        output_model = cast(type[_O], output_model)

        fn_doc = fn.__doc__ or ""
        description = fn_doc.strip()
        tool = Tool[_I, _O](
            guid=guid if guid is not None else fn.__name__.lower(),
            function=fn,
            description=description,
            input_model=input_model,
            output_model=output_model,
            requires_approval=requires_approval,
        )

        return tool

    return decorator
