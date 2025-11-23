"""
Memory management for StudyBuddy.
Stores user progress, quiz history, mastery tracking, and study patterns.
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime

MEM_DIR = os.path.join(os.path.dirname(__file__), "memory")
os.makedirs(MEM_DIR, exist_ok=True)

def _path(user_id: str, course_id: str) -> str:
    """Generate file path for user+course memory."""
    safe = f"{user_id}__{course_id}".replace("/", "_").replace("\\", "_")
    return os.path.join(MEM_DIR, f"{safe}.json")

def load(user_id: str, course_id: str) -> Dict:
    """
    Load user memory with complete structure.
    Returns default structure if file doesn't exist.
    """
    p = _path(user_id, course_id)
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupt file, return default
            pass
    
    # Default structure
    return {
        "goals": [],
        "weak_topics": [],
        "strong_topics": [],
        "last_queries": [],
        "quiz_history": [],
        "mastery_scores": {},  # {topic: {scores: [], avg: float}}
        "next_actions": [],
        "study_streak": 0,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "preferences": {
            "difficulty": "medium",
            "study_hours_per_day": 2
        }
    }

def save(user_id: str, course_id: str, data: Dict) -> None:
    """Save user memory with timestamp."""
    data["last_updated"] = datetime.now().isoformat()
    with open(_path(user_id, course_id), "w") as f:
        json.dump(data, f, indent=2)

def log_query(user_id: str, course_id: str, query: str, mode: str) -> None:
    """
    Log a query to memory with timestamp and mode.
    Keeps last 20 queries.
    """
    m = load(user_id, course_id)
    
    query_entry = {
        "query": query,
        "mode": mode,
        "timestamp": datetime.now().isoformat()
    }
    
    m["last_queries"] = (m.get("last_queries", []) + [query_entry])[-20:]
    m["study_streak"] = m.get("study_streak", 0) + 1
    
    save(user_id, course_id, m)

def log_quiz_attempt(
    user_id: str, 
    course_id: str, 
    topic: str, 
    score: float, 
    total_questions: int,
    difficulty: str,
    answers: Optional[List[Dict]] = None
) -> None:
    """
    Log a quiz attempt and update mastery tracking.
    
    Args:
        user_id: User identifier
        course_id: Course identifier
        topic: Topic being quizzed
        score: Score as float between 0.0 and 1.0
        total_questions: Total number of questions
        difficulty: Quiz difficulty (easy/medium/hard)
        answers: Optional detailed answers for review
    """
    m = load(user_id, course_id)
    
    # Create quiz attempt entry
    attempt = {
        "topic": topic,
        "score": score,
        "total_questions": total_questions,
        "difficulty": difficulty,
        "timestamp": datetime.now().isoformat()
    }
    
    if answers:
        attempt["answers"] = answers
    
    # Add to history (keep last 50)
    m["quiz_history"] = (m.get("quiz_history", []) + [attempt])[-50:]
    
    # Update mastery scores
    if topic not in m["mastery_scores"]:
        m["mastery_scores"][topic] = {
            "scores": [],
            "avg": 0.0,
            "first_attempt": datetime.now().isoformat(),
            "last_attempt": datetime.now().isoformat()
        }
    
    m["mastery_scores"][topic]["scores"].append(score)
    m["mastery_scores"][topic]["scores"] = m["mastery_scores"][topic]["scores"][-10:]  # Keep last 10
    m["mastery_scores"][topic]["avg"] = sum(
        m["mastery_scores"][topic]["scores"]
    ) / len(m["mastery_scores"][topic]["scores"])
    m["mastery_scores"][topic]["last_attempt"] = datetime.now().isoformat()
    
    # Update weak/strong topics based on mastery
    avg_score = m["mastery_scores"][topic]["avg"]
    
    if avg_score < 0.6:
        # Weak topic
        if topic not in m["weak_topics"]:
            m["weak_topics"].append(topic)
        # Remove from strong if it was there
        if topic in m.get("strong_topics", []):
            m["strong_topics"].remove(topic)
    
    elif avg_score > 0.8:
        # Strong topic
        if topic not in m.get("strong_topics", []):
            m["strong_topics"] = m.get("strong_topics", []) + [topic]
        # Remove from weak if it was there
        if topic in m["weak_topics"]:
            m["weak_topics"].remove(topic)
    
    else:
        # Moderate - remove from both lists
        if topic in m["weak_topics"]:
            m["weak_topics"].remove(topic)
        if topic in m.get("strong_topics", []):
            m["strong_topics"].remove(topic)
    
    save(user_id, course_id, m)

def update_next_actions(
    user_id: str, 
    course_id: str, 
    actions: List[str]
) -> None:
    """Update the next actions list."""
    m = load(user_id, course_id)
    m["next_actions"] = actions
    save(user_id, course_id, m)

def add_goal(user_id: str, course_id: str, goal: str, deadline: Optional[str] = None) -> None:
    """Add a study goal."""
    m = load(user_id, course_id)
    
    goal_entry = {
        "goal": goal,
        "created": datetime.now().isoformat(),
        "deadline": deadline,
        "completed": False
    }
    
    m["goals"] = m.get("goals", []) + [goal_entry]
    save(user_id, course_id, m)

def complete_goal(user_id: str, course_id: str, goal_index: int) -> bool:
    """Mark a goal as completed."""
    m = load(user_id, course_id)
    goals = m.get("goals", [])
    
    if 0 <= goal_index < len(goals):
        goals[goal_index]["completed"] = True
        goals[goal_index]["completed_at"] = datetime.now().isoformat()
        save(user_id, course_id, m)
        return True
    
    return False

def get_stats(user_id: str, course_id: str) -> Dict:
    """
    Get comprehensive statistics for display.
    
    Returns:
        Dictionary with study_streak, total_queries, quizzes_taken,
        avg_quiz_score, weak_topics, strong_topics, mastery_scores, etc.
    """
    m = load(user_id, course_id)
    
    quiz_history = m.get("quiz_history", [])
    
    # Calculate average quiz score
    avg_quiz_score = 0.0
    if quiz_history:
        avg_quiz_score = sum(q["score"] for q in quiz_history) / len(quiz_history)
    
    # Get recent performance trend
    recent_trend = "stable"
    if len(quiz_history) >= 5:
        recent_5 = [q["score"] for q in quiz_history[-5:]]
        older_5 = [q["score"] for q in quiz_history[-10:-5]] if len(quiz_history) >= 10 else [avg_quiz_score]
        
        recent_avg = sum(recent_5) / len(recent_5)
        older_avg = sum(older_5) / len(older_5)
        
        if recent_avg > older_avg + 0.1:
            recent_trend = "improving"
        elif recent_avg < older_avg - 0.1:
            recent_trend = "declining"
    
    return {
        "study_streak": m.get("study_streak", 0),
        "total_queries": len(m.get("last_queries", [])),
        "quizzes_taken": len(quiz_history),
        "avg_quiz_score": avg_quiz_score,
        "recent_trend": recent_trend,
        "weak_topics": m.get("weak_topics", []),
        "strong_topics": m.get("strong_topics", []),
        "mastery_scores": m.get("mastery_scores", {}),
        "next_actions": m.get("next_actions", []),
        "goals": m.get("goals", []),
        "created_at": m.get("created_at"),
        "last_updated": m.get("last_updated"),
        "preferences": m.get("preferences", {})
    }

def reset_streak(user_id: str, course_id: str) -> None:
    """Reset study streak (for testing or new semester)."""
    m = load(user_id, course_id)
    m["study_streak"] = 0
    save(user_id, course_id, m)

def get_topic_history(user_id: str, course_id: str, topic: str) -> Dict:
    """
    Get detailed history for a specific topic.
    
    Returns quiz attempts, mastery progression, and recommendations.
    """
    m = load(user_id, course_id)
    
    # Filter quiz history for this topic
    topic_quizzes = [
        q for q in m.get("quiz_history", [])
        if q.get("topic", "").lower() == topic.lower()
    ]
    
    # Get mastery data
    mastery_data = m.get("mastery_scores", {}).get(topic, {})
    
    return {
        "topic": topic,
        "quiz_attempts": len(topic_quizzes),
        "quiz_history": topic_quizzes,
        "mastery": mastery_data,
        "is_weak": topic in m.get("weak_topics", []),
        "is_strong": topic in m.get("strong_topics", [])
    }

def export_data(user_id: str, course_id: str) -> Dict:
    """Export all user data (for backup or portability)."""
    return load(user_id, course_id)

def import_data(user_id: str, course_id: str, data: Dict) -> None:
    """Import user data (from backup)."""
    data["last_updated"] = datetime.now().isoformat()
    save(user_id, course_id, data)

def delete_all_data(user_id: str, course_id: str) -> bool:
    """Delete all memory data for a user+course."""
    p = _path(user_id, course_id)
    if os.path.exists(p):
        os.remove(p)
        return True
    return False