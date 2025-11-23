"""
AnalyzeProgressTool: Tool for analyzing student progress and providing recommendations.
"""

import json
from typing import Any, Dict, List
from openai import OpenAI
from .base_tool import Tool


class AnalyzeProgressTool(Tool):
    """
    Tool for comprehensive progress analysis and recommendations.

    Analyzes quiz performance, topic mastery, and learning patterns.
    """

    name: str = "Analyze Progress"
    description: str = "Analyze student learning progress, quiz performance, and topic mastery to provide insights and recommendations"
    action_type: str = "analyze_progress"
    input_format: str = '{"user_id": "user123", "course_id": "course456", "analysis_type": "overview|detailed|recommendations"}'

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7, **data):
        super().__init__(**data)
        from agentpro_app.config import OPENAI_API_KEY
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        self.temperature = temperature

    def _calculate_mastery_trends(self, mastery_scores: Dict) -> Dict:
        """Calculate trends in mastery scores over time."""
        trends = {}

        for topic, data in mastery_scores.items():
            scores = data.get("scores", [])
            if len(scores) < 2:
                trends[topic] = "insufficient_data"
            else:
                recent_avg = sum(scores[-3:]) / len(scores[-3:])
                older_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]

                if recent_avg > older_avg + 0.1:
                    trends[topic] = "improving"
                elif recent_avg < older_avg - 0.1:
                    trends[topic] = "declining"
                else:
                    trends[topic] = "stable"

        return trends

    def _identify_learning_gaps(self, user_stats: Dict) -> List[str]:
        """Identify specific learning gaps based on quiz history."""
        gaps = []
        quiz_history = user_stats.get("quiz_history", [])
        weak_topics = user_stats.get("weak_topics", [])

        # Topics with consistently low quiz scores
        topic_performances = {}
        for quiz in quiz_history:
            topic = quiz.get("topic", "unknown")
            score = quiz.get("score", 0)
            if topic not in topic_performances:
                topic_performances[topic] = []
            topic_performances[topic].append(score)

        for topic, scores in topic_performances.items():
            avg_score = sum(scores) / len(scores)
            if avg_score < 0.6:
                gaps.append(f"{topic} (avg: {avg_score*100:.0f}%)")

        # Add weak topics not yet quizzed
        for weak in weak_topics:
            if weak not in topic_performances:
                gaps.append(f"{weak} (not yet assessed)")

        return gaps

    def _basic_analysis(self, user_stats: Dict) -> str:
        """Generate basic progress analysis without LLM."""
        weak_topics = user_stats.get("weak_topics", [])
        strong_topics = user_stats.get("strong_topics", [])
        quiz_history = user_stats.get("quiz_history", [])
        mastery_scores = user_stats.get("mastery_scores", {})

        # Calculate trends
        trends = self._calculate_mastery_trends(mastery_scores)
        gaps = self._identify_learning_gaps(user_stats)

        # Generate recommendations
        recommendations = []

        if weak_topics:
            recommendations.append(f"📚 Review weak topics: {', '.join(weak_topics[:3])}")

        if len(quiz_history) > 0:
            recent_scores = [q.get('score', 0) for q in quiz_history[-5:]]
            avg_recent = sum(recent_scores) / len(recent_scores)

            if avg_recent < 0.6:
                recommendations.append("⚠️ Quiz scores are low - consider reviewing fundamentals")
            elif avg_recent > 0.85:
                recommendations.append("🎉 Excellent quiz performance! Try harder difficulty.")

        if strong_topics:
            recommendations.append(f"💪 Strong areas: {', '.join(strong_topics[:3])} - keep it up!")

        # Build report
        report = f"""## 📊 Progress Analysis

### 📈 Performance Summary
- **Quizzes Taken:** {len(quiz_history)}
- **Topics Mastered:** {len(strong_topics)}
- **Topics to Review:** {len(weak_topics)}

### 🎯 Mastery Status
"""

        if mastery_scores:
            for topic, data in list(mastery_scores.items())[:5]:
                avg = data.get("avg", 0.0)
                trend = trends.get(topic, "stable")
                emoji = "📈" if trend == "improving" else "📉" if trend == "declining" else "➡️"
                status = "🟢" if avg > 0.7 else "🟡" if avg > 0.5 else "🔴"
                report += f"- {status} **{topic}:** {avg*100:.0f}% {emoji}\n"
        else:
            report += "- No mastery data yet - take some quizzes to get started!\n"

        if gaps:
            report += f"\n### 🔍 Learning Gaps\n"
            for gap in gaps[:5]:
                report += f"- {gap}\n"

        report += f"\n### 💡 Recommendations\n"
        for rec in recommendations:
            report += f"- {rec}\n"

        return report

    def _detailed_analysis(self, user_stats: Dict) -> str:
        """Generate detailed analysis with LLM insights."""
        # First get basic analysis
        basic = self._basic_analysis(user_stats)

        # Prepare context for LLM
        context = json.dumps({
            "weak_topics": user_stats.get("weak_topics", []),
            "strong_topics": user_stats.get("strong_topics", []),
            "quiz_history": user_stats.get("quiz_history", [])[-10:],  # Last 10 quizzes
            "mastery_scores": user_stats.get("mastery_scores", {})
        }, indent=2)

        system = """You are an expert learning coach analyzing student progress.

Provide:
1. Detailed insights into learning patterns
2. Specific recommendations for improvement
3. Actionable next steps
4. Motivational feedback

Keep your analysis concise but insightful. Focus on actionable advice."""

        user = f"""Analyze this student's learning progress and provide personalized recommendations:

{context}

Generate detailed insights and recommendations."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=self.temperature,
                max_tokens=512
            )

            llm_insights = response.choices[0].message.content

            return f"{basic}\n\n### 🤖 AI Insights\n{llm_insights}"

        except Exception as e:
            return f"{basic}\n\n_Note: Could not generate AI insights: {str(e)}_"

    def run(self, input_data: Any) -> str:
        """
        Analyze student progress.

        Args:
            input_data: Dict with user_id, course_id, analysis_type

        Returns:
            Markdown-formatted progress analysis
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return "ERROR: Invalid input format"

            user_id = params.get("user_id")
            course_id = params.get("course_id")
            analysis_type = params.get("analysis_type", "overview")

            if not all([user_id, course_id]):
                return "ERROR: Missing required fields: user_id, course_id"

            # Load user stats from database
            from agentpro_app.persistence.database import Database
            db = Database()
            user_stats = db.get_stats(user_id, course_id)

            # Generate analysis based on type
            if analysis_type == "detailed" or analysis_type == "recommendations":
                return self._detailed_analysis(user_stats)
            else:
                return self._basic_analysis(user_stats)

        except Exception as e:
            return f"ERROR: Failed to analyze progress: {str(e)}"
