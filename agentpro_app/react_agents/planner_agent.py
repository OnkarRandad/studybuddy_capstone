"""
PlannerReActAgent: ReactAgent for study planning and scheduling.

Uses MemoryTool, AnalyzeProgressTool, and CreateStudyPlanTool to generate
personalized study schedules with spaced repetition.
"""

from openai import OpenAI
from agentpro_app.agentpro import ReactAgent
from agentpro_app.agentpro.tools.planner_tool import CreateStudyPlanTool
from agentpro_app.agentpro.tools.progress_tool import AnalyzeProgressTool
from agentpro_app.agentpro.tools.memory_tool import MemoryReadTool
from agentpro_app.config import OPENAI_API_KEY


def create_planner_agent(model: str = "gpt-4o-mini", temperature: float = 0.4) -> ReactAgent:
    """
    Create a planner ReactAgent with study planning tools.

    Args:
        model: LLM model to use
        temperature: LLM temperature

    Returns:
        Configured ReactAgent
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Create tools
    tools = [
        MemoryReadTool(),
        AnalyzeProgressTool(model=model, temperature=0.7),
        CreateStudyPlanTool(model=model, temperature=temperature)
    ]

    # Custom system prompt for planner
    system_prompt = """You are a ReAct-style study planning agent that creates personalized learning schedules.

Your goal is to create realistic, effective study plans that prioritize weak topics and use spaced repetition.

**Your Process:**
1. First, use the "read_memory" tool to get student's learning profile and preferences
2. Optionally, use the "analyze_progress" tool to get detailed insights on student's progress
3. Then, use the "create_study_plan" tool to generate a personalized weekly schedule
4. Finally, provide your Final Answer with the complete study plan

**Important:**
- Prioritize weak topics (60% of study time)
- Include spaced repetition (review at 1, 3, 7, 14 day intervals)
- Keep daily study loads realistic based on student's preferences
- If student has a deadline, calculate timeline appropriately
- Include review sessions and practice tests

Remember: You must use tools - don't generate study plans directly!
"""

    # Create and return ReactAgent
    return ReactAgent(
        client=client,
        tools=tools,
        system_prompt=system_prompt,
        max_iterations=10,
        model=model,
        temperature=temperature
    )
