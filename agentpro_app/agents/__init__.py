"""
StudyBuddy Pro - Multi-Agent System
Exports all agent classes for easy importing.
"""

from .base import BaseAgent, AgentRole, AgentContext, AgentResponse, AgentChain
from .tutor_agent import TutorAgent
from .quiz_coach_agent import QuizCoachAgent
from .planner_agent import PlannerAgent
from .orchestrator import AgentOrchestrator, get_orchestrator

__all__ = [
    # Base classes
    'BaseAgent',
    'AgentRole',
    'AgentContext',
    'AgentResponse',
    'AgentChain',
    
    # Agent implementations
    'TutorAgent',
    'QuizCoachAgent',
    'PlannerAgent',
    
    # Orchestrator
    'AgentOrchestrator',
    'get_orchestrator'
]

__version__ = '2.0.0'
