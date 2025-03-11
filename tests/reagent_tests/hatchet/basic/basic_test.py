import pytest
from hatchet_sdk import Hatchet, Worker


# requires scope module or higher for shared event loop
@pytest.mark.asyncio(loop_scope="session")
async def test_run(hatchet: Hatchet, worker: Worker) -> None:
    run = hatchet.admin.run_workflow("MyWorkflow", {})
    result = await run.result()

    one = result["step1"]
    assert one == "step1"
