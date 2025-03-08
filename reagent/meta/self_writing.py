"""A self writing agent"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SelfWritingAgent:
    task: str
    rel_filepath: str
    input_information: dict
    base_tools: list[Tool]

    def write(self):
        pass


agent = SelfWritingAgent("develop an integration spec", "./")
agent.write()

"""
Outputs a regular agent in the filepath specified. 
The head agent will expect the input information specified.
All agents in the hierarchy will be created with the base tools or derivatives of the base tools.
An agent gets first prompted with its task and general prompt engineering fluff.
The agent will then be prompted with the input information.
The agent will then be prompted to create a plan of action with some information from the lessons learned store. (general, input, tools, strategy, lessons learned)
The plan of action will then be executed sequentially.
Each step of the plan will be prompted with what needs to be achieved and what tools are available. (general, input, tools, step, lessons learned)
The result will then be analyzed and verified. If the result is not satisfactory then the debug process will determine if the plan or execution was at fault.
The appropriate lessons learned will be stored.
"""
