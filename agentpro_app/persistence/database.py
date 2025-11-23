"""
SQLite-based memory system for StudyBuddy Pro.
Replaces JSON files with relational database for better scalability.
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "studybuddy.db")

# Schema definitions
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    preferences TEXT
);

CREATE TABLE IF NOT EXISTS courses (
    course_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    study_streak INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    query TEXT NOT NULL,
    mode TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    score REAL NOT NULL CHECK(score >= 0.0 AND score <= 1.0),
    total_questions INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    answers TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS mastery_scores (
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    avg_score REAL NOT NULL,
    first_attempt TEXT NOT NULL,
    last_attempt TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 1,
    recent_scores TEXT,
    PRIMARY KEY (user_id, course_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    created TEXT NOT NULL,
    deadline TEXT,
    completed INTEGER DEFAULT 0,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS topics (
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('weak', 'moderate', 'strong')),
    last_updated TEXT NOT NULL,
    PRIMARY KEY (user_id, course_id, topic),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE INDEX IF NOT EXISTS idx_queries_user_course ON queries(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_quiz_user_course ON quiz_attempts(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_quiz_topic ON quiz_attempts(topic);
CREATE INDEX IF NOT EXISTS idx_mastery_user_course ON mastery_scores(user_id, course_id);
"""

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)

def ensure_user_course(user_id: str, course_id: str) -> None:
    """Ensure user and course exist in database."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, created_at, preferences)
            VALUES (?, ?, ?)
        """, (user_id, now, json.dumps({"difficulty": "medium", "study_hours_per_day": 2})))
        
        conn.execute("""
            INSERT OR IGNORE INTO courses (course_id, user_id, created_at, last_updated, study_streak)
            VALUES (?, ?, ?, ?, 0)
        """, (course_id, user_id, now, now))

def log_query(user_id: str, course_id: str, query: str, mode: str) -> None:
    """Log a user query and increment study streak."""
    ensure_user_course(user_id, course_id)
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO queries (user_id, course_id, query, mode, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, course_id, query, mode, now))
        
        conn.execute("""
            UPDATE courses SET study_streak = study_streak + 1, last_updated = ?
            WHERE course_id = ? AND user_id = ?
        """, (now, course_id, user_id))

def log_quiz_attempt(
    user_id: str,
    course_id: str,
    topic: str,
    score: float,
    total_questions: int,
    difficulty: str,
    answers: Optional[List[Dict]] = None
) -> None:
    """Log a quiz attempt and update mastery tracking."""
    ensure_user_course(user_id, course_id)
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO quiz_attempts (user_id, course_id, topic, score, total_questions, difficulty, timestamp, answers)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, course_id, topic, score, total_questions, difficulty, now, 
              json.dumps(answers) if answers else None))
        
        cursor = conn.execute("""
            SELECT recent_scores, attempt_count FROM mastery_scores
            WHERE user_id = ? AND course_id = ? AND topic = ?
        """, (user_id, course_id, topic))
        
        row = cursor.fetchone()
        
        if row:
            recent_scores = json.loads(row['recent_scores'])
            recent_scores.append(score)
            recent_scores = recent_scores[-10:]
            
            avg_score = sum(recent_scores) / len(recent_scores)
            
            conn.execute("""
                UPDATE mastery_scores
                SET avg_score = ?, last_attempt = ?, attempt_count = attempt_count + 1, recent_scores = ?
                WHERE user_id = ? AND course_id = ? AND topic = ?
            """, (avg_score, now, json.dumps(recent_scores), user_id, course_id, topic))
        else:
            conn.execute("""
                INSERT INTO mastery_scores (user_id, course_id, topic, avg_score, first_attempt, last_attempt, recent_scores)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, course_id, topic, score, now, now, json.dumps([score])))
        
        cursor = conn.execute("""
            SELECT avg_score FROM mastery_scores WHERE user_id = ? AND course_id = ? AND topic = ?
        """, (user_id, course_id, topic))
        
        avg_score = cursor.fetchone()['avg_score']
        
        if avg_score < 0.6:
            status = 'weak'
        elif avg_score > 0.8:
            status = 'strong'
        else:
            status = 'moderate'
        
        conn.execute("""
            INSERT OR REPLACE INTO topics (user_id, course_id, topic, status, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, course_id, topic, status, now))

def get_stats(user_id: str, course_id: str) -> Dict:
    """Get comprehensive statistics for a user in a course."""
    ensure_user_course(user_id, course_id)

    default_stats = {
        "num_files": 0,
        "study_streak": 0,
        "last_activity": None,
        "num_questions_answered": 0,
        "num_quizzes_taken": 0,
    }

    with get_db() as conn:
        course = conn.execute(
            """
            SELECT study_streak, created_at, last_updated FROM courses
            WHERE course_id = ? AND user_id = ?
            """,
            (course_id, user_id),
        ).fetchone()

        if not course:
            return default_stats

        query_count = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM queries WHERE user_id = ? AND course_id = ?
            """,
            (user_id, course_id),
        ).fetchone()["cnt"]

        quiz_stats = conn.execute(
            """
            SELECT COUNT(*) as cnt, AVG(score) as avg_score FROM quiz_attempts
            WHERE user_id = ? AND course_id = ?
            """,
            (user_id, course_id),
        ).fetchone()

        recent_5 = conn.execute(
            """
            SELECT score FROM quiz_attempts WHERE user_id = ? AND course_id = ?
            ORDER BY timestamp DESC LIMIT 5
            """,
            (user_id, course_id),
        ).fetchall()

        older_5 = conn.execute(
            """
            SELECT score FROM quiz_attempts WHERE user_id = ? AND course_id = ?
            ORDER BY timestamp DESC LIMIT 5 OFFSET 5
            """,
            (user_id, course_id),
        ).fetchall()

        recent_trend = "stable"
        if len(recent_5) >= 3:
            recent_avg = sum(r["score"] for r in recent_5) / len(recent_5)
            older_avg = (
                sum(r["score"] for r in older_5) / len(older_5) if older_5 else recent_avg
            )

            if recent_avg > older_avg + 0.1:
                recent_trend = "improving"
            elif recent_avg < older_avg - 0.1:
                recent_trend = "declining"

        weak_topics = conn.execute(
            """
            SELECT topic FROM topics WHERE user_id = ? AND course_id = ? AND status = 'weak'
            """,
            (user_id, course_id),
        ).fetchall()

        strong_topics = conn.execute(
            """
            SELECT topic FROM topics WHERE user_id = ? AND course_id = ? AND status = 'strong'
            """,
            (user_id, course_id),
        ).fetchall()

        mastery = conn.execute(
            """
            SELECT topic, avg_score, attempt_count, recent_scores FROM mastery_scores
            WHERE user_id = ? AND course_id = ?
            """,
            (user_id, course_id),
        ).fetchall()

        mastery_dict = {
            row["topic"]: {
                "avg": row["avg_score"],
                "attempts": row["attempt_count"],
                "scores": json.loads(row["recent_scores"]),
            }
            for row in mastery
        }

        goals = conn.execute(
            """
            SELECT * FROM goals WHERE user_id = ? AND course_id = ?
            """,
            (user_id, course_id),
        ).fetchall()

        return {
            "study_streak": course["study_streak"],
            "total_queries": query_count,
            "quizzes_taken": quiz_stats["cnt"],
            "avg_quiz_score": quiz_stats["avg_score"] or 0.0,
            "recent_trend": recent_trend,
            "weak_topics": [t["topic"] for t in weak_topics],
            "strong_topics": [t["topic"] for t in strong_topics],
            "mastery_scores": mastery_dict,
            "goals": [dict(g) for g in goals],
            "created_at": course["created_at"],
            "last_updated": course["last_updated"],
        }

def get_recent_queries(user_id: str, course_id: str, limit: int = 20) -> List[Dict]:
    """Get recent queries for a user in a course."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT query, mode, timestamp FROM queries
            WHERE user_id = ? AND course_id = ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (user_id, course_id, limit),
        ).fetchall()

        return [dict(r) for r in rows]

def get_quiz_history(user_id: str, course_id: str, topic: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Get quiz history, optionally filtered by topic."""
    with get_db() as conn:
        if topic:
            rows = conn.execute(
                """
                SELECT * FROM quiz_attempts
                WHERE user_id = ? AND course_id = ? AND topic = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (user_id, course_id, topic, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM quiz_attempts
                WHERE user_id = ? AND course_id = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (user_id, course_id, limit),
            ).fetchall()

        return [dict(r) for r in rows]

def add_goal(user_id: str, course_id: str, goal: str, deadline: Optional[str] = None) -> int:
    """Add a study goal and return its ID."""
    ensure_user_course(user_id, course_id)
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO goals (user_id, course_id, goal, created, deadline)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, course_id, goal, now, deadline))
        
        return cursor.lastrowid or -1

def complete_goal(goal_id: int) -> bool:
    """Mark a goal as completed."""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        cursor = conn.execute("""
            UPDATE goals SET completed = 1, completed_at = ?
            WHERE id = ?
        """, (now, goal_id))
        
        return cursor.rowcount > 0

def delete_user_data(user_id: str, course_id: str) -> bool:
    """Delete all data for a user in a specific course."""
    with get_db() as conn:
        conn.execute("DELETE FROM queries WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        conn.execute("DELETE FROM quiz_attempts WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        conn.execute("DELETE FROM mastery_scores WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        conn.execute("DELETE FROM goals WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        conn.execute("DELETE FROM topics WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        conn.execute("DELETE FROM courses WHERE user_id = ? AND course_id = ?", (user_id, course_id))
        
        return True

def get_chunks_for_course(course_id: str):
        """Retrieve text chunks for a given course."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT chunk_text FROM chunks WHERE course_id = ?",
                (course_id,)
            )
            return [row[0] for row in cursor.fetchall()]

# Initialize database on import
init_db()
