"""
Agent Orchestrator: Routes requests to appropriate agents and manages agent chains.
"""

from typing import Dict, List, Optional
from .base import AgentContext, AgentResponse, AgentRole, AgentChain
from .tutor_agent import TutorAgent
from .quiz_coach_agent import QuizCoachAgent
from .planner_agent import PlannerAgent
from agentpro_app.config import CHAT_MODEL
import traceback


class AgentOrchestrator:
    """Central coordinator for all agents."""

    def __init__(self, model: Optional[str] = None):
        # Ensure model is always a valid string
        if model is None:
            model = CHAT_MODEL

        # Debug prints for validation
        print("[DEBUG] TutorAgent model:", model)
        print("[DEBUG] PlannerAgent model:", model)
        print("[DEBUG] QuizCoachAgent model:", model)

        self.agents = {
            AgentRole.TUTOR: TutorAgent(model),
            AgentRole.QUIZ_COACH: QuizCoachAgent(model),
            AgentRole.PLANNER: PlannerAgent(model)
        }

        self.agent_chain = AgentChain(list(self.agents.values()))

    def route(self, context: AgentContext) -> AgentRole:
        """Determine which agent should handle the request."""

        # Explicit mode routing
        mode_routing = {
            'guide': AgentRole.TUTOR,
            'chat': AgentRole.TUTOR,
            'quiz': AgentRole.QUIZ_COACH,
            'flashcards': AgentRole.TUTOR,  # Tutor can handle flashcards
            'plan': AgentRole.PLANNER
        }

        if context.mode in mode_routing:
            return mode_routing[context.mode]

        # Query-based routing
        query_lower = context.query.lower()

        if any(word in query_lower for word in ['plan', 'schedule', 'timeline']):
            return AgentRole.PLANNER

        if any(word in query_lower for word in ['quiz', 'test', 'assessment']):
            return AgentRole.QUIZ_COACH

        # Default to tutor
        return AgentRole.TUTOR

    async def process(
        self,
        context: AgentContext,
        enable_chaining: bool = True
    ) -> List[AgentResponse]:
        """Process a request through the agent system."""

        try:
            # Route to primary agent
            primary_role = self.route(context)

            if enable_chaining:
                # Execute agent chain
                responses = await self.agent_chain.execute(context, primary_role)
            else:
                # Single agent execution
                agent = self.agents[primary_role]
                if agent.can_handle(context):
                    response = await agent.process(context)
                    responses = [response]
                else:
                    # Fallback to tutor
                    tutor = self.agents[AgentRole.TUTOR]
                    response = await tutor.process(context)
                    responses = [response]

            return responses

        except Exception as e:
            print("=== ORCHESTRATOR ERROR ===")
            traceback.print_exc()
            raise e  # Re-raise the exception after logging

    def get_agent_capabilities(self) -> Dict:
        """Get information about available agents and their capabilities."""
        return {
            "tutor": {
                "role": "General Q&A and study guides",
                "modes": ["chat", "guide", "flashcards"],
                "specialties": ["explanations", "teaching", "concept breakdown"]
            },
            "quiz_coach": {
                "role": "Adaptive quiz generation",
                "modes": ["quiz"],
                "specialties": ["assessment", "difficulty adaptation", "mastery evaluation"]
            },
            "planner": {
                "role": "Study planning and scheduling",
                "modes": ["plan"],
                "specialties": ["scheduling", "prioritization", "spaced repetition"]
            }
        }

    def format_responses(self, responses: List[AgentResponse]) -> Dict:
        """Format agent responses for API output."""

        if not responses:
            return {
                "ok": False,
                "error": "No agent could handle this request"
            }

        # Primary response (first in chain)
        primary = responses[0]

        output = {
            "ok": True,
            "type": primary.agent_role.value,
            "content_md": primary.content,
            "citations": primary.citations,
            "metadata": primary.metadata,
            "confidence": primary.confidence
        }

        # Add chained responses if any
        if len(responses) > 1:
            output["chained_responses"] = [
                {
                    "type": r.agent_role.value,
                    "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                    "metadata": r.metadata
                }
                for r in responses[1:]
            ]

        # Add warnings for low quality
        if primary.confidence < 0.6:
            output["warning"] = "âš ï¸ Low confidence in results. Consider uploading more materials or rephrasing your question."
            output["suggestions"] = [
                "Try more specific search terms",
                "Upload additional course materials",
                "Break your question into smaller parts"
            ]

        return output


# Singleton instance
_orchestrator = None

def get_orchestrator(model: Optional[str] = None) -> AgentOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator(model)
    return _orchestrator