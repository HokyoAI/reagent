from typing import TYPE_CHECKING, List

from pydantic import BaseModel, Field

from reagent.core.llms.llms import LlmTool, ModelCall, response_model_llm_tool
from reagent.core.llms.messages import SystemMessage, UserMessage

from ..spaces import ActionSpace, ActionSpaceDiff, MemorySpace, MemorySpaceDiff

if TYPE_CHECKING:
    from ..agent import Agent


class Step(BaseModel):
    """
    A step in a plan that can be executed to complete a task.
    """

    goal: str = Field(
        ..., description="The goal that needs to be achieved in this step."
    )


class Plan(BaseModel):
    """
    A plan is a sequence of steps that can be executed to complete a task.
    """

    steps: List[Step] = Field(
        ..., description="The steps in the plan to complete the task."
    )


plan_response_model_tool = response_model_llm_tool(Plan)


class PlanningPhase:
    """
    Gives the agent the memories, action space, and input as a prompt.

    Tells the agent to either generate a plan to complete the task or ask for help.
    """

    def __init__(
        self,
        input: BaseModel,
        agent: "Agent",
        action_space: ActionSpace,
        memory_space: MemorySpace,
    ):
        self.input = input
        self.agent = agent
        self.action_space = action_space
        self.memory_space = memory_space

    async def __call__(self) -> Plan:
        system_message = SystemMessage(
            content="""
You are an expert planner. Your purpose is to help the user by generating a plan to complete the task provided to you. \
You will be given a description of the task, the task's input, the expected output, the tools and delegates that you have available \
and any additional context that may be relevant to the task. \
The plan will be executed and you will be given an opportunity to verify the result \
and synthesize a final response to the user after the plan is executed. \
You do not need to include the verification or synthesis steps in your plan. \
It is very important that you ask for help if you are unsure how to proceed or do not believe you can complete the task. \
Here are the requirements for building a good plan: 
1. The plan should be a sequence of steps that can be executed to complete the task.
2. If the task is complex you should break it down into smaller sub-tasks and delegate those sub-tasks to the appropriate tools or agents.
3. If you are unsure how to proceed or do not believe you can complete the task, you should ask for help.
4. The plan should be clear and concise, with each step clearly defined.
5. Do not delegate the entire task to another agent or tool unless you are sure that you cannot complete it yourself.
6. Do not include any steps that are not necessary to complete the task.
7. Do not include the verification or synthesis steps in your plan.
        """
        )
        model_call = ModelCall(
            messages=[system_message, UserMessage(content=str(self.input))],
            tools=[plan_response_model_tool],
        )
        output = await self.agent.llm.complete(model_call)
        if not output.tool_calls:
            raise ValueError("No tool calls found in the model output.")
        plan_tool_call = list(output.tool_calls.values())[0]
        if plan_tool_call.name != plan_response_model_tool.name:
            raise ValueError(
                f"Unexpected tool call name: {plan_tool_call.name}. Expected: {plan_response_model_tool.name}"
            )
        plan = Plan.model_validate(plan_tool_call.arguments)

        # ask the model to verify that the plan is correct
        verification_message = SystemMessage(
            content=""""
You have generated a plan to complete the task. \
Please verify that the plan is correct and that it will achieve the goal. \
If the plan is correct, please return it as is. \
If the plan is not correct, please modify it to make it correct. \
If you are unsure how to modify the plan, please ask for help. \
Do not include any verification or synthesis steps in your response.
            """
        )
        verification_model_call = ModelCall(
            messages=[verification_message, UserMessage(content=str(plan))],
            tools=[plan_response_model_tool],
        )
        verification_output = await self.agent.llm.complete(verification_model_call)
        if not verification_output.tool_calls:
            raise ValueError("No tool calls found in the model output.")
        verification_tool_call = list(verification_output.tool_calls.values())[0]
        if verification_tool_call.name != plan_response_model_tool.name:
            raise ValueError(
                f"Unexpected tool call name: {verification_tool_call.name}. Expected: {plan_response_model_tool.name}"
            )
        verified_plan = Plan.model_validate(verification_tool_call.arguments)
        return verified_plan


"""
In large engineering projects, the challenge of validating a top-down plan while maintaining efficiency is significant.
Here are effective checks and balances that can be implemented without overly slowing down work:
Technical Design Reviews

Multi-level reviews: Have independent technical experts review plans at key milestones
Red team exercises: Assign a dedicated team to find flaws in the approach or identify potential failure points
Prototype validation: Test critical components or concepts early to confirm viability

Feedback Loops

Bottom-up communication channels: Create structured ways for frontline engineers to flag issues directly to senior leadership
Regular technical sync meetings: Hold cross-functional meetings where implementation challenges can surface quickly
Anonymous feedback systems: Allow concerns to be raised without fear of organizational repercussions

Distributed Responsibility

Technical authority at multiple levels: Ensure project leads have genuine decision-making power within their domains
Consensus-based technical decisions: Require agreement from multiple stakeholders on critical design choices
Empowered expertise: Allow subject matter experts to challenge decisions regardless of hierarchical position

Risk Management

Progressive elaboration: Start with high-level plans that become more detailed as uncertainties are resolved
Regular risk reviews: Schedule dedicated sessions to identify, assess, and mitigate emerging risks
Contingency planning: Develop alternate approaches for high-risk aspects of the project

Metrics and Validation

Clear success criteria: Define measurable outcomes for each project phase
Independent testing: Have separate teams validate that components meet requirements
Continuous integration: Implement systems that automatically test components as they're developed

The key is finding the balance between necessary validation and bureaucratic overhead. Too many checks create analysis paralysis, while too few can lead to catastrophic failures. This balance often depends on project criticality, available resources, and organizational culture.
"""
