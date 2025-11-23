"""
Configuration module for StudyBuddy.AI backend.
Loads environment variables from the .env file in the project root.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env file from the project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Expose environment variables as constants
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("CHAT_MODEL")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER")

# Ensure critical variables are loaded
if not OPENAI_API_KEY:
    raise ValueError("[ERROR] OPENAI_API_KEY is not set in the .env file.")
if not CHAT_MODEL:
    raise ValueError("[ERROR] CHAT_MODEL is not set in the .env file.")
if not MODEL_PROVIDER:
    raise ValueError("[ERROR] MODEL_PROVIDER is not set in the .env file.")