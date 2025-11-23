"""
Base agent architecture for StudyBuddy Pro.
Defines the interface all agents must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
from agentpro_app.config import CHAT_MODEL, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
DEFAULT_MODEL = CHAT_MODEL

# Debug print for model
print("[DEBUG] Using model:", CHAT_MODEL)


class AgentRole(Enum):
    """Agent role definitions."""
    TUTOR = "tutor"
    QUIZ_COACH = "quiz_coach"
    PLANNER = "planner"
    FEEDBACK = "feedback"
    EVALUATOR = "evaluator"


@dataclass
class AgentContext:
    """Shared context passed between agents."""
    user_id: str
    course_id: str
    query: str
    mode: str
    retrieval_results: List[Dict]
    user_stats: Dict
    memory_state: Dict
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AgentResponse:
    """Standardized agent response."""
    content: str
    agent_role: AgentRole
    citations: List[Dict]
    metadata: Dict
    confidence: float = 1.0
    next_agent: Optional[AgentRole] = None
    tool_calls: List[Dict] = None
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


class BaseAgent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, role: AgentRole, model: str = DEFAULT_MODEL):
        self.role = role
        self.model = model
        self.system_prompt = self._build_system_prompt()
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Build the system prompt for this agent."""
        pass
    
    @abstractmethod
    def can_handle(self, context: AgentContext) -> bool:
        """Determine if this agent can handle the given context."""
        pass
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResponse:
        """Process the context and return a response."""
        pass
    
    def _call_llm(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Any:
        """Call the LLM with standard error handling."""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )
            return response
        except Exception as e:
            raise RuntimeError(f"LLM call failed for {self.role.value}: {str(e)}")
    
    def _extract_citations(self, hits: List[Dict]) -> List[Dict]:
        """Extract unique citations from retrieval results."""
        citations = []
        seen = set()
        
        for h in hits[:5]:
            key = (h['meta'].get('title'), h['meta'].get('page'))
            if key not in seen:
                citations.append({
                    "title": h['meta'].get('title', 'Document'),
                    "page": h['meta'].get('page', '?'),
                    "snippet": h.get('snippet', ''),
                    "score": h.get('score', 0.0)
                })
                seen.add(key)
        
        return citations
    
    def _format_context_for_llm(self, hits: List[Dict]) -> str:
        """Format retrieval results for LLM context."""
        formatted = []
        for i, h in enumerate(hits, 1):
            title = h['meta'].get('title', 'Document')
            page = h['meta'].get('page', '?')
            snippet = h.get('snippet', h['text'][:150] + "...")
            score = h.get('score', 0.0)
            
            formatted.append(
                f"[{i}] ({title}, p.{page}, relevance: {score:.2f})\n{snippet}\n"
            )
        return "\n".join(formatted)
    
    def _assess_retrieval_quality(self, hits: List[Dict]) -> Dict:
        """Assess the quality of retrieval results."""
        if not hits:
            return {"quality": "empty", "avg_score": 0.0, "confidence": 0.0}
        
        avg_score = sum(h.get('score', 0) for h in hits) / len(hits)
        
        if avg_score > 0.7:
            quality = "high"
            confidence = 0.9
        elif avg_score > 0.4:
            quality = "medium"
            confidence = 0.7
        else:
            quality = "low"
            confidence = 0.5
        
        return {
            "quality": quality,
            "avg_score": avg_score,
            "confidence": confidence,
            "num_results": len(hits)
        }


class AgentChain:
    """Chain multiple agents together for complex workflows."""
    
    def __init__(self, agents: List[BaseAgent]):
        self.agents = {agent.role: agent for agent in agents}
    
    async def execute(self, context: AgentContext, start_role: AgentRole) -> List[AgentResponse]:
        """Execute agent chain starting from specified role."""
        responses = []
        current_role = start_role
        max_iterations = 5
        iteration = 0
        
        while current_role and iteration < max_iterations:
            agent = self.agents.get(current_role)
            if not agent:
                break
            
            if not agent.can_handle(context):
                break
            
            response = await agent.process(context)
            responses.append(response)
            
            # Update context with response
            context.metadata['previous_responses'] = responses
            
            # Check if agent wants to chain to another
            current_role = response.next_agent
            iteration += 1
        
        return responses