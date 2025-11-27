"""
Improved Orchestrator for StudyBuddy Pro 2.0

This orchestrator uses a streamlined approach:
1. LLM-based routing to determine intent
2. Direct tool execution (no nested ReactAgent)
3. Deterministic response generation
4. Proper error handling and logging
"""

from typing import Dict, List, Optional, Any
import json
from openai import OpenAI
from dataclasses import dataclass

from agentpro_app.config import CHAT_MODEL, OPENAI_API_KEY
from agentpro_app.rag import hybrid_retrieve
from agentpro_app.memory import load as load_memory, log_query
from agentpro_app.persistence import database as db

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

print("[ORCHESTRATOR] Initialized with model:", CHAT_MODEL)


@dataclass
class RoutingDecision:
    """Structured routing decision from LLM."""
    agent: str  # assistant, tutor, quiz_coach, planner, flashcards
    reasoning: str
    confidence: float
    requires_retrieval: bool
    response_type: str  # summary, guide, quiz, chat, plan, flashcards


def route_request(query: str, mode_hint: Optional[str] = None) -> RoutingDecision:
    """
    Use LLM to determine routing based on query intent.
    
    Args:
        query: User's query text
        mode_hint: Optional mode hint from API (quiz, plan, guide, etc.)
        
    Returns:
        RoutingDecision with agent and response_type
    """
    system_prompt = """You are an intelligent routing system for a study assistant.

Analyze the user's request and determine the best agent and response type.

**Available Agents:**
- assistant: General questions, summaries, basic explanations
- tutor: Comprehensive study guides, detailed concept explanations
- quiz_coach: Quiz generation and assessment
- planner: Study planning and scheduling (can use materials when available)
- flashcards: Flashcard creation

**Response Types:**
- summary: Brief overview or summary
- guide: Comprehensive study guide
- quiz: Assessment/quiz generation
- chat: Conversational response
- plan: Study schedule/plan
- flashcards: Memory cards

**Routing Rules:**
1. "Summarize" or "summary" → assistant + summary
2. "Study guide" or "explain in detail" → tutor + guide
3. "Quiz" or "test me" → quiz_coach + quiz
4. "Plan" or "schedule" or time-based requests → planner + plan
5. "Flashcards" → flashcards + flashcards
6. General questions → assistant + chat

**For Planner:**
- requires_retrieval: true if user mentions materials, documents, slides, specific topics
- requires_retrieval: false for general time-based planning without content reference

Return ONLY valid JSON:
{
  "agent": "agent_name",
  "reasoning": "why this agent",
  "confidence": 0.9,
  "requires_retrieval": true,
  "response_type": "type"
}"""

    # Build user prompt with mode hint if available
    user_prompt = f"Route this request: '{query}'"
    if mode_hint:
        user_prompt += f"\n\nMode hint provided: {mode_hint}"
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=256,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return RoutingDecision(
            agent=result.get("agent", "assistant"),
            reasoning=result.get("reasoning", ""),
            confidence=result.get("confidence", 0.7),
            requires_retrieval=result.get("requires_retrieval", True),
            response_type=result.get("response_type", "chat")
        )
        
    except Exception as e:
        print(f"[ROUTING ERROR] {str(e)}")
        # Fallback routing
        return RoutingDecision(
            agent="assistant",
            reasoning="Default routing due to error",
            confidence=0.5,
            requires_retrieval=True,
            response_type="chat"
        )


def format_context_for_llm(hits: List[Dict]) -> str:
    """Format retrieval results for LLM context."""
    if not hits:
        return "No course materials found."
    
    formatted = []
    for i, h in enumerate(hits, 1):
        title = h.get('meta', {}).get('title', 'Document')
        page = h.get('meta', {}).get('page', '?')
        text = h.get('text', '')[:400]  # Truncate for context window
        score = h.get('score', 0.0)
        
        formatted.append(
            f"[{i}] (Source: {title}, p.{page}, relevance: {score:.2f})\n{text}...\n"
        )
    
    return "\n".join(formatted)


def extract_citations(hits: List[Dict]) -> List[Dict]:
    """Extract unique citations from retrieval results."""
    citations = []
    seen = set()
    
    for h in hits[:5]:
        title = h.get('meta', {}).get('title')
        page = h.get('meta', {}).get('page')
        key = (title, page)
        
        if key not in seen and title:
            citations.append({
                "title": title,
                "page": page,
                "snippet": h.get('snippet', '')[:150],
                "score": h.get('score', 0.0)
            })
            seen.add(key)
    
    return citations


def generate_summary(query: str, context: str) -> str:
    """Generate a concise summary."""
    system_prompt = """You are a helpful assistant that provides clear, concise summaries.

Focus on the main points and key takeaways.
Keep your response brief and well-organized.
Do NOT create study guides or extensive explanations - just summarize.
If context is insufficient, say so briefly."""

    user_prompt = f"Summarize: {query}\n\nContext:\n{context}"
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1024
    )
    
    return response.choices[0].message.content


def generate_study_guide(query: str, context: str, user_stats: Dict) -> str:
    """Generate a comprehensive study guide."""
    system_prompt = """You are an expert tutor creating comprehensive study guides.

Create well-structured guides with:
1. Topic Overview
2. Key Concepts (with examples and citations)
3. Important Details
4. Practice Questions
5. Summary/Key Takeaways

Use inline citations: (Source, p.X) after each claim.
Make it educational and thorough."""

    # Add personalization
    weak_topics = user_stats.get("weak_topics", [])
    personalization = ""
    if weak_topics:
        personalization = f"\n\nNote: Student needs extra help with: {', '.join(weak_topics)}"
    
    user_prompt = f"Create a study guide for: {query}\n\nCourse Materials:\n{context}{personalization}"
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2048
    )
    
    return response.choices[0].message.content


def generate_quiz(query: str, context: str, difficulty: str, num_questions: int, user_stats: Dict) -> str:
    """Generate an adaptive quiz."""
    # Adaptive difficulty adjustment
    mastery_scores = user_stats.get("mastery_scores", {})
    query_lower = query.lower()
    
    # Find relevant topic in mastery
    relevant_topic = None
    for topic in mastery_scores.keys():
        if topic.lower() in query_lower or query_lower in topic.lower():
            relevant_topic = topic
            break
    
    # Adjust difficulty based on mastery
    adaptive_note = ""
    if relevant_topic:
        avg_score = mastery_scores[relevant_topic].get('avg', 0.0)
        if avg_score >= 0.85 and difficulty == "medium":
            difficulty = "hard"
            adaptive_note = "\n\n**Coach's Note:** Increased difficulty to 'hard' based on your strong performance (>85%)."
        elif avg_score < 0.6 and difficulty == "medium":
            difficulty = "easy"
            adaptive_note = "\n\n**Coach's Note:** Starting with 'easy' difficulty to build confidence (<60%)."
    
    system_prompt = f"""You are an expert educator creating assessments.

Generate a {difficulty} difficulty quiz with {num_questions} questions.

**Instructions:**
1. Mix question types: Multiple Choice, True/False, Short Answer
2. Include answer key with detailed rationales
3. Cite page numbers: (Source, p.X)
4. Base questions on provided materials

**Format:**
## Quiz: [Topic] - {difficulty.title()} Level

### Question 1 (Multiple Choice)
**Q:** [Question text] _(Source, p.X)_
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

---
## Answer Key
**Q1:** B - [Detailed explanation] _(p.X)_"""

    user_prompt = f"Create quiz on: {query}\n\nCourse content:\n{context}"
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
        max_tokens=2048
    )
    
    content = response.choices[0].message.content
    return adaptive_note + content if adaptive_note else content


def generate_study_plan(
    query: str, 
    user_stats: Dict, 
    deadline: Optional[str], 
    hours_per_day: int,
    retrieval_results: List[Dict] = None
) -> str:
    """
    Generate a flexible, RAG-aware study plan.
    
    Handles human requests like:
    - "make me a 2 hour plan"
    - "give me a 7 day schedule, 2 hrs/day"
    - "use the slides I uploaded"
    - "focus on linear algebra"
    """
    from datetime import datetime
    import re
    
    # Parse flexible time requests from query
    time_info = _parse_time_from_query(query, deadline, hours_per_day)
    
    # Build user context
    weak_topics = user_stats.get("weak_topics", [])
    strong_topics = user_stats.get("strong_topics", [])
    recent_queries = user_stats.get("total_queries", 0)
    
    user_context = []
    if weak_topics:
        user_context.append(f"Weak areas: {', '.join(weak_topics[:3])}")
    if strong_topics:
        user_context.append(f"Strong areas: {', '.join(strong_topics[:3])}")
    
    trend = user_stats.get('recent_trend', 'stable')
    if trend == 'declining':
        user_context.append("Recent performance declining — needs foundational review")
    elif trend == 'improving':
        user_context.append("Making progress — can handle challenge")
    
    user_context_str = "\n".join(user_context) if user_context else "New student — no history yet"
    
    # Build RAG context with specific material references
    materials_context = ""
    if retrieval_results and len(retrieval_results) > 0:
        materials_context = "\n\n**Available Materials:**\n"
        
        # Group by document
        docs = {}
        for i, hit in enumerate(retrieval_results[:15], 1):
            title = hit.get('meta', {}).get('title', 'Document')
            page = hit.get('meta', {}).get('page', '?')
            text_preview = hit.get('text', '')[:150]
            
            if title not in docs:
                docs[title] = []
            docs[title].append({
                'chunk_id': i,
                'page': page,
                'preview': text_preview
            })
        
        for title, chunks in docs.items():
            materials_context += f"\n**{title}:**\n"
            for chunk in chunks[:5]:  # Max 5 chunks per doc
                materials_context += f"  • Chunk {chunk['chunk_id']} (p.{chunk['page']}): {chunk['preview']}...\n"
    
    # System prompt - flexible and RAG-aware
    system_prompt = f"""You are StudyPlanner, a flexible, human-aware study planning agent.

**CRITICAL: Follow the EXACT timeline provided below. Do NOT invent different timelines.**

**Core Responsibilities:**
1. **Follow Timeline Exactly**: Use the exact number of days/hours specified. If timeline says "2 days", create a 2-day plan, NOT 7 days or 30 days.
2. Use retrieval (RAG) whenever course materials are available:
   • Reference specific chunks: "Study Chunk 5 (Linear Algebra, p.12-15)"
   • Cite pages and sections: "Review pages 20-25"
   • Use material titles in recommendations
3. Adjust format to timeline:
   • 1-3 hours → Single session breakdown
   • 2-5 days → Day-by-day schedule
   • 1+ weeks → Weekly structure with daily breakdown
4. Stay practical:
   • Use realistic time blocks (45-90 min study sessions)
   • Include 10-min breaks after every 90 minutes
   • Reference actual uploaded materials
5. Be concise and actionable:
   • Clean markdown for frontend
   • Natural language, not overly formal
   • Specific, practical actions

**RAG Usage (REQUIRED when materials available):**
• Identify topics, sections, titles from chunks
• Build plan that references specific material:
  - "Study Chunk 3 about Linear Algebra (p.12-15)"
  - "Review 'Gradient Descent' in Chunks 7-9"
  - "Practice problems from Chunk 12"
• If NO materials: Create general plan but note that uploading materials will improve recommendations

**Output Format Examples:**

For 1-3 hours:
```
## Study Session: [Topic]
**Duration:** {time_info['days']} day, {time_info['hours_per_day']} hours

### Time Breakdown
• 0:00-0:45 → Study [Topic from Chunk X]
• 0:45-1:00 → Break
• 1:00-1:45 → [Next activity]
```

For 2-5 days:
```
## Study Plan: [Topic]
**Timeline:** {time_info['days']} days, {time_info['hours_per_day']} hrs/day

### Day 1
• Study: Chunk X, Y (pages A-B)
• Practice: [Exercises]

### Day 2
• Review: Previous concepts
• New: Chunk Z (pages C-D)
```

**REMEMBER**: Create a plan for EXACTLY {time_info['days']} days at {time_info['hours_per_day']} hours/day."""

    # User prompt with all context
    print(f"[PLANNER] Timeline: {time_info['days']} days, {time_info['hours_per_day']} hrs/day (Source: {time_info['source']})")
    print(f"[PLANNER] Total hours: {time_info['total_hours']}")
    print(f"[PLANNER] Materials available: {len(retrieval_results)} chunks")
    
    user_prompt = f"""User Request: {query}

**IMPORTANT - FOLLOW THIS TIMELINE EXACTLY:**
- Number of days: {time_info['days']}
- Hours per day: {time_info['hours_per_day']}
- Total hours: {time_info['total_hours']}
- Description: {time_info['description']}

**DO NOT create a plan for a different number of days. Use EXACTLY {time_info['days']} days.**

**Student Context:**
{user_context_str}
{materials_context}

Generate a practical, actionable study plan for EXACTLY {time_info['days']} days at {time_info['hours_per_day']} hours per day. Reference the specific chunks/pages from the available materials."""
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
        max_tokens=2500
    )
    
    return response.choices[0].message.content


def _parse_time_from_query(query: str, deadline: Optional[str], hours_per_day: int) -> Dict:
    """
    Parse flexible time expressions from natural language.
    
    Examples:
    - "2 hour plan" → 2 hours total
    - "7 day plan, 2 hrs/day" → 7 days, 2 hrs/day
    - "help me for next week" → 7 days
    - "I have a month" → 30 days
    """
    import re
    from datetime import datetime, timedelta
    
    query_lower = query.lower()
    print(f"[TIME_PARSE] Parsing: '{query}'")
    print(f"[TIME_PARSE] Deadline: {deadline}, Hours/day: {hours_per_day}")
    
    # Validate and clean deadline
    valid_deadline = None
    if deadline and deadline.lower() not in ['string', 'null', 'none', '']:
        try:
            valid_deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            print(f"[TIME_PARSE] Valid deadline parsed: {valid_deadline}")
        except Exception as e:
            print(f"[TIME_PARSE] Invalid deadline '{deadline}': {e}")
            valid_deadline = None
    
    # Try to extract hours from query (for single-session plans)
    hour_match = re.search(r'(\d+)\s*(?:hour|hr|hours|hrs)(?!\s*(?:per|/|each))', query_lower)
    if hour_match:
        total_hours = int(hour_match.group(1))
        print(f"[TIME_PARSE] Found hours: {total_hours}")
        return {
            'days': 1,
            'hours_per_day': total_hours,
            'total_hours': total_hours,
            'description': f"{total_hours} hours today",
            'source': 'query_hours'
        }
    
    # Try to extract days from query (priority over deadline)
    day_match = re.search(r'(\d+)\s*(?:day|days)', query_lower)
    if day_match:
        days = int(day_match.group(1))
        # Try to find hours per day
        hrs_match = re.search(r'(\d+)\s*(?:hour|hr|hours|hrs)(?:\s*(?:per|/|each)\s*day)?', query_lower)
        if hrs_match and 'per' in query_lower or '/' in query_lower or 'each' in query_lower:
            hrs = int(hrs_match.group(1))
        else:
            hrs = hours_per_day or 2
        
        print(f"[TIME_PARSE] Found days: {days}, hours/day: {hrs}")
        return {
            'days': days,
            'hours_per_day': hrs,
            'total_hours': days * hrs,
            'description': f"{days} days, {hrs} hours/day ({days * hrs} total hours)",
            'source': 'query_days'
        }
    
    # Check for common time expressions
    if 'week' in query_lower:
        days = 7
        hrs = hours_per_day or 2
        print(f"[TIME_PARSE] Found 'week': {days} days")
        return {
            'days': days,
            'hours_per_day': hrs,
            'total_hours': days * hrs,
            'description': f"1 week, {hrs} hours/day ({days * hrs} total hours)",
            'source': 'query_week'
        }
    
    if 'month' in query_lower:
        days = 30
        hrs = hours_per_day or 2
        print(f"[TIME_PARSE] Found 'month': {days} days")
        return {
            'days': days,
            'hours_per_day': hrs,
            'total_hours': days * hrs,
            'description': f"1 month, {hrs} hours/day ({days * hrs} total hours)",
            'source': 'query_month'
        }
    
    # Use valid deadline if provided and no time found in query
    if valid_deadline:
        days_until = max(1, (valid_deadline - datetime.now()).days)
        hrs = hours_per_day or 2
        print(f"[TIME_PARSE] Using deadline: {days_until} days")
        return {
            'days': days_until,
            'hours_per_day': hrs,
            'total_hours': days_until * hrs,
            'description': f"{days_until} days until deadline, {hrs} hours/day",
            'source': 'deadline'
        }
    
    # Default fallback
    default_days = 7
    default_hrs = hours_per_day or 2
    print(f"[TIME_PARSE] Using default: {default_days} days")
    return {
        'days': default_days,
        'hours_per_day': default_hrs,
        'total_hours': default_days * default_hrs,
        'description': f"{default_days} days, {default_hrs} hours/day (default)",
        'source': 'default'
    }


def generate_flashcards(query: str, context: str, num_cards: int) -> str:
    """Generate spaced-repetition flashcards."""
    system_prompt = f"""You are creating flashcards for spaced repetition learning.

Create {num_cards} concise, focused flashcards.

**Formats:**
1. Q&A: Question → Answer
2. Cloze: The {{{{c1::answer}}}} format

**Output:**
## Flashcard Set: [Topic]

### Card 1 (Q&A)
**Front:** [Question]
**Back:** [Answer with brief explanation]
**Tags:** #concept1 #concept2
**Difficulty:** 2/5
**Source:** (Title, p.X)

### Card 2 (Cloze)
**Text:** The {{{{c1::base case}}}} prevents infinite recursion.
**Tags:** #recursion
**Difficulty:** 1/5
**Source:** (Title, p.Y)

## Spaced Repetition Schedule
- Day 1: Review all cards
- Day 3: Review cards 1, 3, 5
- Day 7: Review difficult cards
- Day 14: Review all"""

    user_prompt = f"Create {num_cards} flashcards for: {query}\n\nContext:\n{context}"
    
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2048
    )
    
    return response.choices[0].message.content


def process_request(
    query: str,
    user_id: str,
    course_id: str,
    mode: Optional[str] = None,
    difficulty: str = "medium",
    num_questions: int = 6,
    num_items: Optional[int] = None,
    top_k: int = 8,
    deadline: Optional[str] = None,
    hours_per_day: int = 2,
    **kwargs
) -> Dict:
    """
    Main entry point for processing requests.
    
    Args:
        query: User's query
        user_id: User identifier
        course_id: Course identifier
        mode: Optional mode hint (quiz, plan, guide, etc.)
        difficulty: Quiz difficulty (easy, medium, hard)
        num_questions: Number of quiz questions
        num_items: Generic num items (for flashcards, etc.)
        top_k: Number of retrieval results
        deadline: Study plan deadline
        hours_per_day: Daily study hours for planning
        
    Returns:
        Response dict with ok, content, agent, routing, thought_process
    """
    print(f"\n[ORCHESTRATOR] Processing query: '{query[:50]}...'")
    print(f"[ORCHESTRATOR] Mode hint: {mode}")
    
    # Step 1: Route the request
    routing = route_request(query, mode_hint=mode)
    print(f"[ROUTING] Agent: {routing.agent}, Type: {routing.response_type}")
    print(f"[ROUTING] Reasoning: {routing.reasoning}")
    
    # Step 2: Load user stats and memory
    user_stats = db.get_stats(user_id, course_id)
    memory = load_memory(user_id, course_id)
    
    # Step 3: Retrieve course materials (if needed)
    retrieval_results = []
    context_str = ""
    citations = []
    
    # Planner now uses RAG when available for material-aware planning
    if routing.requires_retrieval or routing.agent == "planner":
        print(f"[RAG] Retrieving top {top_k} chunks...")
        retrieval_results = hybrid_retrieve(user_id, course_id, query, k=top_k)
        print(f"[RAG] Retrieved {len(retrieval_results)} chunks")
        
        if retrieval_results:
            context_str = format_context_for_llm(retrieval_results)
            citations = extract_citations(retrieval_results)
        else:
            print("[RAG] No relevant materials found")
    
    # Step 4: Generate response based on routing decision
    content = ""
    thought_process = [
        {
            "step": "routing",
            "decision": {
                "agent": routing.agent,
                "response_type": routing.response_type,
                "reasoning": routing.reasoning,
                "confidence": routing.confidence
            }
        },
        {
            "step": "retrieval",
            "results": {
                "count": len(retrieval_results),
                "avg_score": sum(h.get('score', 0) for h in retrieval_results) / len(retrieval_results) if retrieval_results else 0.0
            }
        }
    ]
    
    try:
        if routing.response_type == "summary":
            if not retrieval_results:
                content = "**No materials found to summarize.**\n\nPlease upload course materials first."
            else:
                content = generate_summary(query, context_str)
                
        elif routing.response_type == "guide":
            if not retrieval_results:
                content = "**No materials found for study guide.**\n\nPlease upload course materials first."
            else:
                content = generate_study_guide(query, context_str, user_stats)
                
        elif routing.response_type == "quiz":
            if not retrieval_results:
                content = "**No materials found for quiz generation.**\n\nPlease upload course materials first."
            else:
                content = generate_quiz(query, context_str, difficulty, num_questions, user_stats)
                
        elif routing.response_type == "plan":
            content = generate_study_plan(query, user_stats, deadline, hours_per_day, retrieval_results)
            
        elif routing.response_type == "flashcards":
            num_cards = num_items or 10
            if not retrieval_results:
                content = "**No materials found for flashcards.**\n\nPlease upload course materials first."
            else:
                content = generate_flashcards(query, context_str, num_cards)
                
        else:  # chat
            if not retrieval_results:
                content = """I don't have any course materials to reference for this question.

**To get started:**
1. Upload course materials (PDFs, documents)
2. Then ask your questions

I can help you with:
- Study guides and explanations
- Quizzes and practice tests
- Study plans and schedules
- Flashcards for review"""
            else:
                system_prompt = """You are a friendly study assistant.
Answer questions directly and conversationally.
Use the provided course materials as context.
Be helpful but concise."""
                
                user_prompt = f"{query}\n\nContext:\n{context_str}"
                
                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1024
                )
                content = response.choices[0].message.content
        
        thought_process.append({
            "step": "generation",
            "agent": routing.agent,
            "response_type": routing.response_type,
            "success": True
        })
        
    except Exception as e:
        print(f"[ERROR] Generation failed: {str(e)}")
        content = f"**Error generating response:** {str(e)}\n\nPlease try again or rephrase your question."
        thought_process.append({
            "step": "generation",
            "error": str(e),
            "success": False
        })
    
    # Step 5: Log the query
    log_query(user_id, course_id, query, routing.response_type)
    
    # Step 6: Return structured response
    return {
        "ok": True,
        "content": content,
        "agent": routing.agent,
        "routing": {
            "method": "llm_intent_detection",
            "agent": routing.agent,
            "response_type": routing.response_type,
            "reasoning": routing.reasoning,
            "confidence": routing.confidence,
            "mode_hint": mode
        },
        "thought_process": thought_process,
        "citations": citations,
        "context": {
            "user_id": user_id,
            "course_id": course_id,
            "retrieval_count": len(retrieval_results),
            "has_materials": len(retrieval_results) > 0
        }
    }


# Test function for debugging
if __name__ == "__main__":
    test_cases = [
        "Summarize chapter 3",
        "Create a study guide for binary trees",
        "Give me a quiz on data structures",
        "Help me plan my study schedule",
        "What is recursion?"
    ]
    
    for test_query in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_query}")
        routing = route_request(test_query)
        print(f"→ Agent: {routing.agent}")
        print(f"→ Type: {routing.response_type}")
        print(f"→ Reasoning: {routing.reasoning}")