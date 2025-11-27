"""
Migration script to convert JSON memory files to SQLite database.
Run this once to migrate existing user data.
"""

import os
import json
import glob
from datetime import datetime
from agentpro_app.persistence import database as db

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "agentpro_app", "memory")


def migrate_json_memory():
    """Migrate all JSON memory files to SQLite."""
    
    if not os.path.exists(MEMORY_DIR):
        print("No memory directory found. Skipping migration.")
        return
    
    json_files = glob.glob(os.path.join(MEMORY_DIR, "*.json"))
    
    if not json_files:
        print("No JSON memory files found.")
        return
    
    print(f"YOO"„ Found {len(json_files)} memory files to migrate...")
    
    migrated = 0
    errors = 0
    
    for json_file in json_files:
        try:
            # Parse filename: {user_id}__{course_id}.json
            filename = os.path.basename(json_file)
            parts = filename.replace(".json", "").split("__")
            
            if len(parts) != 2:
                print(f"Skipping invalid filename: {filename}")
                continue
            
            user_id, course_id = parts
            
            # Load JSON data
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            print(f"Migrating {user_id} / {course_id}...")
            
            # Ensure user and course exist
            db.ensure_user_course(user_id, course_id)
            
            # Migrate queries
            for query in data.get("last_queries", []):
                if isinstance(query, dict):
                    db.log_query(
                        user_id,
                        course_id,
                        query.get("query", ""),
                        query.get("mode", "chat")
                    )
            
            # Migrate quiz history
            for quiz in data.get("quiz_history", []):
                db.log_quiz_attempt(
                    user_id,
                    course_id,
                    quiz.get("topic", "unknown"),
                    quiz.get("score", 0.0),
                    quiz.get("total_questions", 0),
                    quiz.get("difficulty", "medium"),
                    quiz.get("answers")
                )
            
            # Migrate goals
            for goal in data.get("goals", []):
                if not goal.get("completed", False):
                    db.add_goal(
                        user_id,
                        course_id,
                        goal.get("goal", ""),
                        goal.get("deadline")
                    )
            
            # Update study streak
            with db.get_db() as conn:
                conn.execute("""
                    UPDATE courses SET study_streak = ?
                    WHERE user_id = ? AND course_id = ?
                """, (data.get("study_streak", 0), user_id, course_id))
            
            migrated += 1
            print(f"  âœ… Migrated successfully")
            
        except Exception as e:
            print(f"  âŒ Error migrating {json_file}: {str(e)}")
            errors += 1
    
    print(f"\nðŸŽ‰ Migration complete!")
    print(f"  âœ… Migrated: {migrated}")
    print(f"  âŒ Errors: {errors}")
    
    if errors == 0:
        print(f"\nðŸ—'ï¸  You can now safely delete the memory/ directory")
    else:
        print(f"\nâš ï¸  Some files had errors. Review before deleting memory/ directory")


def verify_migration():
    """Verify migration by comparing JSON and SQLite data."""
    print("\nðŸ"Š Verifying migration...")
    
    with db.get_db() as conn:
        # Count users
        user_count = conn.execute("SELECT COUNT(DISTINCT user_id) FROM users").fetchone()[0]
        course_count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        query_count = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        quiz_count = conn.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0]
        
        print(f"  Users: {user_count}")
        print(f"  Courses: {course_count}")
        print(f"  Queries: {query_count}")
        print(f"  Quizzes: {quiz_count}")


if __name__ == "__main__":
    print("StudyBuddy JSON → SQLite Migration")
    print("=" * 50)
    
    migrate_json_memory()
    verify_migration()
    
    print("\nMigration script finished!")