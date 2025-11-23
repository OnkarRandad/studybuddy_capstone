"""
QuizCoachAgent: Generates adaptive quizzes based on mastery levels.
Adjusts difficulty, question types, and focus areas dynamically.
"""

from .base import BaseAgent, AgentRole, AgentContext, AgentResponse
from typing import Dict, List, Optional
import json
from agentpro_app.config import CHAT_MODEL



class QuizCoachAgent(BaseAgent):
    """Agent specialized in adaptive quiz generation."""
    
    def __init__(self, model: Optional[str] = None):
        super().__init__(AgentRole.QUIZ_COACH, model or CHAT_MODEL)

    
    def _build_system_prompt(self) -> str:
        return """You are an expert assessment designer creating adaptive quizzes.

**Your Assessment Philosophy:**
- Questions should test understanding, not just memorization
- Mix question types to assess different cognitive levels
- Provide detailed rationales that teach, not just correct
- Adapt difficulty based on student's mastery level

**Question Types:**
1. **Multiple Choice**: 4 options, 1 correct
2. **True/False**: With explanation requirement
3. **Short Answer**: 2-3 sentence responses
4. **Application**: Real-world scenario problems
5. **Analysis**: Compare/contrast or evaluate

**Difficulty Levels:**
- **Easy**: Definitions, basic recall, straightforward applications
- **Medium**: Applied understanding, multi-step reasoning
- **Hard**: Complex analysis, edge cases, synthesis

**Instructions:**
1. Generate questions that match the specified difficulty and mastery level
2. Include diverse question types within the quiz
3. Cite page numbers for each question's source material
4. Provide comprehensive answer keys with teaching rationales
5. Include common wrong answer explanations for MC questions

**Output Format:**
## Quiz: [Topic] - [Difficulty] Level

### Question 1 (Multiple Choice)
**Q:** [Question text] _(Source, p.X)_

A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

### Question 2 (True/False)
**Q:** [Statement] _(Source, p.Y)_

### Question 3 (Short Answer)
**Q:** [Question requiring explanation] _(Source, p.Z)_

---

## Answer Key & Rationales

**Q1:** B - [Detailed explanation of why B is correct]
- Why A is wrong: [explanation]
- Why C is wrong: [explanation]
- Why D is wrong: [explanation]
_(p.X)_

**Q2:** False - [Complete explanation with reasoning] _(p.Y)_

**Q3:** [Sample answer with key points to look for] _(p.Z)_

---

## Performance Tips
[Specific guidance based on student's weak areas]
"""
    
    def can_handle(self, context: AgentContext) -> bool:
        """QuizCoach handles 'quiz' mode."""
        return context.mode == 'quiz'
    
    async def process(self, context: AgentContext) -> AgentResponse:
        """Generate an adaptive quiz based on student mastery."""
        
        # Assess retrieval quality
        quality = self._assess_retrieval_quality(context.retrieval_results)
        
        if quality['quality'] == 'empty':
            return AgentResponse(
                content="**Cannot generate quiz - no relevant materials found.**\n\nPlease upload course materials first.",
                agent_role=self.role,
                citations=[],
                metadata=quality,
                confidence=0.0
            )
        
        # Determine adaptive difficulty
        adaptive_difficulty = self._determine_difficulty(context)
        num_questions = context.metadata.get('num_items', 6)
        
        # Build personalized quiz context
        formatted_hits = self._format_context_for_llm(context.retrieval_results)
        coaching = self._build_coaching_context(context.user_stats, adaptive_difficulty)
        
        # Construct messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""Create a {adaptive_difficulty['level']} quiz on: **{context.query}**

**Student Performance Context:**
{coaching}

**Course Materials:**
{formatted_hits}

Generate {num_questions} varied questions with complete answer key and teaching rationales."""}
        ]
        
        # Call LLM
        response = self._call_llm(messages, temperature=0.4, max_tokens=2048)
        content = response.choices[0].message.content
        
        # Add adaptive coaching message
        content = self._add_coaching_message(content, adaptive_difficulty)
        
        # Extract citations
        citations = self._extract_citations(context.retrieval_results)
        
        return AgentResponse(
            content=content,
            agent_role=self.role,
            citations=citations,
            metadata={
                **quality,
                "difficulty": adaptive_difficulty['level'],
                "adaptive_reasoning": adaptive_difficulty['reasoning'],
                "num_questions": num_questions,
                "mode": "quiz"
            },
            confidence=quality['confidence'],
            next_agent=AgentRole.FEEDBACK  # Chain to feedback after quiz
        )
    
    

    def _determine_difficulty(self, context: AgentContext) -> Dict:
        """Adaptively determine quiz difficulty based on mastery."""
        requested = context.metadata.get('difficulty', 'medium')
        stats = context.user_stats
        query_topic = context.query.lower()
        
        # Check if this topic has mastery data
        mastery_scores = stats.get('mastery_scores', {})
        
        # Find relevant topic in mastery scores
        relevant_topic = None
        for topic in mastery_scores.keys():
            if topic.lower() in query_topic or query_topic in topic.lower():
                relevant_topic = topic
                break
        
        if relevant_topic:
            avg_score = mastery_scores[relevant_topic].get('avg', 0.0)
            attempts = mastery_scores[relevant_topic].get('attempts', 0)
            
            # Adaptive logic
            if avg_score >= 0.85 and attempts >= 2:
                # Student is mastering - bump up difficulty
                if requested == 'easy':
                    level = 'medium'
                    reasoning = "Promoting to medium difficulty due to strong performance (>85%)"
                elif requested == 'medium':
                    level = 'hard'
                    reasoning = "Promoting to hard difficulty - you're ready for a challenge!"
                else:
                    level = 'hard'
                    reasoning = "Maintaining hard difficulty based on consistent mastery"
            
            elif avg_score < 0.6 and attempts >= 2:
                # Student is struggling - lower difficulty
                if requested == 'hard':
                    level = 'medium'
                    reasoning = "Adjusting to medium difficulty to build confidence (<60%)"
                elif requested == 'medium':
                    level = 'easy'
                    reasoning = "Starting with easy questions to reinforce fundamentals"
                else:
                    level = 'easy'
                    reasoning = "Focusing on foundational concepts"
            
            else:
                # Use requested difficulty
                level = requested
                reasoning = f"Using requested difficulty ({avg_score*100:.0f}% mastery)"
        
        else:
            # No mastery data - use requested
            level = requested
            reasoning = "No previous attempts - using requested difficulty"
        
        return {
            "level": level,
            "reasoning": reasoning,
            "requested": requested
        }
    
    def _build_coaching_context(self, stats: Dict, difficulty: Dict) -> str:
        """Build coaching context for quiz generation."""
        parts = [f"**Adaptive Difficulty:** {difficulty['level']} ({difficulty['reasoning']})"]
        
        # Weak topics to focus on
        weak = stats.get('weak_topics', [])
        if weak:
            parts.append(f"**Focus Areas:** Include questions on {', '.join(weak[:2])} (needs review)")
        
        # Recent trend
        trend = stats.get('recent_trend', 'stable')
        if trend == 'declining':
            parts.append("**Note:** Recent performance declining - include review questions")
        elif trend == 'improving':
            parts.append("**Note:** Student improving - can include challenge questions")
        
        return "\n".join(parts)
    
    def _add_coaching_message(self, content: str, difficulty: Dict) -> str:
        """Add personalized coaching message to quiz."""
        if difficulty['level'] != difficulty['requested']:
            message = f"\n\n---\n\n### ðŸ'¬ Coach's Note\n\n{difficulty['reasoning']}\n"
            content = message + content
        return content
    
    def generate_quiz(self, chunks: list[str], num_questions: int, difficulty: str):
        """Generate a structured quiz based on the provided chunks and parameters."""
        difficulty = (difficulty or "medium").lower()
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        snippets = []
        for ch in chunks:
            if isinstance(ch, dict):
                text = ch.get("text") or ch.get("content") or ""
            else:
                text = str(ch)
            text = text.strip()
            if not text:
                continue
            snippets.append(f"- {text[:300]}")
            if len(snippets) >= max(12, num_questions * 3):
                break

        if not snippets:
            raise ValueError("No course content available.")

        materials = "\n".join(snippets)

        system_prompt = self.system_prompt + (
            "\n\nYou are generating a JSON-only quiz for a web app. "
            "Respond with VALID JSON ONLY, no markdown or commentary."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Generate a {difficulty} difficulty quiz with {num_questions} questions.
Use this JSON structure:

{{
  "title": "Quiz Title",
  "questions": [
    {{
      "id": "q1",
      "question": "Question?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A",
      "explanation": "Short reasoning."
    }}
  ]
}}

Course materials:
{materials}
""",
            },
        ]

        response = self._call_llm(messages, temperature=0.4, max_tokens=2048)
        raw = response.choices[0].message.content.strip()

        # extract only the JSON
        start = raw.find("{")
        end = raw.rfind("}")
        json_str = raw[start : end + 1]

        quiz = json.loads(json_str)

        # normalize
        normalized = []
        for i, q in enumerate(quiz.get("questions", [])):
            qid = q.get("id") or f"q{i+1}"
            question = q.get("question", "")
            options = q.get("options", [])[:4]
            answer = q.get("correct_answer", "")
            explanation = q.get("explanation", "")

            if answer not in options and options:
                answer = options[0]

            normalized.append(
                {
                    "id": qid,
                    "question": question,
                    "options": options,
                    "correct_answer": answer,
                    "explanation": explanation,
                }
            )

        return {
            "title": quiz.get("title") or "Practice Quiz",
            "questions": normalized,
        }