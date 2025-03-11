import ast
import asyncio
import inspect
import textwrap
from functools import wraps
from typing import Awaitable, Callable, List, ParamSpec, Protocol, Tuple, TypeVar

from hatchet_sdk import Hatchet
from hatchet_sdk.workflow import WorkflowMeta
from pydantic import BaseModel

_P = ParamSpec("_P")
_R = TypeVar("_R", covariant=True)


def checkpoint(*args, name: str, **kwargs):
    pass


def fht(hatchet: Hatchet, checkpoint_symbol="checkpoint"):
    """
    Transforms a function into a class with separate executable methods for each step,
    splitting at each occurrence of the checkpoint_symbol.

    Args:
        hatchet: The hatchet instance to use
        checkpoint_symbol: The symbol/function call to split on (default: 'checkpoint')

    Returns:
        decorator: The decorator function
    """

    def decorator(
        func: Callable[_P, Awaitable[_R]],
    ) -> Callable[_P, Awaitable[_R]]:
        # Get function attributes
        func_name = func.__name__
        class_name = func_name.title()
        is_async = asyncio.iscoroutinefunction(func)
        if not is_async:
            raise ValueError("Function must be async")
        func_globals = func.__globals__  # not sure if this is needed yet

        # Get the source code of the function
        source = inspect.getsource(func)

        # Dedent the source code to fix indentation issues
        # ast will not parse correctly if the source is not dedented
        source = textwrap.dedent(source)

        tree = ast.parse(source)

        func_defn = None

        for stmt in tree.body:
            if func_defn is None and isinstance(stmt, ast.AsyncFunctionDef):
                func_defn = stmt
                break

        if not func_defn:
            raise ValueError("could not identify function definition")

        func_body = func_defn.body

        # Split the function body into steps based on checkpoint occurrences
        steps: List[Tuple[str, List[ast.stmt | ast.Expr]]] = []
        step_name: str = "begin"
        current_step: List[ast.stmt | ast.Expr] = []

        for stmt in func_body:
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == checkpoint_symbol
            ):  # check for checkpoint call
                if not current_step:
                    continue  # ignore checkpoints with no filling

                # Check if the checkpoint has an argument
                if hasattr(stmt.value, "args") and stmt.value.args:
                    checkpoint_arg = stmt.value.args[0]
                    # Create a return statement for this value
                    current_step.append(ast.Return(value=checkpoint_arg))

                steps.append((step_name, current_step))
                current_step = []

                # Get name keyword argument if it exists for next step_name
                next_step_name = None
                if hasattr(stmt.value, "keywords"):
                    for keyword in stmt.value.keywords:
                        if keyword.arg == "name" and isinstance(
                            keyword.value, ast.Constant
                        ):
                            next_step_name = keyword.value.value
                if next_step_name is None:
                    next_step_name = "step_" + str(len(steps) + 1)
                step_name = next_step_name

            else:
                current_step.append(stmt)
        # Add the last step with any remaining statements
        if current_step:
            steps.append((step_name, current_step))

        # build the workflow class
        class_dict = {}

        for step_name, step_body in steps:
            """
            in every step, raise errors will be converted into return statements.
            these return statements end the workflow with an error.
            this should return workflow_done = True in the context along with the error message.
            all other errors that occur in a step are upto hatchet to handle and retry.

            all explicit return statements end the workflow.
            in any step except for the last one this means we need to set the workflow_done flag in context.

            all steps need to respect the workflow_done flag in context.
            if the flag is set, the step should return immediately.
            """

            # Create a module to contain the step function
            module = ast.Module(body=[], type_ignores=[])

            func_def = ast.AsyncFunctionDef(
                name=step_name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self", annotation=None)] + func_defn.args.args,
                    kwonlyargs=func_defn.args.kwonlyargs,
                    kw_defaults=func_defn.args.kw_defaults,
                    defaults=func_defn.args.defaults,
                    vararg=func_defn.args.vararg,
                    kwarg=func_defn.args.kwarg,
                ),
                body=[],
                decorator_list=[],
                returns=None,
                type_comment=None,
                type_params=[],
            )

        WorkflowClass = type(class_name, (), class_dict)

        workflow_ref = hatchet.workflow(class_name)(WorkflowClass)

        # build the wrapper function that runs the workflow instead
        @wraps(func)
        async def new_func(*args, **kwargs):
            # TODO need to do some arg packaging here
            workflow_run = await hatchet.admin.aio.run_workflow(
                class_name,
                input=kwargs,
            )
            return await workflow_run.result()

        new_func.workflow_ref = workflow_ref  # type: ignore cannot figure out how to type this

        return new_func

    return decorator
