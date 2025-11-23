"""
GenerateFlashcardsTool: LLM-based tool for generating spaced-repetition flashcards.
"""

import json
from typing import Any, Dict, List
from openai import OpenAI
from .base_tool import Tool


class GenerateFlashcardsTool(Tool):
    """
    Tool for generating flashcards with spaced repetition schedules.

    Creates both Q&A and cloze deletion formats.
    """

    name: str = "Generate Flashcards"
    description: str = "Generate spaced-repetition flashcards in Q&A and cloze deletion formats with difficulty ratings"
    action_type: str = "generate_flashcards"
    input_format: str = '{"query": "topic", "context": [...], "num_cards": 10}'

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3, **data):
        super().__init__(**data)
        from agentpro_app.config import OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.temperature = temperature

    def _format_context(self, context: List[Dict]) -> str:
        """Format context for LLM prompt."""
        formatted = []
        for i, ctx in enumerate(context, 1):
            title = ctx.get('title', 'Document')
            page = ctx.get('page', '?')
            text = ctx.get('text', '')
            score = ctx.get('score', 0.0)

            formatted.append(
                f"[{i}] ({title}, p.{page}, relevance: {score:.2f})\n{text}\n"
            )
        return "\n".join(formatted)

    def run(self, input_data: Any) -> str:
        """
        Generate flashcards using LLM.

        Args:
            input_data: Dict with query, context, num_cards

        Returns:
            Markdown-formatted flashcards with spaced repetition schedule
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return "ERROR: Invalid input format"

            query = params.get("query")
            context = params.get("context", [])
            num_cards = params.get("num_cards", 10)

            if not query:
                return "ERROR: Missing required field 'query'"

            if not context:
                return "**Cannot generate flashcards - no relevant materials found.**"

            # Format context
            ctx = self._format_context(context)

            # System prompt
            system = """You are creating flashcards for spaced repetition learning.

**Instructions:**
1. Create concise, focused flashcards (one concept per card)
2. Use two formats:
   - **Q&A**: Question on front, answer on back
   - **Cloze**: Fill-in-the-blank style with {{c1::answer}}
3. Include page citations
4. Tag each card with concept keywords
5. Rate difficulty (1-5 scale, 1=easiest)

**Output Format:**
## Flashcard Set: [Topic]

### Card 1 (Q&A)
**Front:** [Clear, specific question]
**Back:** [Concise answer with brief explanation]
**Tags:** #concept1 #concept2
**Difficulty:** 2/5
**Source:** (Title, p.X)

---

### Card 2 (Cloze)
**Text:** The {{c1::base case}} prevents infinite recursion by providing a {{c2::termination condition}}.
**Tags:** #recursion #fundamentals
**Difficulty:** 1/5
**Source:** (Title, p.Y)

---

## Spaced Repetition Schedule
- **Today (Day 1):** Review all cards
- **Day 3:** Review cards 1, 3, 5, 7, 9
- **Day 7:** Review cards with difficulty 3+
- **Day 14:** Review all cards again
"""

            user = f"""Create {num_cards} flashcards for: **{query}**

**Context:**
{ctx}

Generate varied flashcards (mix Q&A and cloze formats). Focus on key concepts and testable knowledge."""

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.temperature,
                max_tokens=2048
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"ERROR: Failed to generate flashcards: {str(e)}"
