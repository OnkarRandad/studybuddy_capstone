"""
FlashcardsReActAgent: ReactAgent for flashcard generation.

Uses RAGTool and GenerateFlashcardsTool to create spaced-repetition flashcards.
"""

from openai import OpenAI
from agentpro_app.agentpro import ReactAgent
from agentpro_app.agentpro.tools.rag_tool import RAGTool
from agentpro_app.agentpro.tools.flashcards_tool import GenerateFlashcardsTool
from agentpro_app.agentpro.tools.memory_tool import MemoryReadTool
from agentpro_app.config import OPENAI_API_KEY


def create_flashcards_agent(model: str = "gpt-4o-mini", temperature: float = 0.3) -> ReactAgent:
    """
    Create a flashcards ReactAgent with flashcard generation tools.

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
        GenerateFlashcardsTool(model=model, temperature=temperature),
        MemoryReadTool()
    ]

    # Custom system prompt for flashcards
    system_prompt = """You are a ReAct-style flashcard generation agent that creates effective review materials.

Your goal is to generate concise, focused flashcards for spaced repetition learning.

**Your Process:**
1. First, use the "retrieve_materials" tool to find relevant course materials
2. Use the "read_memory" tool to understand student's focus areas
3. Then, use the "generate_flashcards" tool to create Q&A and cloze deletion flashcards
4. Finally, provide your Final Answer with the complete flashcard set

**Important:**
- Always retrieve materials before generating flashcards
- Create a mix of Q&A and cloze deletion formats
- Include difficulty ratings for each card
- Provide spaced repetition schedule
- If no materials are found, explain that course materials need to be uploaded

Remember: You must use tools - don't generate flashcards directly!
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
