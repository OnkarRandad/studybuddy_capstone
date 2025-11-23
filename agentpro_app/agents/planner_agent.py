"""
PlannerAgent: Generates personalized study plans and schedules.
Considers deadlines, weak topics, and study patterns.
"""

from .base import BaseAgent, AgentRole, AgentContext, AgentResponse
from datetime import datetime, timedelta
from typing import Dict, List


class PlannerAgent(BaseAgent):
    """Agent specialized in study planning and scheduling."""
    
    def __init__(self, model: str = None):
        super().__init__(AgentRole.PLANNER, model)
    
    def _build_system_prompt(self) -> str:
        return """You are an expert study planner creating personalized learning schedules.

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
## 📘 Study Plan: [Course Name]

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
- 0:00-0:45 → Study [Topic A] from [Source, p.X-Y]
- 0:45-1:15 → Practice problems on [Topic A]
- 1:15-1:45 → Flashcard review (previous topics)
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
- **End of Week 1:** Take practice quiz on [Topic A, B]
- **End of Week 2:** Take comprehensive quiz
- **Midpoint:** Review plan and adjust priorities

### 💡 Study Tips for Your Learning Style
[Personalized based on performance patterns]
"""
    
    def can_handle(self, context: AgentContext) -> bool:
        """Planner handles plan generation requests."""
        return (
            context.mode == 'plan' or
            'plan' in context.query.lower() or
            'schedule' in context.query.lower()
        )
    
    async def process(self, context: AgentContext) -> AgentResponse:
        """Generate a personalized study plan."""
        
        stats = context.user_stats
        deadline = context.metadata.get('deadline')
        hours_per_day = context.metadata.get('hours_per_day', 2)
        
        if deadline:
            days_until = self._calculate_days_until(deadline)
        else:
            days_until = 30
        
        total_hours = days_until * hours_per_day
        planning_data = self._build_planning_data(stats, total_hours)
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Create a study plan for: **{context.query}**

**Timeline:**
- Days available: {days_until}
- Hours per day: {hours_per_day}
- Total study hours: {total_hours}

**Student Performance:**
{planning_data}

Generate a detailed, week-by-week study plan with daily schedules and review cycles."""}
        ]
        
        response = self._call_llm(messages, temperature=0.4, max_tokens=2500)
        content = response.choices[0].message.content
        content = self._enhance_with_schedule(content, stats, days_until, hours_per_day)
        
        return AgentResponse(
            content=content,
            agent_role=self.role,
            citations=[],
            metadata={
                "days_until": days_until,
                "hours_per_day": hours_per_day,
                "total_hours": total_hours,
                "mode": "plan"
            },
            confidence=0.9
        )
    
    def _build_planning_data(self, stats: Dict, total_hours: int) -> str:
        parts = []
        weak = stats.get('weak_topics', [])
        if weak:
            weak_hours = int(total_hours * 0.6)
            parts.append(f"**Focus Areas ({weak_hours}h / 60%):**")
            mastery = stats.get('mastery_scores', {})
            for topic in weak[:3]:
                score = mastery.get(topic, {}).get('avg', 0.0)
                parts.append(f"- {topic}: {score*100:.0f}% mastery")
        
        strong = stats.get('strong_topics', [])
        if strong:
            strong_hours = int(total_hours * 0.2)
            parts.append(f"\n**Maintenance Areas ({strong_hours}h / 20%):**")
            for topic in strong[:3]:
                score = mastery.get(topic, {}).get('avg', 0.0)
                parts.append(f"- {topic}: {score*100:.0f}% mastery")
        
        streak = stats.get('study_streak', 0)
        queries = stats.get('total_queries', 0)
        parts.append(f"\n**Study Patterns:**")
        parts.append(f"- Current streak: {streak} sessions")
        parts.append(f"- Total queries: {queries}")
        trend = stats.get('recent_trend', 'stable')
        avg_score = stats.get('avg_quiz_score', 0.0)
        parts.append(f"- Recent trend: {trend}")
        parts.append(f"- Average quiz score: {avg_score*100:.0f}%")
        
        return "\n".join(parts)
    
    def _calculate_days_until(self, deadline_str: str) -> int:
        try:
            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            now = datetime.now()
            delta = deadline - now
            return max(1, delta.days)
        except:
            return 30
    
    def _enhance_with_schedule(self, content: str, stats: Dict, days: int, hours_per_day: int) -> str:
        weak_topics = stats.get('weak_topics', [])
        strong_topics = stats.get('strong_topics', [])
        
        schedule_template = "\n\n---\n\n### 🧠 Smart Task Distribution\n\n"
        
        if weak_topics:
            schedule_template += f"**Primary Focus (First {hours_per_day * 0.6:.0f} hours daily):**\n"
            for i, topic in enumerate(weak_topics[:2], 1):
                schedule_template += f"{i}. {topic} - Deep study with examples and practice\n"
        
        if strong_topics:
            schedule_template += f"\n**Maintenance Review ({hours_per_day * 0.2:.0f} hours daily):**\n"
            schedule_template += f"- Quick review of {', '.join(strong_topics[:2])}\n"
        
        schedule_template += f"\n**Testing & Practice ({hours_per_day * 0.2:.0f} hours daily):**\n"
        schedule_template += "- Take quizzes to identify gaps\n"
        schedule_template += "- Flashcard sessions for retention\n"
        
        return content + schedule_template
