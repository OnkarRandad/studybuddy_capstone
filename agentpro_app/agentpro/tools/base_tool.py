"""
Base Tool class for AgentPro framework.

All tools must inherit from this class and implement the run() method.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class Tool(ABC, BaseModel):
    """
    Abstract base class for all AgentPro tools.

    Tools are the primary mechanism for agents to interact with the world.
    Each tool must implement the run() method to execute its functionality.

    Attributes:
        name: Human-readable name of the tool
        description: What the tool does
        action_type: Unique identifier for the tool (used in action routing)
        input_format: Description of expected input structure
    """

    name: str = Field(..., description="Name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    action_type: str = Field(..., description="Action type identifier for this tool")
    input_format: str = Field(..., description="Expected input format")

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    def run(self, input_data: Any) -> str:
        """
        Execute the tool's functionality.

        Args:
            input_data: Input for the tool (format specified by input_format)

        Returns:
            String result from tool execution
        """
        pass

    def get_tool_description(self) -> str:
        """
        Get formatted tool description for prompt construction.

        Returns:
            Multi-line string with tool metadata
        """
        return f"""Tool: {self.name}
Action Type: {self.action_type}
Description: {self.description}
Input Format: {self.input_format}"""
