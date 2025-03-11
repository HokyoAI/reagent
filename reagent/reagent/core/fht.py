import ast
import asyncio
import inspect
import textwrap
from functools import wraps
from typing import Any, Awaitable, Callable, List, ParamSpec, Tuple, TypeVar

import astor
from hatchet_sdk import Hatchet
from hatchet_sdk.hatchet import step, workflow
from hatchet_sdk.workflow import WorkflowMeta
from pydantic import BaseModel

_P = ParamSpec("_P")
_R = TypeVar("_R", covariant=True)


def checkpoint(*args, name: str, **kwargs):
    pass


def serialize_args(args, **kwargs):
    return args, kwargs


"""
Gotchas:
- Code in different checkpoints will be in different scopes entirely
- The function must be async
- No other decorators will be considered
- Imports will fail in the generated code
- Docstrings and comments are not considered right now
- Type annotations are not considered right now
- When registering the workflow, the workflow must be instantiated func.workflow_ref()
- When calling the workflow function, hatchet aio is used, loops must be configured properly
"""


def fht(hatchet: Hatchet, checkpoint_symbol="checkpoint"):
    """
    Fast Hatchet Transform (FHT) decorator.

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
        class_name = func_name.title().replace("_", "")
        is_async = asyncio.iscoroutinefunction(func)
        if not is_async:
            raise ValueError("Function must be async")

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
            # unreliable treatment of docstrings and comments
            # if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            #     continue  # ignore docstrings and comments
            # if isinstance(stmt, ast.AnnAssign):
            #     continue  # ignore type annotations

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

        # Create a new class for the workflow
        hatchet_workflow_decorator = ast.Call(
            func=ast.Name(id="workflow", ctx=ast.Load()),
            args=[],
            keywords=[],
        )
        class_ast = ast.ClassDef(
            name=class_name,
            bases=[],
            keywords=[],
            body=[],
            decorator_list=[hatchet_workflow_decorator],
            type_params=[],
        )

        # create a new function for every step
        for i, (step_name, step_body) in enumerate(steps):
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
            decorator_keywords = []
            if i != 0:
                previous_step_name = steps[i - 1][0]
                decorator_keywords.append(
                    ast.keyword(
                        arg="parents",
                        value=ast.List(
                            elts=[ast.Constant(value=previous_step_name)],
                            ctx=ast.Load(),
                        ),
                    )
                )

            hatchet_step_decorator = ast.Call(
                func=ast.Name(id="step", ctx=ast.Load()),
                args=[],
                keywords=decorator_keywords,
            )

            step_prelude = ""  # checks if workflow_done is set and returns if it is
            # does argument unpacking from the context

            step_epilogue = (
                ""  # handles packing and returning the final values to hatchet
            )

            # alter the body of the step to replace raise statements and update return statements
            # for stmt in step_body:
            #     if isinstance(stmt, ast.Raise):
            #         stmt = ast.Return(
            #             value=ast.Call(
            #                 func=ast.Attribute(
            #                     value=ast.Name(id="ctx", ctx=ast.Load()),
            #                     attr="error",
            #                     ctx=ast.Load(),
            #                 ),
            #                 args=[ast.Constant(value="Error in step " + step_name)],
            #                 keywords=[],
            #             )
            #         )
            #     elif isinstance(stmt, ast.Return):
            #         if i < len(steps) - 1:
            #             stmt = ast.Assign(
            #                 targets=[
            #                     ast.Subscript(
            #                         value=ast.Name(id="ctx", ctx=ast.Load()),
            #                         slice=ast.Index(
            #                             value=ast.Constant(value="workflow_done")
            #                         ),
            #                         ctx=ast.Store(),
            #                     )
            #                 ],
            #                 value=ast.Constant(value=True),
            #             )
            #     step_body[step_body.index(stmt)] = stmt

            step_func_def = ast.AsyncFunctionDef(
                name=step_name,
                args=ast.arguments(
                    posonlyargs=[],
                    args=[
                        ast.arg(arg="self", annotation=None),
                        ast.arg(arg="ctx", annotation=None),
                    ],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                body=[*step_body],
                decorator_list=[hatchet_step_decorator],
                returns=None,
                type_comment=None,
                type_params=[],
            )
            ast.fix_missing_locations(step_func_def)
            class_ast.body.append(step_func_def)

        module = ast.Module(body=[class_ast], type_ignores=[])
        ast.fix_missing_locations(module)

        print(astor.to_source(module))
        compiled_code = compile(module, "<fht_generated>", "exec")
        namespace: dict[str, Any] = {
            "workflow": workflow,  # The workflow decorator
            "step": step,  # The step decorator
            **func.__globals__,  # The globals of the original function
        }
        exec(compiled_code, namespace)

        # Get the created class from the namespace
        workflow_ref: WorkflowMeta = namespace[class_name]

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
