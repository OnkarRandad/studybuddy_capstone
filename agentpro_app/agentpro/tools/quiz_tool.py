"""
GenerateQuizTool: LLM-based tool for generating adaptive quizzes.
"""

import json
from typing import Any, Dict, List
from openai import OpenAI
from .base_tool import Tool


class GenerateQuizTool(Tool):
    """
    Tool for generating adaptive quizzes with answer keys and rationales.

    Supports multiple question types and difficulty levels.
    """

    name: str = "Generate Quiz"
    description: str = "Generate an adaptive quiz with multiple question types, answer keys, and detailed rationales"
    action_type: str = "generate_quiz"
    input_format: str = '{"query": "topic", "context": [...], "difficulty": "easy|medium|hard", "num_questions": 6, "user_stats": {...}}'

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4, **data):
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

    def _determine_difficulty(self, user_stats: Dict, requested_difficulty: str) -> str:
        """Determine appropriate difficulty based on user performance."""
        if requested_difficulty in ["easy", "medium", "hard"]:
            return requested_difficulty

        # Adapt based on recent quiz scores
        quiz_history = user_stats.get("quiz_history", [])
        if quiz_history:
            recent_scores = [q.get('score', 0) for q in quiz_history[-5:]]
            avg_score = sum(recent_scores) / len(recent_scores)

            if avg_score > 0.85:
                return "hard"
            elif avg_score > 0.65:
                return "medium"
            else:
                return "easy"

        return "medium"

    def run(self, input_data: Any) -> str:
        """
        Generate quiz using LLM.

        Args:
            input_data: Dict with query, context, difficulty, num_questions, user_stats

        Returns:
            Markdown-formatted quiz with answer key
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
            difficulty = params.get("difficulty", "medium")
            num_questions = params.get("num_questions", 6)
            user_stats = params.get("user_stats", {})

            if not query:
                return "ERROR: Missing required field 'query'"

            if not context:
                return "**Cannot generate quiz - no relevant materials found.**\n\nPlease upload course materials first."

            # Adapt difficulty
            difficulty = self._determine_difficulty(user_stats, difficulty)

            # Format context
            ctx = self._format_context(context)

            # Build personalization
            weak_topics = user_stats.get("weak_topics", [])
            focus = ""
            if weak_topics:
                focus = f"\n- Focus extra questions on weak areas: {', '.join(weak_topics[:3])}"

            # System prompt
            system = f"""You are an expert educator creating assessments.

**Instructions:**
1. Generate {num_questions} questions at {difficulty} difficulty
2. Mix question types: Multiple Choice, True/False, Short Answer
3. Include answer key with detailed rationales
4. Cite page numbers for each question's source
5. Ensure questions test understanding, not just recall{focus}

**Output Format:**
## Quiz: [Topic]

### Question 1 (Multiple Choice)
**Q:** [Question text] _(Source, p.X)_

A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

### Question 2 (True/False)
**Q:** [Statement] _(Source, p.Y)_

### Question 3 (Short Answer)
**Q:** [Question requiring 2-3 sentence response] _(Source, p.Z)_

---

## Answer Key

**Q1:** B - [Detailed rationale explaining why B is correct and others are wrong] _(p.X)_

**Q2:** False - [Explanation with reasoning] _(p.Y)_

**Q3:** [Sample answer with key points] _(p.Z)_
"""

            user = f"""Create a {difficulty} quiz on: **{query}**

**Context:**
{ctx}

Generate {num_questions} varied questions with complete answer key."""

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

            content = response.choices[0].message.content

            # Add metadata footer
            footer = f"\n\n---\n**Difficulty:** {difficulty} | **Questions:** {num_questions}"

            return content + footer

        except Exception as e:
            return f"ERROR: Failed to generate quiz: {str(e)}"
