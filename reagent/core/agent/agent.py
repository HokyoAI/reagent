from abc import ABC, abstractmethod
from functools import partial
from typing import ClassVar, List, Optional

from hatchet_sdk import Hatchet
from pydantic import BaseModel, Field

from ..ledger import Ledger, log_to_ledger
from ..llms.llms import Llm
from ..memory.base import MemoryStore
from ..taskable import Taskable, call_taskable, checkpoint
from ..tool import Tool
from .phases.planning import PlanningPhase
from .phases.space_init import SpaceInitPhase
from .spaces import ActionSpace, MemorySpace


class TaskSpec[_I: BaseModel, _O: BaseModel](BaseModel):
    """
    This is the class that will be used for agents to adapt to new tasks.
    """

    description: str
    input_model: type[_I]
    output_model: type[_O]


class Task[_I: BaseModel, _O: BaseModel](BaseModel):
    """
    Done this way to get around the ClassVar typing issue (doesn't accept type variables)
    """

    spec: TaskSpec[_I, _O]
    ledger_id: str
    input: _I


class Plan:
    pass


class Result:
    pass


class Feedback:
    pass


class NeedsMorphing(BaseModel):
    needs_morphing: bool
    reason: Optional[str] = None


class Prompts(BaseModel):
    generic: str
    strategy: str
    skill: str


class AgentOptions(BaseModel):
    space_iterations: int = Field(default=1, ge=0)
    action_space_no_filter_size: int = Field(default=10, ge=0)
    recursive: bool = Field(
        default=False,
        description="Determines if Agent includes itself in the action_space.",
    )
    learning: bool = True
    auto_learn: bool = True
    morphing: bool = False
    auto_morph: bool = False


async def complete[_I: BaseModel, _O: BaseModel](self, *, task: Task[_I, _O]) -> _O:
    ledger = await self._create_task_ledger(task)

    if self.adapt.morphing and self.adapt.auto_morph:
        await self._perform_morphing(
            ledger=ledger, lessons=[*planning_lessons, *skill_lessons]
        )
    plan = await self._plan(ledger=ledger, lessons=planning_lessons)
    result = await self._execute(ledger=ledger, plan=plan, lessons=skill_lessons)
    feedback = await self._verify(
        ledger=ledger, result=result, lessons=verification_lessons
    )
    """
    Feedback can be used to update the agent's strategy and skill prompts, or add new lessons learned
    Only morphing can add new tools or delegates
    """


async def morph(self, *, task: Task):
    while True:
        result = await self._perform_morphing(task=task)


async def learn(self, *, task: Task):
    while True:
        result = await self._perform_learning(task=task)


async def _perform_learning(self, *, task: Task):
    pass


async def _create_task_ledger(self, task: Task) -> Ledger:
    return Ledger(id=task.ledger_id)


async def _task_loop(self, task: Task):
    action_space, memory_space = await self._space_init_phase(task=task)
    # initialize the action and memory spaces for the task
    # any future phase can ask for changes to the spaces if necessary

    """
    agents should bias towards completing the task themselves if possible
    this helps prevent huge tree structures of decomposition
    recursive agents could get stuck in a loop if they always delegate
    """
    await self._planning_phase(task=task, task_memory=task_memory)
    # plan the task, using the task memory to inform the plan

    await self._execution_phase(task=task, task_memory=task_memory)
    # execute the plan, using the task memory to inform the execution

    await self._synthesis_phase(task=task, task_memory=task_memory)
    # synthesize the results of the execution, using the task memory to inform the synthesis

    await self._verification_phase(task=task, task_memory=task_memory)
    # verify the results, using the task memory to inform the verification

    # while True:
    #     planning_memories = await self._get_plan_memories(task=task)
    #     plan = await self._plan_task(task=task, memories=planning_memories)
    #     for decomp_task in plan:
    #         await self._step_loop(task=decomp_task)
    #     result = await self._synthesize_results()
    #     feedback = await self._verify_results(result)
    #     await self._handle_result_feedback()


async def _request_help(self, task: Task):
    """
    Can be used when an agent feels it doesn't have the information or tools to complete a task.
    Will first look for more information or tools to see if that helps.
    if that doesn't work, it will propagate the request to the user.

    Pursuant to the "Know what you don't know" principle.
    """
    pass


async def _step_loop(self, task: Task):
    while True:
        step_result = await self._execute_step(task=task)
        step_feedback = await self._verify_step(step_result)
        should_continue = await self._handle_step_feedback(step_feedback)
        if not should_continue:
            break


async def _get_plan_memories(self, task: Task) -> List[Memory]:
    pass


async def _plan_task(self, *, task: Task) -> Plan:
    return Plan()


async def _execute_step(self, *, task: Task) -> Result:
    pass


@log_to_ledger
async def _needs_morphing(
    self,
    *,
    ledger: TaskLedger,
    tools: List[Tool],
    delegates: List["Agent"],
    lessons: List[Lesson],
) -> NeedsMorphing:
    """
    Returns whether the agent needs to morph
    Can either be an update to an existing tool or agent, or a new tool or agent
    """
    pass


@log_to_ledger
async def _morph_child_nodes(
    self,
    *,
    ledger: TaskLedger,
    morph_reason: Optional[str],
    tools: List[Tool],
    delegates: List["Agent"],
    lessons: List[Lesson],
) -> "Tool | Agent":
    """
    Returns an agent or derivative tool for the agent to utilize
    """
    pass


async def _perform_morphing(self, *, ledger: TaskLedger, lessons: List[Lesson]) -> None:
    all_tools = [*self.base_tools, *self.add_tools]
    all_delegates = [*self.base_delegates, *self.add_delegates]
    needs_morphing = await self._needs_morphing(
        ledger=ledger,
        tools=all_tools,
        delegates=all_delegates,
        lessons=lessons,
    )
    while needs_morphing.needs_morphing:
        addition = await self._morph_child_nodes(
            ledger=ledger,
            morph_reason=needs_morphing.reason,
            tools=all_tools,
            delegates=all_delegates,
            lessons=lessons,
        )
        if isinstance(addition, Agent):
            self.add_delegates.append(addition)
            all_delegates.append(addition)
        elif isinstance(addition, Tool):
            self.add_tools.append(addition)
            all_tools.append(addition)
        else:
            raise ValueError("Morphed addition must be an agent or tool")

        needs_morphing = await self._needs_morphing(
            ledger=ledger, tools=all_tools, delegates=all_delegates, lessons=lessons
        )


@log_to_ledger
async def _plan(self, *, ledger: TaskLedger, lessons: List[Lesson]) -> Plan:
    pass


@log_to_ledger
async def _execute(
    self, *, ledger: TaskLedger, plan: Plan, lessons: List[Lesson]
) -> Result:
    pass


@log_to_ledger
async def _verify(
    self, *, ledger: TaskLedger, result: Result, lessons: List[Lesson]
) -> Feedback:
    pass


class Agent[_I: BaseModel, _O: BaseModel](Taskable[_I, _O]):
    llm: Llm
    prompts: Prompts
    options: AgentOptions = Field(default_factory=AgentOptions)
    action_space: ActionSpace
    memory_stores: List[MemoryStore]

    def model_post_init(self, __context):
        super().model_post_init(__context)
        if self.options.recursive:
            self.action_space.add(self)
        self.fn = partial(
            __do, agent=self
        )  # cannot inspect __do source because of partial


async def __do[_I: BaseModel, _O: BaseModel](input: _I, agent: Agent[_I, _O]) -> _O:
    action_space, memory_space = await SpaceInitPhase(input=input, agent=agent)()
    checkpoint(action_space, memory_space, checkpoint_name="planning")
    plan = await PlanningPhase(
        input=input, agent=agent, action_space=action_space, memory_space=memory_space
    )()
    checkpoint(plan, checkpoint_name="execution")

    await self._execution_phase(task=task, task_memory=task_memory)
    # execute the plan, using the task memory to inform the execution
    await self._verification_phase(task=task, task_memory=task_memory)
    # verify the results, using the task memory to inform the verification

    await self._synthesis_phase(task=task, task_memory=task_memory)
    # synthesize the results of the execution, using the task memory to inform the synthesis
