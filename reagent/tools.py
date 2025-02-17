from typing import Any

from pydantic import BaseModel


class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]


class RespondTool(Tool):
    name = "respond"
    description = """
Responds to the asking user with a final result.
This will end your turn in the conversation and you chatbot.
will no longer be able to think further or use more tools until the user asks you something again.
"""
    inputs = {
        "answer": {"type": "any", "description": "The final answer to the problem"}
    }
    output_type = "any"

    def forward(self, answer: Any) -> Any:
        return answer
