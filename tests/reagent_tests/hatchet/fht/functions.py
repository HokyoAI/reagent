from hatchet_sdk import Hatchet

from reagent.reagent.core.fht import checkpoint, fht


async def my_function(self, x: int = 1):
    """
    Example Docstring
    """
    print("Step 1")
    checkpoint({"step1": 1}, name="middle")
    print("Step 2")
    checkpoint({"step2": 2}, name="finish")
    print("Step 3")
    return {"result": "Done"}


def get_workflow_version(hatchet: Hatchet):
    my_function_workflow = fht(hatchet)(my_function)
    return my_function_workflow
