"""
Base Tool class for AgentPro framework.

All tools must inherit from this class and implement the run() method.
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    Abstract base class for all AgentPro tools.
    
    Tools are the building blocks that agents use to accomplish tasks.
    Each tool has a unique action_type that maps to specific functionality.
    
    Attributes:
        name: Human-readable name of the tool
        description: What the tool does
        action_type: Unique identifier for this tool (used in Action objects)
        input_format: Description of expected input format
    """
    
    name: str = "Base Tool"
    description: str = "Base tool description"
    action_type: str = "base_action"
    input_format: str = "Input format description"
    
    @abstractmethod
    def run(self, input_data: Any) -> str:
        """
        Execute the tool's functionality.
        
        Args:
            input_data: Input for the tool (can be string, dict, list, etc.)
            
        Returns:
            String result that will be added as an Observation
        """
        pass
    
    def get_tool_description(self) -> str:
        """
        Generate formatted tool description for system prompt.
        
        Returns:
            Formatted string describing the tool
        """
        return f"""
Tool: {self.name}
Action Type: {self.action_type}
Description: {self.description}
Input Format: {self.input_format}
"""
    
    def __repr__(self) -> str:
        return f"Tool(name={self.name}, action_type={self.action_type})"