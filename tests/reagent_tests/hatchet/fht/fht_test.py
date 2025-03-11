import time

import pytest
from dotenv import load_dotenv
from hatchet_sdk import Hatchet, Worker

load_dotenv()

from reagent.reagent.core.fht import checkpoint, fht


async def my_function(self, x: int = 1):
    """
    Example Docstring
    """
    print("Step 1")
    checkpoint(1, name="middle")
    print("Step 2")
    checkpoint(2, name="finish")
    print("Step 3")
    return "Done"


# requires scope module or higher for shared event loop
@pytest.mark.asyncio(scope="session")
async def test_run(hatchet: Hatchet, worker: Worker) -> None:
    result = await my_function(None, 1)

    time.sleep(5)
    # run = hatchet.admin.run_workflow("DagWorkflow", {})
    # result = await run.result()

    # one = result["step1"]["rando"]
    # two = result["step2"]["rando"]
    # assert result["step3"]["sum"] == one + two
    # assert result["step4"]["step4"] == "step4"
