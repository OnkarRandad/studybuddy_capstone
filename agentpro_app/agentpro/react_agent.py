"""
ReactAgent: Core AgentPro class implementing ReAct-style agent framework.

Implements the ReAct pattern:
1. Thought: Agent reasons about the task
2. Action: Agent decides to use a tool
3. Observation: Tool execution result
4. Repeat until Final Answer

The agent maintains a complete history of thought steps and produces
a structured AgentResponse.
"""

import re
import json
from typing import List, Optional, Dict, Any
from openai import OpenAI

from .agent import ThoughtStep, Action, Observation, AgentResponse
from .tools.base_tool import Tool


class ReactAgent:
    """
    ReAct-style agent that uses tools to accomplish tasks.

    The agent follows a thought-action-observation loop:
    1. Thinks about what to do next
    2. Takes an action (uses a tool)
    3. Observes the result
    4. Repeats until it can provide a final answer

    Attributes:
        client: OpenAI client for LLM calls
        tools: List of available tools
        system_prompt: Base system prompt (augmented with tool descriptions)
        max_iterations: Maximum reasoning loop iterations
        model: LLM model to use
        temperature: LLM temperature
        tool_registry: Dictionary mapping action_type to tool
    """

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        tools: Optional[List[Tool]] = None,
        system_prompt: Optional[str] = None,
        max_iterations: int = 20,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3
    ):
        """
        Initialize ReactAgent.

        Args:
            client: OpenAI client (creates default if None)
            tools: List of tools available to the agent
            system_prompt: Custom system prompt (uses default if None)
            max_iterations: Maximum reasoning iterations
            model: LLM model name
            temperature: LLM temperature
        """
        self.client = client or OpenAI()
        self.tools = tools or []
        self.max_iterations = max_iterations
        self.model = model
        self.temperature = temperature

        # Build tool registry for quick lookup
        self.tool_registry: Dict[str, Tool] = {
            tool.action_type: tool for tool in self.tools
        }

        # Build system prompt with tool descriptions
        self.system_prompt = self._build_system_prompt(system_prompt)

    def _build_system_prompt(self, base_prompt: Optional[str] = None) -> str:
        """
        Build system prompt with tool descriptions.

        Args:
            base_prompt: Base prompt to augment

        Returns:
            Complete system prompt with tool information
        """
        if base_prompt is None:
            base_prompt = """You are a ReAct-style reasoning agent. You solve tasks by following this pattern:

Thought: [Your reasoning about what to do next]
Action: {"action_type": "tool_name", "input": "input_data"}
Observation: [Result from tool execution - provided by system]

You must continue this loop until you have enough information to provide a final answer.
When you're ready to answer, use:

Final Answer: [Your complete answer to the user]

IMPORTANT RULES:
1. You MUST use the Thought → Action → Observation pattern
2. NEVER provide content directly - always use tools
3. Each response must contain EITHER an Action OR a Final Answer, not both
4. Actions must be valid JSON matching the tool's input format
5. Think step-by-step and use tools to gather information
"""

        # Add tool descriptions
        if self.tools:
            tool_descriptions = "\n\n".join([
                tool.get_tool_description() for tool in self.tools
            ])
            base_prompt += f"\n\nAVAILABLE TOOLS:\n{tool_descriptions}"

        return base_prompt

    def _get_llm_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Get response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            LLM response text
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048
        )
        return response.choices[0].message.content

    def _parse_thought(self, text: str) -> Optional[str]:
        """Extract thought from response."""
        match = re.search(r"Thought:\s*(.*?)(?:Action:|PAUSE:|Final Answer:|$)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _parse_action(self, text: str) -> Optional[Action]:
        """Extract and parse action from response."""
        match = re.search(r"Action:\s*({.*?})", text, re.DOTALL)
        if match:
            try:
                action_dict = json.loads(match.group(1))
                return Action(**action_dict)
            except (json.JSONDecodeError, ValueError) as e:
                return None
        return None

    def _parse_final_answer(self, text: str) -> Optional[str]:
        """Extract final answer from response."""
        match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _parse_pause(self, text: str) -> Optional[str]:
        """Extract pause reflection from response."""
        match = re.search(r"PAUSE:\s*(.*?)(?:Action:|Final Answer:|$)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def execute_tool(self, action: Action) -> str:
        """
        Execute a tool based on the action.

        Args:
            action: Action object with action_type and input

        Returns:
            Result string from tool execution
        """
        tool = self.tool_registry.get(action.action_type)
        if not tool:
            available_tools = ", ".join(self.tool_registry.keys())
            return f"Error: Unknown action type '{action.action_type}'. Available tools: {available_tools}"

        try:
            result = tool.run(action.get_input())
            return str(result)
        except Exception as e:
            return f"Error executing tool '{action.action_type}': {str(e)}"

    def run(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        Run the ReAct agent on a query.

        Args:
            query: User query to process
            context: Optional context dictionary (e.g., user_id, course_id, etc.)

        Returns:
            AgentResponse with thought_process and final_answer
        """
        thought_process = []
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]

        # Add context to initial message if provided
        if context:
            context_str = f"\n\nContext: {json.dumps(context, indent=2)}"
            messages[-1]["content"] += context_str

        for iteration in range(self.max_iterations):
            # Get LLM response
            response_text = self._get_llm_response(messages)

            # Parse response
            thought = self._parse_thought(response_text)
            action = self._parse_action(response_text)
            final_answer = self._parse_final_answer(response_text)
            pause = self._parse_pause(response_text)

            # Create thought step
            step = ThoughtStep(
                thought=thought,
                action=action,
                pause_reflection=pause
            )

            # Check for final answer
            if final_answer:
                thought_process.append(step)
                return AgentResponse(
                    thought_process=thought_process,
                    final_answer=final_answer
                )

            # Execute action if present
            if action:
                observation_result = self.execute_tool(action)
                step.observation = Observation(result=observation_result)

                # Add observation to messages for next iteration
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Observation: {observation_result}"})
            else:
                # No action and no final answer - add response and continue
                messages.append({"role": "assistant", "content": response_text})

            thought_process.append(step)

        # Max iterations reached without final answer
        return AgentResponse(
            thought_process=thought_process,
            final_answer="I apologize, but I reached the maximum number of reasoning steps without arriving at a complete answer. Please try rephrasing your question or breaking it into smaller parts."
        )

    def add_tool(self, tool: Tool):
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.tool_registry[tool.action_type] = tool
        # Rebuild system prompt with new tool
        self.system_prompt = self._build_system_prompt()
