import ast
import asyncio
import inspect
import json
import textwrap
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    ParamSpec,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import astor
from fast_depends import Depends, inject
from hatchet_sdk import Hatchet
from hatchet_sdk.hatchet import step, workflow
from hatchet_sdk.workflow import WorkflowMeta
from pydantic import BaseModel


class BasicModel(BaseModel):
    name: str
    age: int
    active: bool


class Input(BaseModel):
    message: str


class Output(BaseModel):
    response: str


def get_configs():
    return BasicModel(name="Default", age=25, active=True)


@inject
async def fn(
    blah: int, input: Input, configs: BasicModel = Depends(get_configs)
) -> Output:
    # Simulate some processing based on the input and configs
    print(blah)
    response = f"Hello {input.message}, your config is {configs.name} with age {configs.age} and active status {configs.active}."
    return Output(response=response)


from functools import partial

if __name__ == "__main__":
    # Generate the function using the BasicModel configuration
    # This is similar to how you would use the `tool` decorator in your original code
    # but here we are just generating a function directly for demonstration.
    func = partial(fn, 2)

    # Get the signature of the original function
    sig = inspect.signature(func.func)
    parameters = list(sig.parameters.values())

    # Get the source code of the function
    source = inspect.getsource(func.func)
    # Dedent the source code to fix indentation issues
    # ast will not parse correctly if the source is not dedented
    source = textwrap.dedent(source)
    tree = ast.parse(source)

    print(astor.to_source(tree))
