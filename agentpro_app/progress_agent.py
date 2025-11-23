"""
ProgressAgent - An AgentPro tool for analyzing student progress and providing recommendations.

This agent uses the ReAct pattern to:
1. Analyze user memory and quiz history
2. Identify weak/strong topics
3. Generate personalized recommendations
4. Track mastery progression over time
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from agentpro.tools import Tool
from openai import OpenAI
from agentpro_app.config import CHAT_MODEL, OPENAI_API_KEY

# Replace direct os.getenv calls
client = OpenAI(api_key=OPENAI_API_KEY)

# Debug print for model
print("[DEBUG] Using model:", CHAT_MODEL)


class ProgressAgentTool(Tool):
    """
    AgentPro tool for comprehensive progress analysis and recommendations.
    
    Can be called by the main ReactAgent to analyze student performance,
    identify learning gaps, and suggest next steps.
    """
    
    name: str = "Progress Analysis Agent"
    description: str = (
        "Analyzes student learning progress, quiz performance, and topic mastery. "
        "Returns insights, recommendations, and personalized study suggestions based on "
        "historical data including quiz scores, query patterns, and weak/strong topics."
    )
    action_type: str = "analyze_progress"
    input_format: str = (
        "JSON object with: {\"user_id\": str, \"course_id\": str, \"analysis_type\": str}. "
        "analysis_type can be: 'overview', 'detailed', 'recommendations', 'mastery_check'"
    )
    
    def __init__(self):
        super().__init__()
        # Import memory module dynamically to avoid circular imports
        from . import memory as mem
        self.mem = mem
    
    def _load_user_data(self, user_id: str, course_id: str) -> Dict:
        """Load all user data from memory."""
        return self.mem.load(user_id, course_id)
    
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
    
    def _identify_learning_gaps(self, memory: Dict) -> List[str]:
        """Identify specific learning gaps based on quiz history and queries."""
        gaps = []
        quiz_history = memory.get("quiz_history", [])
        weak_topics = memory.get("weak_topics", [])
        
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
    
    def _generate_recommendations(self, memory: Dict, analysis_type: str) -> List[str]:
        """Generate personalized recommendations using LLM."""
        weak_topics = memory.get("weak_topics", [])
        strong_topics = memory.get("strong_topics", [])
        quiz_history = memory.get("quiz_history", [])
        last_queries = memory.get("last_queries", [])
        mastery_scores = memory.get("mastery_scores", {})
        
        # Prepare context for LLM
        context = {
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "total_quizzes": len(quiz_history),
            "recent_queries_count": len(last_queries),
            "mastery_scores": {k: v.get("avg", 0) for k, v in mastery_scores.items()}
        }
        
        if quiz_history:
            recent_scores = [q.get("score", 0) for q in quiz_history[-5:]]
            context["recent_avg_score"] = sum(recent_scores) / len(recent_scores)
        
        system_prompt = """You are an expert learning coach analyzing student progress.
Generate 3-5 specific, actionable recommendations based on the student's data.

Focus on:
1. Addressing weak topics with concrete study strategies
2. Building on strong topics to maintain momentum
3. Optimizing study patterns and quiz timing
4. Suggesting difficulty progressions

Be encouraging but honest. Provide specific action items."""
        
        user_prompt = f"""Analyze this student's progress and provide recommendations:

**Student Data:**
{json.dumps(context, indent=2)}

**Analysis Type:** {analysis_type}

Generate 3-5 specific, actionable recommendations."""
        
        try:
            response = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=512
            )
            
            # Parse recommendations from response
            recommendations_text = response.choices[0].message.content
            recommendations = [
                line.strip().lstrip("0123456789.-) ")
                for line in recommendations_text.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
            
            return recommendations[:5]  # Limit to 5
            
        except Exception as e:
            # Fallback to rule-based recommendations
            return self._fallback_recommendations(memory)
    
    def _fallback_recommendations(self, memory: Dict) -> List[str]:
        """Rule-based recommendations as fallback."""
        recs = []
        weak_topics = memory.get("weak_topics", [])
        strong_topics = memory.get("strong_topics", [])
        quiz_history = memory.get("quiz_history", [])
        
        if weak_topics:
            recs.append(f"📚 Focus on weak topics: {', '.join(weak_topics[:2])}")
        
        if len(quiz_history) < 3:
            recs.append("🎯 Take more quizzes to identify knowledge gaps")
        
        if strong_topics:
            recs.append(f"💪 Maintain strength in: {', '.join(strong_topics[:2])}")
        
        if len(memory.get("last_queries", [])) < 5:
            recs.append("🔥 Increase study frequency for better retention")
        
        recs.append("✨ Use spaced repetition with flashcards for long-term retention")
        
        return recs
    
    def _calculate_next_steps(self, memory: Dict) -> List[Dict]:
        """Calculate specific next steps for the student."""
        next_steps = []
        weak_topics = memory.get("weak_topics", [])
        quiz_history = memory.get("quiz_history", [])
        last_queries = memory.get("last_queries", [])
        
        # Priority 1: Address weak topics
        if weak_topics:
            next_steps.append({
                "priority": "high",
                "action": f"Review study guide for: {weak_topics[0]}",
                "type": "review",
                "topic": weak_topics[0]
            })
            
            if len(weak_topics) > 1:
                next_steps.append({
                    "priority": "high",
                    "action": f"Complete quiz on: {weak_topics[1]}",
                    "type": "quiz",
                    "topic": weak_topics[1]
                })
        
        # Priority 2: Practice recent topics
        if last_queries:
            recent_topics = set()
            for q in last_queries[-3:]:
                if isinstance(q, dict):
                    query_text = q.get("query", "")
                    # Extract main topic (simplified)
                    words = query_text.split()
                    if words:
                        recent_topics.add(words[0])
            
            for topic in list(recent_topics)[:2]:
                next_steps.append({
                    "priority": "medium",
                    "action": f"Create flashcards for: {topic}",
                    "type": "flashcards",
                    "topic": topic
                })
        
        # Priority 3: Regular review
        if not next_steps:
            next_steps.append({
                "priority": "medium",
                "action": "Explore course materials and identify topics to study",
                "type": "exploration"
            })
        
        return next_steps[:5]  # Limit to 5 steps
    
    def run(self, input_text: Any) -> str:
        """
        Main execution method for the ProgressAgent tool.
        
        Input: JSON string with user_id, course_id, and analysis_type
        Output: JSON string with progress analysis and recommendations
        """
        try:
            # Parse input
            if isinstance(input_text, str):
                input_data = json.loads(input_text)
            else:
                input_data = input_text
            
            user_id = input_data.get("user_id")
            course_id = input_data.get("course_id")
            analysis_type = input_data.get("analysis_type", "overview")
            
            if not user_id or not course_id:
                return json.dumps({
                    "error": "Missing user_id or course_id",
                    "success": False
                })
            
            # Load user data
            memory = self._load_user_data(user_id, course_id)
            
            # Perform analysis based on type
            result = {
                "success": True,
                "user_id": user_id,
                "course_id": course_id,
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat()
            }
            
            if analysis_type == "overview":
                # High-level overview
                result.update({
                    "study_streak": len(memory.get("last_queries", [])),
                    "quizzes_taken": len(memory.get("quiz_history", [])),
                    "weak_topics": memory.get("weak_topics", []),
                    "strong_topics": memory.get("strong_topics", []),
                    "mastery_count": len(memory.get("strong_topics", []))
                })
            
            elif analysis_type == "detailed":
                # Detailed analysis
                mastery_scores = memory.get("mastery_scores", {})
                trends = self._calculate_mastery_trends(mastery_scores)
                gaps = self._identify_learning_gaps(memory)
                
                result.update({
                    "mastery_scores": {
                        k: {
                            "average": v.get("avg", 0),
                            "attempts": len(v.get("scores", [])),
                            "trend": trends.get(k, "unknown")
                        }
                        for k, v in mastery_scores.items()
                    },
                    "learning_gaps": gaps,
                    "total_queries": len(memory.get("last_queries", [])),
                    "quiz_history_summary": {
                        "total": len(memory.get("quiz_history", [])),
                        "recent_5_avg": sum(q.get("score", 0) for q in memory.get("quiz_history", [])[-5:]) / len(memory.get("quiz_history", [])[-5:]) if len(memory.get("quiz_history", [])) >= 5 else 0
                    }
                })
            
            elif analysis_type == "recommendations":
                # Generate recommendations
                recommendations = self._generate_recommendations(memory, analysis_type)
                next_steps = self._calculate_next_steps(memory)
                
                result.update({
                    "recommendations": recommendations,
                    "next_steps": next_steps,
                    "priority_topics": memory.get("weak_topics", [])[:3]
                })
            
            elif analysis_type == "mastery_check":
                # Check mastery levels
                mastery_scores = memory.get("mastery_scores", {})
                mastery_report = []
                
                for topic, data in mastery_scores.items():
                    avg = data.get("avg", 0)
                    if avg >= 0.8:
                        level = "Mastered"
                        emoji = "🟢"
                    elif avg >= 0.6:
                        level = "Proficient"
                        emoji = "🟡"
                    else:
                        level = "Needs Review"
                        emoji = "🔴"
                    
                    mastery_report.append({
                        "topic": topic,
                        "level": level,
                        "score": avg,
                        "emoji": emoji,
                        "attempts": len(data.get("scores", []))
                    })
                
                result.update({
                    "mastery_report": mastery_report,
                    "summary": {
                        "mastered": len([r for r in mastery_report if r["level"] == "Mastered"]),
                        "proficient": len([r for r in mastery_report if r["level"] == "Proficient"]),
                        "needs_review": len([r for r in mastery_report if r["level"] == "Needs Review"])
                    }
                })
            
            return json.dumps(result, indent=2)
        
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": f"Invalid JSON input: {str(e)}",
                "success": False
            })
        except Exception as e:
            return json.dumps({
                "error": f"Progress analysis failed: {str(e)}",
                "success": False
            })


# Example usage with AgentPro
if __name__ == "__main__":
    from agentpro import ReactAgent, create_model
    
    # Create model
    model = create_model(
        provider="openai",
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Initialize tools
    tools = [ProgressAgentTool()]
    
    # Create agent
    agent = ReactAgent(
        model=model,
        tools=tools,
        max_iterations=10
    )
    
    # Example query
    query = """Analyze the progress for user 'student123' in course 'cs101'. 
    I want a detailed analysis with recommendations."""
    
    response = agent.run(query)
    print(f"\n{response.final_answer}")