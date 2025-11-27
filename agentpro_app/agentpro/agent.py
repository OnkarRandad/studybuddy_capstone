"""
AgentPro core data structures for ReAct pattern.

Implements:
- ThoughtStep: Single reasoning step with thought, action, observation
- Action: Tool invocation with action_type and input
- Observation: Result from tool execution
- AgentResponse: Complete agent response with thought process and final answer
"""

from typing import Optional, List, Any, Dict, Union
from pydantic import BaseModel, Field
import json


class Action(BaseModel):
    """
    Represents an action to be executed by a tool.

    Attributes:
        action_type: The type of action (maps to tool action_type)
        input: The input for the action (can be string, list, or dict)
    """
    action_type: str = Field(..., description="The type of action to execute")
    input: Union[str, List, Dict] = Field(default_factory=dict, description="Input for the action")

    def get_input(self) -> Union[str, List, Dict]:
        """Safely returns the action input."""
        return self.input


class Observation(BaseModel):
    """
    Represents the result/observation from executing an action.

    Attributes:
        result: The result after running an action
    """
    result: Any = Field(..., description="The result after running an action")


class ThoughtStep(BaseModel):
    """
    Represents a single step in the ReAct reasoning process.

    Attributes:
        thought: The reasoning/thinking process
        action: The action to execute (optional)
        observation: The observation from action execution (optional)
        pause_reflection: Optional pause for reflection
    """
    thought: Optional[str] = Field(None, description="The reasoning process")
    action: Optional[Action] = Field(None, description="The action to execute")
    observation: Optional[Observation] = Field(None, description="The observation from action")
    pause_reflection: Optional[str] = Field(None, description="Optional pause for reflection")


class AgentResponse(BaseModel):
    """
    Complete agent response with reasoning process and final answer.

    Attributes:
        thought_process: List of ThoughtStep objects showing the reasoning journey
        final_answer: The final answer from the agent
    """
    thought_process: List[ThoughtStep] = Field(
        default_factory=list,
        description="Complete history of Thought → Action → Observation steps"
    )
    final_answer: Optional[str] = Field(None, description="The final answer from the agent")

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "thought_process": [step.model_dump() for step in self.thought_process],
            "final_answer": self.final_answer
        }

    def get_final_answer(self) -> str:
        """Get the final answer or empty string."""
        return self.final_answer or ""
