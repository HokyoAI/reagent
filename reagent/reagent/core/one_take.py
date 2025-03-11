from abc import ABC, abstractmethod
from typing import  ClassVar,  List,  Optional

from hatchet_sdk import Hatchet
from pydantic import BaseModel, Field

from .ledger import Ledger, log_to_ledger
from .memory import Memory, MemoryStore
from .model_providers import Model
from .space import Space, SpaceDiff
from .store import Store


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


class Taskable(ABC):

    @abstractmethod
    async def complete[_I: BaseModel, _O: BaseModel](self, *, task: Task[_I, _O]) -> _O:
        pass


class Tool[_I: BaseModel, _O: BaseModel](BaseModel, Taskable):
    guid: str
    name: str
    description: str
    input_model: type[_I]
    output_model: type[_O]

    itemtype: ClassVar[str] = "tool"
    requires_approval: ClassVar[bool]

    @abstractmethod
    async def complete(self, *, task: Task[_I, _O]) -> _O:
        pass

    @abstractmethod
    async def setup(self):
        pass


class Plan:
    pass


class Result:
    pass


class Feedback:
    pass


class NeedsMorphing(BaseModel):
    needs_morphing: bool
    reason: Optional[str] = None


"""
Morphing:
Dry run the task with no defined action space, let the agent be creative in the tools and delegates it would want to use
Then display the existing tools and delegates and create a list of updates/additions
With the new action space let the agent try again and assess
If the agent fails, add that info to the agent memories and allow

Learning:
Complete the task hydrated with information, let the agent make fully informed decisions
If the agent fails, update the information it had access to and let it try again

Morphing should only be used in development
Production agents should not morph, but can learn
Using an morphing agent in parallel might to inconsistent states because the action space will change
Auto morphing can be used to allow agents to morph when they detect a need

4 Principles:
Informed Decision: Agents should be given as much information as possible to make decisions
Fast Feedback: Validation of task completions should happen as quick as possible
Monotonic Decomposition: Agents should always be able to make progress on a task by decomposing it into smaller tasks
Don't Know: Agents should be able to say they don't know when they don't have the information or tools to complete a task
"""

ActionSpaceDiff = SpaceDiff["Tool | Agent"]


class ActionSpace(Space["Tool | Agent"]):

    async def filter(
        self,
        *,
        task: Task,
    ) -> "ActionSpace":
        """
        TODO
        Returns a new ActionSpace with only the tools and agents that can be used for the task
        """
        return self

    async def diff(
        self, *, task: Task, memory_space_diff: "MemorySpaceDiff"
    ) -> ActionSpaceDiff:
        """
        TODO
        Returns a new ActionSpaceDiff with the tools and agents that will be useful given the memory space diff
        """
        return ActionSpaceDiff()


MemorySpaceDiff = SpaceDiff["Memory"]


class MemorySpace(Space["Memory"]):

    @classmethod
    async def populate(
        cls, *, task: Task, action_space: ActionSpace, memory_stores: List[MemoryStore]
    ) -> "MemorySpace":
        """
        TODO
        Returns a new MemorySpace with the memories that will be useful given the action space and memory stores
        """
        return cls()

    async def diff(
        self,
        *,
        task: Task,
        action_space_diff: ActionSpaceDiff,
        memory_stores: List[MemoryStore],
    ) -> "MemorySpaceDiff":
        """
        TODO
        Returns a new MemorySpaceDiff with the memories that will be useful given the action space diff
        """
        return MemorySpaceDiff()
    
    async def store(self, *, )


class Prompts(BaseModel):
    generic: str
    strategy: str
    skill: str


class AdaptOptions(BaseModel):
    learning: bool
    auto_learn: bool
    morphing: bool
    auto_morph: bool


def default_adapt_options():
    return AdaptOptions(
        learning=True, auto_learn=True, morphing=False, auto_morph=False
    )


class AgentOptions(BaseModel):
    space_iterations: int = Field(ge=0)
    action_space_no_filter_size: int = Field(ge=0)


def default_agent_options():
    return AgentOptions(space_iterations=1, action_space_no_filter_size=10)


class Agent(BaseModel, Taskable):

    guid: str
    store: Store
    model: Model
    options: AgentOptions
    prompts: Prompts
    adapt: AdaptOptions = Field(default_factory=default_adapt_options)
    action_space: ActionSpace
    memory_stores: List[MemoryStore]
    recursive: bool = Field(
        False, description="Determines if Agent includes itself in the action_space."
    )

    itemtype: ClassVar[str] = "agent"

    def model_post_init(self, __context):
        super().model_post_init(__context)
        if self.recursive:
            self.action_space.add(self)

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

    async def _space_init_phase(self, task: Task) -> tuple[ActionSpace, MemorySpace]:
        """
        Front loads information gathering to inform the action and memory spaces pursuant to the informed decision principle.
        """
        action_space: ActionSpace = await self._init_task_action_space(task=task)
        memory_space: MemorySpace = await self._init_task_memory_space(
            task=task, action_space=action_space
        )
        no_memory_space = MemorySpace()
        memory_space_diff: MemorySpaceDiff = memory_space - no_memory_space
        for _ in range(self.options.space_iterations):
            action_space_diff = await self._diff_task_action_space(
                task=task,
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
                    task=task,
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

    async def _init_task_action_space(self, *, task: Task) -> ActionSpace:
        """
        Initialize the action space for the task. Action space is some subset of the agent's action space.
        Should NOT edit the agent's action space at all.

        Assumes empty memory space to start.
        """
        if len(self.action_space) < self.options.action_space_no_filter_size:
            return (
                self.action_space
            )  # If the action space is small, just use the whole thing
        else:
            return await self.action_space.filter(task=task)

    async def _diff_task_action_space(
        self,
        *,
        task: Task,
        curr_action_space: ActionSpace,
        memory_space_diff: MemorySpaceDiff,
    ) -> ActionSpaceDiff:
        """
        Takes in the task the current action space, and memory_space_diff.
        Alters the action space based on the memory_space_diff.

        Returns the differential action space.
        """
        if len(curr_action_space) < self.options.action_space_no_filter_size:
            return ActionSpaceDiff()  # return no diff for small action spaces
        else:
            diff = await self.action_space.diff(
                task=task, memory_space_diff=memory_space_diff
            )
            return diff

    async def _init_task_memory_space(
        self, *, task: Task, action_space: ActionSpace
    ) -> MemorySpace:
        """
        Initialize the memory space for the task. Memory space is some subset of the agent's memory space.

        Uses the initialized action space to inform the initial memory space.
        """
        return await MemorySpace.populate(
            task=task, action_space=action_space, memory_stores=self.memory_stores
        )

    async def _diff_task_memory_space(
        self,
        *,
        task: Task,
        curr_memory_space: MemorySpace,
        action_space_diff: ActionSpaceDiff,
    ) -> MemorySpaceDiff:
        """
        Takes in the task the current memory space, and diff_action_space.
        Alters the memory space based on the diff_action_space.

        Returns the differential memory space.
        """
        return await curr_memory_space.diff(
            task=task,
            action_space_diff=action_space_diff,
            memory_stores=self.memory_stores,
        )

    async def _store_task_memory_space(self, *, memory_space: MemorySpace):
        """
        Takes in the memory space and stores it in a memory store for the task.
        This ensures durable execution and auditing.
        """
        pass

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

    async def _perform_morphing(
        self, *, ledger: TaskLedger, lessons: List[Lesson]
    ) -> None:
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

    async def save(self):
        pass

    @classmethod
    async def load(
        cls,
        guid: str,
        store: Store,
        learning: bool,
        morphing: bool,
        base_tools: List[Tool],
        base_delegates: List["Agent"],
    ):
        """
        Load agent from database
        """
        prompts, add_tools, add_delegates = await store.load_agent(agent_guid=guid)
        return cls(
            guid=guid,
            store=store,
            learning=learning,
            morphing=morphing,
            prompts=prompts,
            base_tools=base_tools,
            base_delegates=base_delegates,
            add_tools=add_tools,
            add_delegates=add_delegates,
        )


def workflow(*, node: Agent | Tool, hatchet: Hatchet):

    class HatchetWorkflow:

        @hatchet.step()
        async def complete(self):
            pass

    workflow_name = node.guid
    workflow = hatchet.workflow(name=workflow_name)(HatchetWorkflow)

    async def run_workflow[_I: BaseModel, _O: BaseModel](*, task: Task[_I, _O]) -> _O:
        ref = await hatchet.admin.aio.run_workflow(
            workflow_name=workflow_name, input=input
        )
        result = await ref.result()
        return task.template.output_model(**result)

    node.complete = run_workflow
