from typing import List, Dict, Optional
from openai import OpenAI
from agentpro_app.config import CHAT_MODEL, OPENAI_API_KEY

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Debug print for model
print("[DEBUG] Using model:", CHAT_MODEL)

def format_citations(hits: List[Dict]) -> str:
    """Format hits with inline citations for LLM context."""
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

def study_guide(query: str, hits: List[Dict]) -> Dict:
    """Generate comprehensive study guide with improved citations."""
    if not hits:
        return {
            "type": "study_guide",
            "content_md": "**No relevant materials found.**\n\nPlease upload course materials or try rephrasing your question.",
            "citations": [],
            "quality": "empty"
        }
    
    ctx = format_citations(hits)
    
    system = """You are an expert tutor creating comprehensive study guides.

**Instructions:**
1. Create well-structured, clear explanations with examples
2. Use bullet points, headings, and formatting for readability
3. Cite sources inline using format: (Title, p.X) after each claim
4. Include "Key Takeaways" and "Practice Questions" sections
5. If context is insufficient, note what's missing

**Format:**
## Topic Overview
[explanation with citations]

## Key Concepts
- Concept 1 (Source, p.X)
- Concept 2 (Source, p.Y)

## Examples
[worked examples]

## Key Takeaways
[summary bullets]

## Practice Questions
[2-3 questions to test understanding]
"""
    
    user = f"""Create a study guide for: **{query}**

**Context from course materials:**
{ctx}

Generate a complete, citation-rich study guide."""
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.3,
            max_tokens=2048
        )
        content = response.choices[0].message.content
    except Exception as e:
        return {
            "type": "study_guide",
            "content_md": f"**Error generating study guide:** {str(e)}",
            "citations": [],
            "quality": "error"
        }
    
    # Extract unique citations
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
    
    avg_score = sum(h.get('score', 0) for h in hits) / len(hits) if hits else 0
    quality = "high" if avg_score > 0.7 else "medium" if avg_score > 0.4 else "low"
    
    return {
        "type": "study_guide",
        "content_md": content,
        "citations": citations,
        "quality": quality,
        "avg_retrieval_score": avg_score
    }

def quiz_from_context(query: str, hits: List[Dict], num_q: int = 6, difficulty: str = "medium") -> Dict:
    """Enhanced quiz generation with answer keys and rationales."""
    if not hits:
        return {
            "type": "quiz",
            "content_md": "**Cannot generate quiz - no relevant materials found.**\n\nPlease upload course materials first.",
            "questions": [],
            "citations": [],
            "difficulty": difficulty
        }
    
    ctx = format_citations(hits)
    
    system = f"""You are an expert educator creating assessments.

**Instructions:**
1. Generate {num_q} questions at {difficulty} difficulty
2. Mix question types: Multiple Choice, True/False, Short Answer
3. Include answer key with detailed rationales
4. Cite page numbers for each question's source
5. Ensure questions test understanding, not just recall

**Output Format:**
## Quiz: [Topic]

### Question 1 (Multiple Choice)
**Q:** [Question text] _(Source, p.X)_

A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

### Question 2 (True/False)
**Q:** [Statement] _(Source, p.Y)_

### Question 3 (Short Answer)
**Q:** [Question requiring 2-3 sentence response] _(Source, p.Z)_

---

## Answer Key

**Q1:** B - [Detailed rationale explaining why B is correct and others are wrong] _(p.X)_

**Q2:** False - [Explanation with reasoning] _(p.Y)_

**Q3:** [Sample answer with key points] _(p.Z)_
"""
    
    user = f"""Create a {difficulty} quiz on: **{query}**

**Context:**
{ctx}

Generate {num_q} varied questions with complete answer key."""
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.4,
            max_tokens=2048
        )
        content = response.choices[0].message.content
    except Exception as e:
        return {
            "type": "quiz",
            "content_md": f"**Error generating quiz:** {str(e)}",
            "questions": [],
            "citations": [],
            "difficulty": difficulty
        }
    
    citations = [
        {
            "title": h['meta'].get('title', 'Document'),
            "page": h['meta'].get('page', '?'),
            "snippet": h.get('snippet', '')
        }
        for h in hits[:5]
    ]
    
    return {
        "type": "quiz",
        "content_md": content,
        "questions": [],
        "citations": citations,
        "difficulty": difficulty,
        "num_questions": num_q
    }

def flashcards_from_context(query: str, hits: List[Dict], num_cards: int = 10) -> Dict:
    """Generate spaced-repetition flashcards."""
    if not hits:
        return {
            "type": "flashcards",
            "content_md": "**Cannot generate flashcards - no relevant materials found.**",
            "cards": [],
            "citations": []
        }
    
    ctx = format_citations(hits)
    
    system = """You are creating flashcards for spaced repetition learning.

**Instructions:**
1. Create concise, focused flashcards (one concept per card)
2. Use two formats:
   - **Q&A**: Question on front, answer on back
   - **Cloze**: Fill-in-the-blank style with {{c1::answer}}
3. Include page citations
4. Tag each card with concept keywords
5. Rate difficulty (1-5 scale, 1=easiest)

**Output Format:**
## Flashcard Set: [Topic]

### Card 1 (Q&A)
**Front:** [Clear, specific question]
**Back:** [Concise answer with brief explanation]
**Tags:** #concept1 #concept2
**Difficulty:** 2/5
**Source:** (Title, p.X)

---

### Card 2 (Cloze)
**Text:** The {{c1::base case}} prevents infinite recursion by providing a {{c2::termination condition}}.
**Tags:** #recursion #fundamentals
**Difficulty:** 1/5
**Source:** (Title, p.Y)

---

## Spaced Repetition Schedule
- **Today (Day 1):** Review all cards
- **Day 3:** Review cards 1, 3, 5, 7, 9
- **Day 7:** Review cards with difficulty 3+
- **Day 14:** Review all cards again
"""
    
    user = f"""Create {num_cards} flashcards for: **{query}**

**Context:**
{ctx}

Generate varied flashcards (mix Q&A and cloze formats). Focus on key concepts and testable knowledge."""
    
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=0.3,
            max_tokens=2048
        )
        content = response.choices[0].message.content
    except Exception as e:
        return {
            "type": "flashcards",
            "content_md": f"**Error generating flashcards:** {str(e)}",
            "cards": [],
            "citations": []
        }
    
    citations = [
        {"title": h['meta'].get('title'), "page": h['meta'].get('page')}
        for h in hits[:3]
    ]
    
    return {
        "type": "flashcards",
        "content_md": content,
        "cards": [],
        "citations": citations,
        "num_cards": num_cards
    }

def analyze_progress(memory: Dict, quiz_history: List[Dict]) -> Dict:
    """Analyze learning progress and generate recommendations."""
    weak_topics = memory.get("weak_topics", [])
    strong_topics = memory.get("strong_topics", [])
    last_queries = memory.get("last_queries", [])
    mastery_scores = memory.get("mastery_scores", {})
    
    # Analyze query patterns
    topic_frequency = {}
    for q in last_queries:
        if isinstance(q, dict):
            query_text = q.get("query", "")
        else:
            query_text = str(q)
        
        words = query_text.lower().split()
        for word in words:
            if len(word) > 4:
                topic_frequency[word] = topic_frequency.get(word, 0) + 1
    
    frequent_topics = sorted(topic_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Generate recommendations
    recommendations = []
    
    if weak_topics:
        recommendations.append(f"📚 Review weak topics: {', '.join(weak_topics[:3])}")
    
    if len(quiz_history) > 0:
        recent_scores = [q.get('score', 0) for q in quiz_history[-5:]]
        avg_recent = sum(recent_scores) / len(recent_scores)
        
        if avg_recent < 0.6:
            recommendations.append("⚠️ Quiz scores are low - consider reviewing fundamentals")
        elif avg_recent > 0.85:
            recommendations.append("🎉 Excellent quiz performance! Try harder difficulty.")
    
    if strong_topics:
        recommendations.append(f"💪 Strong areas: {', '.join(strong_topics[:3])} - keep it up!")
    
    if len(last_queries) > 10:
        recommendations.append("🔥 Great progress! You've been actively studying.")
    elif len(last_queries) < 3:
        recommendations.append("💡 Start exploring more topics to build momentum.")
    
    # Mastery analysis
    mastery_insights = []
    for topic, data in mastery_scores.items():
        avg = data.get("avg", 0.0)
        if avg < 0.5:
            mastery_insights.append(f"🔴 {topic}: Needs work ({avg*100:.0f}%)")
        elif avg < 0.7:
            mastery_insights.append(f"🟡 {topic}: Developing ({avg*100:.0f}%)")
        else:
            mastery_insights.append(f"🟢 {topic}: Strong ({avg*100:.0f}%)")
    
    return {
        "frequent_topics": [t[0] for t in frequent_topics],
        "recommendations": recommendations,
        "mastery_insights": mastery_insights,
        "study_streak": len(last_queries),
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "summary": {
            "total_queries": len(last_queries),
            "quizzes_taken": len(quiz_history),
            "topics_mastered": len(strong_topics),
            "topics_to_review": len(weak_topics)
        }
    }

def generate_study_plan(memory: Dict, deadline: Optional[str] = None, hours_per_day: int = 2) -> Dict:
    """Generate a personalized study plan."""
    weak_topics = memory.get("weak_topics", [])
    strong_topics = memory.get("strong_topics", [])
    
    plan = {
        "type": "study_plan",
        "deadline": deadline,
        "daily_hours": hours_per_day
    }
    
    if weak_topics:
        plan["focus_areas"] = weak_topics[:3]
        plan["strategy"] = "Focus on weak topics with spaced repetition"
    elif strong_topics:
        plan["focus_areas"] = strong_topics
        plan["strategy"] = "Maintain strong areas and explore advanced topics"
    else:
        plan["focus_areas"] = ["Begin with fundamentals"]
        plan["strategy"] = "Start with core concepts and build foundation"
    
    plan["daily_tasks"] = [
        "Review flashcards (15 min)",
        "Read course materials (30 min)",
        "Practice problems (45 min)",
        "Take a practice quiz (30 min)"
    ]
    
    return plan