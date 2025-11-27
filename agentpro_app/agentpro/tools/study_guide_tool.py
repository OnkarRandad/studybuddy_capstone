"""
GenerateStudyGuideTool: LLM-based tool for generating comprehensive study guides.
"""

import json
from typing import Any, Dict, List
from openai import OpenAI
from .base_tool import Tool


class GenerateStudyGuideTool(Tool):
    """
    Tool for generating comprehensive, citation-rich study guides.

    Uses LLM to create structured explanations with examples and practice questions.
    """

    name: str = "Generate Study Guide"
    description: str = "Generate a comprehensive study guide with explanations, examples, key takeaways, and practice questions"
    action_type: str = "generate_study_guide"
    input_format: str = '{"query": "topic to explain", "context": [{"text": "...", "title": "...", "page": "..."}], "user_stats": {...}}'

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
        Generate study guide using LLM.

        Args:
            input_data: Dict with query, context (list of retrieved materials), user_stats (optional)

        Returns:
            Markdown-formatted study guide
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return "ERROR: Invalid input format. Expected dict or JSON string"

            query = params.get("query")
            context = params.get("context", [])
            user_stats = params.get("user_stats", {})

            if not query:
                return "ERROR: Missing required field 'query'"

            if not context:
                return "**No relevant materials found.**\n\nPlease upload course materials or try rephrasing your question."

            # Format context
            ctx = self._format_context(context)

            # Build personalization context
            personalization = ""
            weak_topics = user_stats.get("weak_topics", [])
            strong_topics = user_stats.get("strong_topics", [])

            if weak_topics:
                personalization += f"\n- User struggles with: {', '.join(weak_topics[:3])}"
            if strong_topics:
                personalization += f"\n- User is strong in: {', '.join(strong_topics[:3])}"

            # System prompt
            system = f"""You are an expert tutor creating comprehensive study guides.

**Instructions:**
1. Create well-structured, clear explanations with examples
2. Use bullet points, headings, and formatting for readability
3. Cite sources inline using format: (Title, p.X) after each claim
4. Include "Key Takeaways" and "Practice Questions" sections
5. If context is insufficient, note what's missing
{personalization}

**Format:**
## Topic Overview
[explanation with citations]

## Key Concepts
- Concept 1 (Source, p.X)
- Concept 2 (Source, p.Y)

## Examples
[worked examples]

## Key Takeaways
[summary bullets]

## Practice Questions
[2-3 questions to test understanding]
"""

            user = f"""Create a study guide for: **{query}**

**Context from course materials:**
{ctx}

Generate a complete, citation-rich study guide."""

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
            return f"ERROR: Failed to generate study guide: {str(e)}"
