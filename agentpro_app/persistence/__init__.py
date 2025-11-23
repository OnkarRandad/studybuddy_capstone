"""
StudyBuddy Pro - Persistence Layer
SQLite-based memory and progress tracking.
"""

from .database import (
    init_db,
    log_query,
    log_quiz_attempt,
    get_stats,
    get_recent_queries,
    get_quiz_history,
    add_goal,
    complete_goal,
    delete_user_data
)

__all__ = [
    'init_db',
    'log_query',
    'log_quiz_attempt',
    'get_stats',
    'get_recent_queries',
    'get_quiz_history',
    'add_goal',
    'complete_goal',
    'delete_user_data'
]
