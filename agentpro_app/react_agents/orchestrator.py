"""
Orchestrator: Top-level ReactAgent that routes to specialized agents.

Uses RoutingTool to decide which agent to use, then delegates to that agent.
"""

from typing import Dict, Any
from openai import OpenAI
from agentpro_app.agentpro import ReactAgent, AgentResponse
from agentpro_app.agentpro.tools.routing_tool import RoutingTool
from agentpro_app.agentpro.tools.rag_tool import RAGTool
from agentpro_app.agentpro.tools.memory_tool import MemoryReadTool
from agentpro_app.config import OPENAI_API_KEY, CHAT_MODEL
from .tutor_agent import create_tutor_agent
from .quiz_coach_agent import create_quiz_coach_agent
from .planner_agent import create_planner_agent
from .flashcards_agent import create_flashcards_agent
import json


class OrchestratorAgent:
    """
    Top-level orchestrator that uses LLM-based routing to delegate to specialized agents.

    This replaces the old rule-based orchestrator with a ReAct-based approach.
    """

    def __init__(self, model: str = None):
        """
        Initialize orchestrator with all specialized agents.

        Args:
            model: LLM model to use (defaults to CHAT_MODEL from config)
        """
        self.model = model or CHAT_MODEL
        self.client = OpenAI(api_key=OPENAI_API_KEY)

        # Create specialized agents
        self.agents = {
            "tutor": create_tutor_agent(model=self.model),
            "quiz_coach": create_quiz_coach_agent(model=self.model),
            "planner": create_planner_agent(model=self.model),
            "flashcards": create_flashcards_agent(model=self.model)
        }

        # Create routing tool
        self.routing_tool = RoutingTool(model=self.model, temperature=0.2)

    def route(
        self,
        query: str,
        mode: str = "",
        retrieval_results: list = None,
        user_stats: Dict = None
    ) -> str:
        """
        Use LLM-based routing to determine which agent should handle the request.

        Args:
            query: User query
            mode: Optional mode hint (guide, quiz, plan, flashcards)
            retrieval_results: RAG retrieval results
            user_stats: User statistics and memory

        Returns:
            Agent name: "tutor", "quiz_coach", "planner", or "flashcards"
        """
        # Prepare context summary
        context_summary = ""
        if retrieval_results and len(retrieval_results) > 0:
            context_summary = f"{len(retrieval_results)} relevant documents found"
        else:
            context_summary = "No course materials available"

        # Use routing tool
        routing_input = {
            "query": query,
            "mode": mode,
            "context_summary": context_summary,
            "user_stats": user_stats or {}
        }

        result = self.routing_tool.run(routing_input)

        try:
            decision = json.loads(result)
            agent_name = decision.get("agent", "tutor")
            reasoning = decision.get("reasoning", "")

            print(f"[ROUTING] Selected agent: {agent_name} - Reason: {reasoning}")

            return agent_name
        except:
            # Fallback to tutor if routing fails
            print("[ROUTING] Routing failed, defaulting to tutor")
            return "tutor"

    def process(
        self,
        query: str,
        user_id: str,
        course_id: str,
        mode: str = "",
        difficulty: str = "medium",
        num_questions: int = 6,
        deadline: str = None,
        hours_per_day: int = 2
    ) -> Dict[str, Any]:
        """
        Process a user request through the ReAct pipeline.

        Args:
            query: User query
            user_id: User ID
            course_id: Course ID
            mode: Optional mode hint
            difficulty: Quiz difficulty (for quiz mode)
            num_questions: Number of quiz questions (for quiz mode)
            deadline: Study plan deadline (for plan mode)
            hours_per_day: Daily study hours (for plan mode)

        Returns:
            Dict with response, agent used, and metadata
        """
        # Import here to avoid circular dependencies
        from agentpro_app.rag import hybrid_retrieve
        from agentpro_app.persistence.database import Database

        db = Database()

        # Step 1: Retrieve materials (if query suggests it's needed)
        retrieval_results = []
        if mode not in ["plan"]:  # Planner doesn't need RAG
            retrieval_results = hybrid_retrieve(query, user_id, course_id, top_k=8)

        # Step 2: Get user stats
        user_stats = db.get_stats(user_id, course_id)

        # Step 3: Route to appropriate agent using LLM
        agent_name = self.route(query, mode, retrieval_results, user_stats)

        # Step 4: Build context for the selected agent
        context = {
            "user_id": user_id,
            "course_id": course_id,
            "mode": mode,
            "difficulty": difficulty,
            "num_questions": num_questions,
            "deadline": deadline,
            "hours_per_day": hours_per_day,
            "retrieval_count": len(retrieval_results),
            "user_stats": user_stats
        }

        # Build agent-specific query with context
        if retrieval_results:
            # Format retrieval results for context
            context_items = []
            for hit in retrieval_results[:5]:
                context_items.append({
                    "text": hit.get("text", ""),
                    "title": hit.get("meta", {}).get("title", "Document"),
                    "page": hit.get("meta", {}).get("page", "?"),
                    "score": hit.get("score", 0.0)
                })
            context["retrieval_context"] = context_items

        # Step 5: Execute selected agent
        agent = self.agents[agent_name]
        response: AgentResponse = agent.run(query, context)

        # Step 6: Log query
        db.log_query(user_id, course_id, query, mode or agent_name)

        # Step 7: Format and return response
        return {
            "ok": True,
            "agent": agent_name,
            "content": response.get_final_answer(),
            "thought_process": [step.model_dump() for step in response.thought_process],
            "context": context
        }


def create_orchestrator_agent(model: str = None) -> OrchestratorAgent:
    """
    Create an orchestrator agent.

    Args:
        model: LLM model to use

    Returns:
        Configured OrchestratorAgent
    """
    return OrchestratorAgent(model=model)
