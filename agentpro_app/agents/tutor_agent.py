"""
TutorAgent: Handles general Q&A and comprehensive study guides.
Specializes in explanations, concept breakdowns, and teaching.
"""

from .base import BaseAgent, AgentRole, AgentContext, AgentResponse


class TutorAgent(BaseAgent):
    """Agent specialized in teaching and explaining concepts."""
    
    def __init__(self, model: str = None):
        super().__init__(AgentRole.TUTOR, model)
    
    def _build_system_prompt(self) -> str:
        return """You are an expert tutor and conversational study assistant. Your primary goal is to help students understand concepts in a natural, engaging, and interactive way. Use the retrieved course materials as context for your responses.

**Your Teaching Philosophy:**
- Communicate in a friendly, conversational tone.
- Adapt explanations to the student's current understanding level.
- Use relatable examples and analogies to clarify concepts.
- Encourage students to ask questions and think critically.

**Instructions:**
1. Provide clear and concise explanations in a conversational style.
2. Avoid generating structured sections like "Topic Overview" or "Key Takeaways" unless explicitly requested.
3. If the user asks for structured notes (e.g., "Make a study guide"), organize the response into sections with headings and bullet points.
4. Always ground your responses in the provided course materials and cite sources when necessary.

**Default Style:**
- Engage the student with a natural, dialogue-driven approach.
- Ask clarifying questions to ensure understanding.
- Provide examples and encourage follow-up questions.
"""
    
    def can_handle(self, context: AgentContext) -> bool:
        """TutorAgent handles 'guide' and 'chat' modes."""
        return context.mode in ['guide', 'chat']
    
    async def process(self, context: AgentContext) -> AgentResponse:
        """Generate a comprehensive study guide with personalization."""
        
        # Assess retrieval quality
        quality = self._assess_retrieval_quality(context.retrieval_results)
        
        if quality['quality'] == 'empty':
            return AgentResponse(
                content=self._generate_no_content_response(),
                agent_role=self.role,
                citations=[],
                metadata=quality,
                confidence=0.0
            )
        
        # Build personalized context
        formatted_hits = self._format_context_for_llm(context.retrieval_results)
        personalization = self._build_personalization_context(context.user_stats)
        
        # Construct messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Create a study guide for: **{context.query}**

**Student Context:**
{personalization}

**Course Materials:**
{formatted_hits}

Generate a complete, personalized study guide with citations and practice questions."""}
        ]
        
        # Call LLM
        response = self._call_llm(messages, temperature=0.3, max_tokens=2048)
        content = response.choices[0].message.content
        
        # Extract citations
        citations = self._extract_citations(context.retrieval_results)
        
        # Determine if we should chain to another agent
        next_agent = None
        if context.mode == 'chat' and self._should_suggest_quiz(context):
            next_agent = AgentRole.QUIZ_COACH
        
        return AgentResponse(
            content=content,
            agent_role=self.role,
            citations=citations,
            metadata={
                **quality,
                "personalized": True,
                "mode": context.mode
            },
            confidence=quality['confidence'],
            next_agent=next_agent
        )
    
    def _build_personalization_context(self, stats: dict) -> str:
        """Build personalization context from user stats."""
        parts = []
        
        # Weak topics
        weak = stats.get('weak_topics', [])
        if weak:
            parts.append(f"**Areas needing review:** {', '.join(weak[:3])}")
        
        # Strong topics
        strong = stats.get('strong_topics', [])
        if strong:
            parts.append(f"**Strong areas:** {', '.join(strong[:3])}")
        
        # Recent performance
        avg_score = stats.get('avg_quiz_score', 0.0)
        if avg_score > 0:
            parts.append(f"**Average quiz score:** {avg_score*100:.0f}%")
        
        trend = stats.get('recent_trend', 'stable')
        if trend == 'improving':
            parts.append("**Trend:** [UP] Improving - keep up the momentum!")
        elif trend == 'declining':
            parts.append("**Trend:** [DOWN] Needs attention - consider review")
        
        return "\n".join(parts) if parts else "New student - no performance history yet."
    
    def _should_suggest_quiz(self, context: AgentContext) -> bool:
        """Determine if we should suggest a quiz after the guide."""
        # Suggest quiz if student has viewed this topic before
        queries = context.memory_state.get('last_queries', [])
        similar_queries = sum(1 for q in queries if context.query.lower() in q.get('query', '').lower())
        return similar_queries >= 2
    
    def _generate_no_content_response(self) -> str:
        return """## [!] No relevant materials found

I couldn't find any course materials related to your question.

**Suggestions:**
- Upload course materials using the file uploader
- Try rephrasing your question with different keywords
- Check if you're in the correct course

**What I can help with:**
- Answer questions from uploaded materials
- Create study guides and quizzes
- Generate flashcards
- Track your progress
"""