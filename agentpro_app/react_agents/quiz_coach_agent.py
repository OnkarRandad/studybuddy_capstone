"""
QuizCoachReActAgent: ReactAgent for adaptive quiz generation.

Uses RAGTool, GenerateQuizTool, and MemoryTool to create
personalized, difficulty-adapted quizzes.
"""

from openai import OpenAI
from agentpro_app.agentpro import ReactAgent
from agentpro_app.agentpro.tools.rag_tool import RAGTool
from agentpro_app.agentpro.tools.quiz_tool import GenerateQuizTool
from agentpro_app.agentpro.tools.memory_tool import MemoryReadTool
from agentpro_app.config import OPENAI_API_KEY


def create_quiz_coach_agent(model: str = "gpt-4o-mini", temperature: float = 0.4) -> ReactAgent:
    """
    Create a quiz coach ReactAgent with quiz generation tools.

    Args:
        model: LLM model to use
        temperature: LLM temperature

    Returns:
        Configured ReactAgent
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    # Create tools
    tools = [
        RAGTool(),
        GenerateQuizTool(model=model, temperature=temperature),
        MemoryReadTool()
    ]

    # Custom system prompt for quiz coach
    system_prompt = """You are a ReAct-style quiz coach agent that creates adaptive assessments.

Your goal is to generate quizzes that appropriately challenge students and test their understanding.

**Your Process:**
1. First, use the "retrieve_materials" tool to find relevant course materials for quiz questions
2. Use the "read_memory" tool to check student's performance history and weak topics
3. Then, use the "generate_quiz" tool with appropriate difficulty and focus areas
4. Finally, provide your Final Answer with the complete quiz

**Important:**
- Adapt difficulty based on student's quiz history (from memory)
- Focus extra questions on weak topics
- Always retrieve materials before generating quizzes
- If no materials are found, explain that course materials need to be uploaded
- Include answer keys with detailed rationales

Remember: You must use tools - don't generate quiz content directly!
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
