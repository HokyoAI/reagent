from typing import Awaitable, Callable, get_type_hints

from reagent.core.taskable import Taskable


class Tool(Taskable):
    pass


def tool(
    guid: str, func: Callable[[T1], Awaitable[T2]], requires_approval=False
) -> Tool:
    """
    Decorator that constructs a Tool from the given function.
    The tool name is the function name (lowercased),
    the description is the docstring,
    the input_model is the single argument type,
    and the output_model is the return type.
    """
    hints = get_type_hints(func)
    name = func.__name__.lower()
    description = (func.__doc__ or "").strip()

    # Pick the first parameter that isn't 'return'
    param = next(k for k in hints if k != "return")
    input_model = hints[param]
    output_model = hints["return"]

    return Tool(
        guid=guid,
        name=name,
        description=description,
        input_model=input_model,
        output_model=output_model,
        forward=func,
        requires_approval=requires_approval,
    )
