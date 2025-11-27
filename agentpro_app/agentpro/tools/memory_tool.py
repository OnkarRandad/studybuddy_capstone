"""
MemoryTool: Tools for reading and writing user memory/context.
"""

import json
from typing import Any, Dict
from .base_tool import Tool


class MemoryReadTool(Tool):
    """
    Tool for reading user memory and context.

    Retrieves stored information about user's learning patterns, preferences, and history.
    """

    name: str = "Read Memory"
    description: str = "Read user's learning history, preferences, weak/strong topics, and quiz history from memory"
    action_type: str = "read_memory"
    input_format: str = '{"user_id": "user123", "course_id": "course456", "fields": ["weak_topics", "quiz_history", "goals"]}'

    def run(self, input_data: Any) -> str:
        """
        Read user memory.

        Args:
            input_data: Dict with user_id, course_id, fields (optional)

        Returns:
            JSON string with requested memory fields
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return json.dumps({"error": "Invalid input format"})

            user_id = params.get("user_id")
            course_id = params.get("course_id")
            fields = params.get("fields", None)  # If None, return all

            if not all([user_id, course_id]):
                return json.dumps({"error": "Missing required fields: user_id, course_id"})

            # Load memory
            from agentpro_app.memory import load
            memory = load(user_id, course_id)

            # Filter fields if requested
            if fields:
                filtered = {k: memory.get(k) for k in fields if k in memory}
                return json.dumps(filtered, indent=2)
            else:
                return json.dumps(memory, indent=2)

        except Exception as e:
            return json.dumps({"error": f"Failed to read memory: {str(e)}"})


class MemoryWriteTool(Tool):
    """
    Tool for writing to user memory.

    Updates stored information about user's learning patterns and preferences.
    """

    name: str = "Write Memory"
    description: str = "Update user's memory with new information (weak/strong topics, goals, preferences, etc.)"
    action_type: str = "write_memory"
    input_format: str = '{"user_id": "user123", "course_id": "course456", "updates": {"weak_topics": [...], "goals": [...]}}'

    def run(self, input_data: Any) -> str:
        """
        Write to user memory.

        Args:
            input_data: Dict with user_id, course_id, updates (dict of fields to update)

        Returns:
            Success/failure message
        """
        try:
            # Parse input
            if isinstance(input_data, str):
                params = json.loads(input_data)
            elif isinstance(input_data, dict):
                params = input_data
            else:
                return json.dumps({"error": "Invalid input format"})

            user_id = params.get("user_id")
            course_id = params.get("course_id")
            updates = params.get("updates", {})

            if not all([user_id, course_id]):
                return json.dumps({"error": "Missing required fields: user_id, course_id"})

            if not updates:
                return json.dumps({"error": "No updates provided"})

            # Load, update, and save memory
            from agentpro_app.memory import load, save
            memory = load(user_id, course_id)

            # Update fields
            for key, value in updates.items():
                memory[key] = value

            save(user_id, course_id, memory)

            return json.dumps({
                "status": "success",
                "message": f"Updated {len(updates)} field(s) in memory",
                "updated_fields": list(updates.keys())
            })

        except Exception as e:
            return json.dumps({"error": f"Failed to write memory: {str(e)}"})
