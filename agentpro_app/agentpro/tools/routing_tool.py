"""
RoutingTool: LLM-based intelligent routing tool for agent selection.

This tool replaces rule-based routing with LLM-powered decision making.
"""

import json
from typing import Any, Dict
from openai import OpenAI
from .base_tool import Tool


class RoutingTool(Tool):
    """
    LLM-based routing tool that decides which agent should handle a request.

    Uses retrieval results, query content, mode, and memory to intelligently
    route to the appropriate specialized agent.
    """

    name: str = "Route Request"
    description: str = "Intelligently route user requests to the appropriate specialized agent (tutor, quiz_coach, planner, flashcards) based on query, context, and user needs"
    action_type: str = "route"
    input_format: str = '{"query": "user query", "mode": "guide|quiz|plan|flashcards", "context_summary": "...", "user_stats": {...}}'

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2, **data):
        super().__init__(**data)
        from agentpro_app.config import OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.temperature = temperature  # Low temperature for consistent routing

    def run(self, input_data: Any) -> str:
        """
        Route request to appropriate agent using LLM.

        Args:
            input_data: Dict with query, mode (optional), context_summary, user_stats

        Returns:
            JSON string with routing decision: {"agent": "tutor|quiz_coach|planner|flashcards", "reasoning": "..."}
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return json.dumps({"error": "Invalid input format"})

            query = params.get("query", "")
            mode = params.get("mode", "")
            context_summary = params.get("context_summary", "")
            user_stats = params.get("user_stats", {})

            if not query:
                return json.dumps({"error": "Missing required field 'query'"})

            # Build context for routing decision
            weak_topics = user_stats.get("weak_topics", [])
            strong_topics = user_stats.get("strong_topics", [])
            quiz_history = user_stats.get("quiz_history", [])

            context = f"""**Query:** {query}

**Mode:** {mode if mode else "Not specified"}

**Available Context:** {context_summary if context_summary else "No materials retrieved"}

**User Profile:**
- Weak Topics: {', '.join(weak_topics) if weak_topics else 'None identified'}
- Strong Topics: {', '.join(strong_topics) if strong_topics else 'None identified'}
- Quizzes Taken: {len(quiz_history)}
"""

            # System prompt for routing
            system = """You are an intelligent routing agent for StudyBuddy, an AI tutoring system.

Your job is to analyze user requests and route them to the most appropriate specialized agent:

**Available Agents:**

1. **tutor** - Study Guide & Explanation Agent
   - Use for: Explanations, learning new concepts, clarifications, general Q&A
   - Generates: Comprehensive study guides with citations, examples, and practice questions
   - Best when: User wants to understand or learn something

2. **quiz_coach** - Adaptive Quiz Generation Agent
   - Use for: Assessment, testing knowledge, practice questions
   - Generates: Adaptive quizzes with multiple question types and answer keys
   - Best when: User wants to test their knowledge or practice

3. **planner** - Study Planning & Scheduling Agent
   - Use for: Study plans, schedules, time management, preparation strategies
   - Generates: Weekly schedules with spaced repetition and prioritized topics
   - Best when: User wants to plan their studying or needs a schedule

4. **flashcards** - Flashcard Generation Agent
   - Use for: Memorization, spaced repetition, quick review materials
   - Generates: Q&A and cloze deletion flashcards with review schedules
   - Best when: User wants flashcards or quick review materials

**Routing Guidelines:**
- If mode is specified (guide, quiz, plan, flashcards), strongly prefer the corresponding agent
- Consider query keywords: "explain", "how" → tutor; "quiz", "test" → quiz_coach; "plan", "schedule" → planner; "flashcard", "memorize" → flashcards
- Consider context: If user has many weak topics and asks a vague question, planner might help
- Default to tutor for general questions

**Output Format:**
Respond with ONLY a JSON object:
{
  "agent": "tutor|quiz_coach|planner|flashcards",
  "reasoning": "Brief explanation of why this agent was chosen"
}
"""

            user = f"""Route this request to the appropriate agent:

{context}

Decide which agent should handle this request."""

            # Call LLM for routing decision
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.temperature,
                max_tokens=150
            )

            result = response.choices[0].message.content.strip()

            # Try to parse JSON response
            try:
                # Extract JSON if wrapped in markdown
                if "```json" in result:
                    result = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    result = result.split("```")[1].split("```")[0].strip()

                routing_decision = json.loads(result)

                # Validate agent choice
                valid_agents = ["tutor", "quiz_coach", "planner", "flashcards"]
                if routing_decision.get("agent") not in valid_agents:
                    routing_decision["agent"] = "tutor"  # Default fallback

                return json.dumps(routing_decision, indent=2)

            except json.JSONDecodeError:
                # Fallback: parse text response
                agent = "tutor"  # Default
                if "quiz_coach" in result.lower() or "quiz" in result.lower():
                    agent = "quiz_coach"
                elif "planner" in result.lower() or "plan" in result.lower():
                    agent = "planner"
                elif "flashcards" in result.lower() or "flashcard" in result.lower():
                    agent = "flashcards"

                return json.dumps({
                    "agent": agent,
                    "reasoning": "Fallback routing based on text analysis"
                })

        except Exception as e:
            # Emergency fallback
            return json.dumps({
                "agent": "tutor",
                "reasoning": f"Error in routing, defaulting to tutor: {str(e)}"
            })
