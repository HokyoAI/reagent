import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from typing import Callable, ClassVar, Dict, List, Literal, Optional

from hatchet_sdk import Hatchet
from pydantic import BaseModel, Field

from .ledger import TaskLedger, log_to_ledger
from .memory import Memory
from .model_providers import Model
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


class Prompts(BaseModel):
    generic: str
    strategy: str
    skill: str


class AdaptOptions(BaseModel):
    learning: bool
    morphing: bool
    auto_morph: bool


def default_adapt_options():
    return AdaptOptions(learning=False, morphing=False, auto_morph=False)


class Plan:
    pass


class Result:
    pass


class Feedback:
    pass


class NeedsMorphing(BaseModel):
    needs_morphing: bool
    reason: Optional[str] = None


@dataclass
class Agent(BaseModel, Taskable):
    """
    Morphing should only be used in development
    Production agents should not morph, but can learn
    Using an morphing agent in parallel can lead to inconsistent states
    Auto morphing can be used to allow agents to morph when they detect a need
    """

    guid: str
    store: Store
    model: Model
    prompts: Prompts
    memories: List[Memory]
    base_tools: list[Tool]
    base_delegates: list["Agent"]
    adapt: AdaptOptions = Field(default_factory=default_adapt_options)
    add_tools: list[Tool] = Field(default_factory=list)
    add_delegates: list["Agent"] = Field(default_factory=list)

    itemtype: ClassVar[str] = "agent"

    async def complete[_I: BaseModel, _O: BaseModel](self, *, task: Task[_I, _O]) -> _O:
        ledger = await self._create_task_ledger(task)
        planning_lessons = await self.store.get_relevant_lessons(
            agent_guid=self.guid, lesson_type="strategy"
        )
        skill_lessons = await self.store.get_relevant_lessons(
            agent_guid=self.guid, lesson_type="skill"
        )
        verification_lessons = await self.store.get_relevant_lessons(
            agent_guid=self.guid, lesson_type="verification"
        )
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

    async def _create_task_ledger(self, task: Task) -> TaskLedger:
        return TaskLedger(id=task.ledger_id)

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

    async def morph(
        self, *, ledger: TaskLedger, lessons: List[Lesson], task_spec: TaskSpec
    ):
        """TODO implement with task spec"""
        await self._perform_morphing(ledger=ledger, lessons=lessons)

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
