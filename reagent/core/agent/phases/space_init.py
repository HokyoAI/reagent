from typing import TYPE_CHECKING

from pydantic import BaseModel

from ..spaces import ActionSpace, ActionSpaceDiff, MemorySpace, MemorySpaceDiff

if TYPE_CHECKING:
    from ..agent import Agent


class SpaceInitPhase:
    def __init__(self, input: BaseModel, agent: Agent):
        self.input = input
        self.agent = agent

    async def __call__(self) -> tuple[ActionSpace, MemorySpace]:
        """
        Front loads information gathering to inform the action and memory spaces pursuant to the informed decision principle.
        """
        action_space: ActionSpace = await self._init_task_action_space()
        memory_space: MemorySpace = await self._init_task_memory_space(
            action_space=action_space
        )
        no_memory_space = MemorySpace()
        memory_space_diff: MemorySpaceDiff = memory_space - no_memory_space
        for _ in range(self.agent.options.space_iterations):
            action_space_diff = await self._diff_task_action_space(
                curr_action_space=action_space,
                memory_space_diff=memory_space_diff,
            )
            if len(action_space_diff) == 0:
                break
            else:
                action_space = ActionSpace(
                    elements=(action_space + action_space_diff).elements
                )  # subclassing is causing typing issues with __add__ and __sub__

                memory_space_diff = await self._diff_task_memory_space(
                    curr_memory_space=memory_space,
                    action_space_diff=action_space_diff,
                )
                if len(memory_space_diff) == 0:
                    break
                else:
                    memory_space = MemorySpace(
                        elements=(memory_space + memory_space_diff).elements
                    )

        return action_space, memory_space

    async def _init_task_action_space(self) -> ActionSpace:
        """
        Initialize the action space for the task. Action space is some subset of the agent's action space.
        Should NOT edit the agent's action space at all.

        Assumes empty memory space to start.
        """
        if (
            len(self.agent.action_space)
            < self.agent.options.action_space_no_filter_size
        ):
            return (
                self.agent.action_space  # If the action space is small, just use the whole thing
            )
        else:
            return await self.agent.action_space.filter(input=self.input)

    async def _diff_task_action_space(
        self,
        *,
        curr_action_space: ActionSpace,
        memory_space_diff: MemorySpaceDiff,
    ) -> ActionSpaceDiff:
        """
        Takes in the task the current action space, and memory_space_diff.
        Alters the action space based on the memory_space_diff.

        Returns the differential action space.
        """
        if len(curr_action_space) < self.agent.options.action_space_no_filter_size:
            return ActionSpaceDiff()  # return no diff for small action spaces
        else:
            diff = await self.agent.action_space.diff(
                input=self.input, memory_space_diff=memory_space_diff
            )
            return diff

    async def _init_task_memory_space(
        self, *, action_space: ActionSpace
    ) -> MemorySpace:
        """
        Initialize the memory space for the task. Memory space is some subset of the agent's memory space.

        Uses the initialized action space to inform the initial memory space.
        """
        return await MemorySpace.populate(
            input=self.input,
            action_space=action_space,
            memory_stores=self.agent.memory_stores,
        )

    async def _diff_task_memory_space(
        self,
        *,
        curr_memory_space: MemorySpace,
        action_space_diff: ActionSpaceDiff,
    ) -> MemorySpaceDiff:
        """
        Takes in the task the current memory space, and diff_action_space.
        Alters the memory space based on the diff_action_space.

        Returns the differential memory space.
        """
        return await curr_memory_space.diff(
            input=self.input,
            action_space_diff=action_space_diff,
            memory_stores=self.agent.memory_stores,
        )
