import time

from dotenv import load_dotenv
from hatchet_sdk import Context, Hatchet

from tests.reagent_tests.hatchet.fht.functions import get_workflow_version

load_dotenv(override=True)

hatchet = Hatchet(debug=True)

workflow_func = get_workflow_version(hatchet)


def main() -> None:
    worker = hatchet.worker("test-worker", max_runs=1)
    worker.register_workflow(workflow_func.workflow_ref())  # type: ignore
    worker.start()


if __name__ == "__main__":
    main()
