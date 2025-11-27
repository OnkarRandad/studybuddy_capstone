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
    agent: str
    reasoning: str
    confidence: float
    requires_retrieval: bool
    response_type: str


def route_request(query: str, mode_hint: Optional[str] = None) -> RoutingDecision:
    """Use LLM to determine routing based on query intent."""
    system_prompt = """You are an intelligent routing system for a study assistant.

Analyze the user's request and determine the best agent and response type.

**Available Agents:**
- assistant: General questions, summaries, basic explanations
- tutor: Comprehensive study guides, detailed concept explanations
- quiz_coach: Quiz generation and assessment
- planner: Study planning and scheduling
- flashcards: Flashcard creation

**Response Types:**
- summary: Brief overview
- guide: Comprehensive study guide
- quiz: Assessment generation
- chat: Conversational response
- plan: Study schedule
- flashcards: Memory cards

**Routing Rules:**
1. "Summarize" → assistant + summary
2. "Study guide" or "explain" → tutor + guide
3. "Quiz" → quiz_coach + quiz
4. "Plan" or "schedule" → planner + plan
5. "Flashcards" → flashcards + flashcards
6. General questions → assistant + chat

Return ONLY valid JSON:
{
  "agent": "agent_name",
  "reasoning": "why this agent",
  "confidence": 0.9,
  "requires_retrieval": true,
  "response_type": "type"
}"""

    user_prompt = f"Route this request: '{query}'"
    if mode_hint:
        user_prompt += f"\n\nMode hint: {mode_hint}"
    
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
        return RoutingDecision(
            agent="assistant",
            reasoning="Default routing",
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
        text = h.get('text', '')[:400]
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
Focus on main points and key takeaways.
Keep responses brief and well-organized."""

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
2. Key Concepts with examples
3. Important Details
4. Practice Questions
5. Summary

Use inline citations: (Source, p.X)"""

    weak_topics = user_stats.get("weak_topics", [])
    personalization = ""
    if weak_topics:
        personalization = f"\n\nNote: Student needs help with: {', '.join(weak_topics)}"
    
    user_prompt = f"Create a study guide for: {query}\n\nMaterials:\n{context}{personalization}"
    
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
    system_prompt = f"""Create a {difficulty} quiz with {num_questions} multiple choice questions.

Format:
### Question [N]
[Question text]

A) [Option]
B) [Option]
C) [Option]
D) [Option]

**Correct Answer:** [Letter]
**Explanation:** [Why, with source]
**Source:** (Document, p.X)"""

    user_prompt = f"Create {num_questions} questions for: {query}\n\nContext:\n{context}"
    
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


def generate_study_plan(query: str, user_stats: Dict, deadline: Optional[str], hours_per_day: int, retrieval_results: List[Dict] = None) -> str:
    """Generate flexible, RAG-aware study plan."""
    from datetime import datetime
    import re
    
    time_info = _parse_time_from_query(query, deadline, hours_per_day)
    
    weak_topics = user_stats.get("weak_topics", [])
    strong_topics = user_stats.get("strong_topics", [])
    
    user_context = []
    if weak_topics:
        user_context.append(f"Weak areas: {', '.join(weak_topics[:3])}")
    if strong_topics:
        user_context.append(f"Strong areas: {', '.join(strong_topics[:3])}")
    
    user_context_str = "\n".join(user_context) if user_context else "New student"
    
    materials_context = ""
    if retrieval_results:
        materials_context = "\n\n**Available Materials:**\n"
        docs = {}
        for i, hit in enumerate(retrieval_results[:15], 1):
            title = hit.get('meta', {}).get('title', 'Document')
            page = hit.get('meta', {}).get('page', '?')
            text_preview = hit.get('text', '')[:150]
            
            if title not in docs:
                docs[title] = []
            docs[title].append({'chunk_id': i, 'page': page, 'preview': text_preview})
        
        for title, chunks in docs.items():
            materials_context += f"\n**{title}:**\n"
            for chunk in chunks[:5]:
                materials_context += f"  • Chunk {chunk['chunk_id']} (p.{chunk['page']}): {chunk['preview']}...\n"
    
    system_prompt = f"""You are StudyPlanner creating practical study schedules.

**CRITICAL: Use EXACTLY {time_info['days']} days at {time_info['hours_per_day']} hours/day.**

Format for {time_info['days']} days:

## Study Plan
**Timeline:** {time_info['days']} days, {time_info['hours_per_day']} hrs/day

### Day 1
• 0:00-0:45 → Study Chunk X (p.Y)
• 0:45-1:00 → Break
• 1:00-1:45 → Practice

Reference specific chunks and pages when available."""

    print(f"[PLANNER] Timeline: {time_info['days']} days, {time_info['hours_per_day']} hrs/day")
    print(f"[PLANNER] Materials: {len(retrieval_results) if retrieval_results else 0} chunks")
    
    user_prompt = f"""Request: {query}

**Timeline:** {time_info['days']} days, {time_info['hours_per_day']} hrs/day

**Student:** {user_context_str}
{materials_context}

Generate plan for EXACTLY {time_info['days']} days."""
    
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
    """Parse time expressions from natural language."""
    import re
    from datetime import datetime
    
    query_lower = query.lower()
    print(f"[TIME_PARSE] Parsing: '{query}'")
    
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
    
    day_match = re.search(r'(\d+)\s*(?:day|days)', query_lower)
    if day_match:
        days = int(day_match.group(1))
        hrs = hours_per_day or 2
        print(f"[TIME_PARSE] Found days: {days}")
        return {
            'days': days,
            'hours_per_day': hrs,
            'total_hours': days * hrs,
            'description': f"{days} days, {hrs} hours/day",
            'source': 'query_days'
        }
    
    if 'week' in query_lower:
        days = 7
        hrs = hours_per_day or 2
        return {'days': days, 'hours_per_day': hrs, 'total_hours': days * hrs, 'description': f"1 week", 'source': 'query_week'}
    
    if 'month' in query_lower:
        days = 30
        hrs = hours_per_day or 2
        return {'days': days, 'hours_per_day': hrs, 'total_hours': days * hrs, 'description': f"1 month", 'source': 'query_month'}
    
    default_days = 7
    default_hrs = hours_per_day or 2
    return {'days': default_days, 'hours_per_day': default_hrs, 'total_hours': default_days * default_hrs, 'description': f"default 7 days", 'source': 'default'}


def generate_flashcards(query: str, context: str, num_cards: int) -> str:
    """Generate flashcards."""
    system_prompt = f"""Create {num_cards} flashcards for spaced repetition.

Format:
### Card [N]
**Front:** [Question]
**Back:** [Answer]
**Source:** (Title, p.X)"""

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
    """Main entry point for processing requests."""
    print(f"\n[ORCHESTRATOR] Processing: '{query[:50]}...'")
    print(f"[ORCHESTRATOR] Mode: {mode}")
    
    routing = route_request(query, mode_hint=mode)
    print(f"[ROUTING] Agent: {routing.agent}, Type: {routing.response_type}")
    
    user_stats = db.get_stats(user_id, course_id)
    memory = load_memory(user_id, course_id)
    
    retrieval_results = []
    context_str = ""
    citations = []
    
    # FORCE RETRIEVAL (Fix for routing bug)
    if True:
        print(f"[RAG] Retrieving top {top_k} chunks...")
        retrieval_results = hybrid_retrieve(user_id, course_id, query, k=top_k)
        print(f"[RAG] Retrieved {len(retrieval_results)} chunks")
        
        if retrieval_results:
            context_str = format_context_for_llm(retrieval_results)
            citations = extract_citations(retrieval_results)
    
    content = ""
    thought_process = [
        {"step": "routing", "decision": {"agent": routing.agent, "response_type": routing.response_type}},
        {"step": "retrieval", "results": {"count": len(retrieval_results), "avg_score": sum(h.get('score', 0) for h in retrieval_results) / len(retrieval_results) if retrieval_results else 0.0}}
    ]
    
    try:
        if routing.response_type == "summary":
            content = generate_summary(query, context_str) if retrieval_results else "No materials found."
        elif routing.response_type == "guide":
            content = generate_study_guide(query, context_str, user_stats) if retrieval_results else "No materials found."
        elif routing.response_type == "quiz":
            content = generate_quiz(query, context_str, difficulty, num_questions, user_stats) if retrieval_results else "No materials found."
        elif routing.response_type == "plan":
            content = generate_study_plan(query, user_stats, deadline, hours_per_day, retrieval_results)
        elif routing.response_type == "flashcards":
            num_cards = num_items or 10
            content = generate_flashcards(query, context_str, num_cards) if retrieval_results else "No materials found."
        else:
            if not retrieval_results:
                content = "No course materials found. Please upload materials first."
            else:
                system_prompt = "You are a helpful study assistant. Answer using the provided materials."
                user_prompt = f"{query}\n\nContext:\n{context_str}"
                response = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.5,
                    max_tokens=1024
                )
                content = response.choices[0].message.content
        
        thought_process.append({"step": "generation", "agent": routing.agent, "success": True})
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        content = f"Error: {str(e)}"
        thought_process.append({"step": "generation", "error": str(e), "success": False})
    
    log_query(user_id, course_id, query, routing.response_type)
    
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