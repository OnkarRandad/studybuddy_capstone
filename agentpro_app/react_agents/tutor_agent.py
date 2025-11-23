"""
TutorReActAgent: ReactAgent for study guides and explanations.

Uses RAGTool, GenerateStudyGuideTool, and MemoryTool to provide
comprehensive, personalized study guides.
"""

from openai import OpenAI
from agentpro_app.agentpro import ReactAgent
from agentpro_app.agentpro.tools.rag_tool import RAGTool
from agentpro_app.agentpro.tools.study_guide_tool import GenerateStudyGuideTool
from agentpro_app.agentpro.tools.memory_tool import MemoryReadTool
from agentpro_app.config import OPENAI_API_KEY


def create_tutor_agent(model: str = "gpt-4o-mini", temperature: float = 0.3) -> ReactAgent:
    """
    Create a tutor ReactAgent with study guide generation tools.

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
        GenerateStudyGuideTool(model=model, temperature=temperature),
        MemoryReadTool()
    ]

    # Custom system prompt for tutor
    system_prompt = """You are a ReAct-style tutoring agent that helps students learn.

Your goal is to provide comprehensive, well-cited study guides that help students understand concepts deeply.

**Your Process:**
1. First, use the "retrieve_materials" tool to find relevant course materials
2. Use the "read_memory" tool to understand the student's learning profile
3. Then, use the "generate_study_guide" tool to create a personalized study guide
4. Finally, provide your Final Answer with the complete study guide

**Important:**
- ALWAYS retrieve materials before generating a study guide
- Personalize explanations based on student's weak/strong topics
- If no materials are found, explain that course materials need to be uploaded
- Include citations, examples, and practice questions in your guides

Remember: You must use tools - don't generate content directly!
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
