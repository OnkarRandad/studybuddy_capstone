"""
CreateStudyPlanTool: LLM-based tool for generating personalized study plans.
"""

import json
from typing import Any, Dict
from datetime import datetime, timedelta
from openai import OpenAI
from .base_tool import Tool


class CreateStudyPlanTool(Tool):
    """
    Tool for creating personalized study plans with spaced repetition.

    Considers user's weak/strong topics, deadlines, and study preferences.
    """

    name: str = "Create Study Plan"
    description: str = "Generate a personalized study plan with weekly schedules, spaced repetition, and prioritized focus areas"
    action_type: str = "create_study_plan"
    input_format: str = '{"query": "study plan request", "user_stats": {...}, "deadline": "YYYY-MM-DD", "hours_per_day": 2}'

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.4, **data):
        super().__init__(**data)
        from agentpro_app.config import OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.temperature = temperature

    def run(self, input_data: Any) -> str:
        """
        Generate study plan using LLM.

        Args:
            input_data: Dict with query, user_stats, deadline, hours_per_day

        Returns:
            Markdown-formatted study plan with weekly schedule
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return "ERROR: Invalid input format"

            query = params.get("query", "Create a study plan")
            user_stats = params.get("user_stats", {})
            deadline = params.get("deadline")
            hours_per_day = params.get("hours_per_day", 2)

            # Extract user data
            weak_topics = user_stats.get("weak_topics", [])
            strong_topics = user_stats.get("strong_topics", [])
            mastery_scores = user_stats.get("mastery_scores", {})
            quiz_history = user_stats.get("quiz_history", [])

            # Calculate timeline
            timeline_info = ""
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    days_until = (deadline_date - datetime.now()).days
                    weeks = max(1, days_until // 7)
                    total_hours = days_until * hours_per_day
                    timeline_info = f"\n- **Timeline:** {weeks} weeks ({days_until} days)\n- **Total Study Hours:** {total_hours} hours"
                except:
                    timeline_info = f"\n- **Daily Hours:** {hours_per_day}"
            else:
                timeline_info = f"\n- **Daily Hours:** {hours_per_day}"

            # Build context
            context = f"""**Student Profile:**
- Weak Topics: {', '.join(weak_topics) if weak_topics else 'None identified yet'}
- Strong Topics: {', '.join(strong_topics) if strong_topics else 'None identified yet'}
- Quizzes Taken: {len(quiz_history)}
{timeline_info}
"""

            # Add mastery scores if available
            if mastery_scores:
                context += "\n**Mastery Levels:**\n"
                for topic, data in list(mastery_scores.items())[:5]:
                    avg = data.get("avg", 0.0)
                    context += f"- {topic}: {avg*100:.0f}%\n"

            # System prompt
            system = """You are an expert study planner creating personalized learning schedules.

**Your Planning Philosophy:**
- Prioritize weak areas while maintaining strong areas
- Use spaced repetition for long-term retention
- Balance study load across available time
- Build in review sessions and practice tests
- Adapt to student's preferred study hours

**Planning Principles:**
1. **Prioritization**: Weak topics get 60% of time, strong topics get 20%, new topics 20%
2. **Spaced Repetition**: Review at 1 day, 3 days, 1 week, 2 weeks intervals
3. **Active Practice**: 50% reading/study, 30% practice, 20% testing
4. **Realistic Load**: Don't overload - sustainable progress beats burnout
5. **Flexibility**: Build buffer time for adjustments

**Output Format:**
## 📘 Study Plan: [Course/Topic]

### 🎯 Goals & Timeline
- **Target Date:** [Deadline or milestone]
- **Total Study Hours:** [Calculated]
- **Daily Commitment:** [Hours per day]

### 📊 Priority Assessment
**Focus Areas (60% of time):**
1. [Weak topic 1] - Current mastery: X%
2. [Weak topic 2] - Current mastery: Y%

**Maintenance Areas (20% of time):**
- [Strong topics to maintain]

**New Material (20% of time):**
- [Upcoming topics or advanced concepts]

### 📆 Weekly Schedule

#### Week 1: Foundations
**Monday (2 hours)**
- 0:00-0:45 → Study [Topic A]
- 0:45-1:15 → Practice problems on [Topic A]
- 1:15-1:45 → Flashcard review
- 1:45-2:00 → Quick quiz on [Topic A]

**Tuesday (2 hours)**
[Similar breakdown]

[Continue for full week]

#### Week 2: Building & Review
[Next week's focus]

### 🔁 Review Schedule (Spaced Repetition)
- **Day 1:** [Topics covered today]
- **Day 3:** Review [Topics from Day 1]
- **Day 7:** Review [Topics from Day 1-3]
- **Day 14:** Review [All Week 1 topics]

### ✅ Daily Checklist Template
- [ ] Complete scheduled study session
- [ ] Review flashcards (15 min)
- [ ] Practice problems (30 min)
- [ ] Quick self-quiz
- [ ] Log progress in StudyBuddy

### 📈 Progress Checkpoints
- **End of Week 1:** Take practice quiz on [Topics]
- **End of Week 2:** Take comprehensive quiz
- **Midpoint:** Review plan and adjust priorities

### 💡 Study Tips
[Personalized based on performance patterns]
"""

            user = f"""Create a personalized study plan.

**Request:** {query}

{context}

Generate a comprehensive, actionable study plan with daily schedules and spaced repetition."""

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.temperature,
                max_tokens=2500
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"ERROR: Failed to create study plan: {str(e)}"
