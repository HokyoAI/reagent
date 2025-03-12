import time

import pytest
from hatchet_sdk import Hatchet, Worker

from tests.reagent_tests.hatchet.fht.functions import get_workflow_version, my_function


# requires scope module or higher for shared event loop
@pytest.mark.asyncio(scope="session")
async def test_run(aiohatchet: Hatchet, worker: Worker) -> None:
    result = await my_function(None, 1)

    time.sleep(2)

    workflow_func = get_workflow_version(aiohatchet)
    result2 = await workflow_func(None, 1)
    assert result == result2["finish"]

    # time.sleep(5)
