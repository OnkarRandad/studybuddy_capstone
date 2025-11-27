"""
StudyBuddy Pro v3.0 - AgentPro ReAct Architecture with Intelligent Routing
Uses LLM-based orchestration for proper intent detection and routing.
"""

import os
from agentpro_app.config import OPENAI_API_KEY

print("[DEBUG] Loaded key:", OPENAI_API_KEY[:10] + "..." if OPENAI_API_KEY else "NO KEY")

import uuid
from typing import Optional, List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import traceback

from agentpro_app.rag import upsert_pdf, get_collection_stats
from agentpro_app.persistence import database as db
from agentpro_app.improved_orchestrator import process_request, route_request

# Directory for uploaded PDF files
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI(
    title="StudyBuddy Pro v3.0 - AgentPro ReAct",
    description="Multi-agent AI study assistant with intelligent LLM-based routing",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db.init_db()


class ChatRequest(BaseModel):
    user_id: str
    course_id: str
    prompt: str
    mode: Optional[str] = None  # Now optional - let LLM decide
    top_k: Optional[int] = 8
    difficulty: Optional[str] = "medium"
    num_items: Optional[int] = None
    stream: Optional[bool] = False


class QuizSubmission(BaseModel):
    user_id: str
    course_id: str
    topic: str
    score: float
    total_questions: int
    difficulty: str
    answers: Optional[List[Dict]] = None


class PlanRequest(BaseModel):
    user_id: str
    course_id: str
    query: str = "Generate study plan"
    deadline: Optional[str] = None  # ISO format datetime or None
    hours_per_day: Optional[int] = 2
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "student123",
                "course_id": "cs101",
                "query": "Make me a 3 day study plan for data structures",
                "deadline": None,  # or "2025-12-01T00:00:00Z" for specific date
                "hours_per_day": 2
            }
        }


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("[STARTUP] StudyBuddy Pro v3.0 (Intelligent Routing) starting up...")
    print("[OK] Database initialized")
    print("[OK] LLM-based orchestrator ready")
    print("[OK] Intelligent routing enabled")


@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "ok": True,
        "message": "StudyBuddy Pro v3.0 - Intelligent LLM-based Routing",
        "version": "3.0.0",
        "architecture": "AgentPro ReAct with LLM Orchestration",
        "features": {
            "llm_routing": True,
            "intent_detection": True,
            "adaptive_learning": True,
            "persistence": "SQLite",
            "thought_process_tracking": True
        },
        "agents": {
            "assistant": "Summaries and basic Q&A",
            "tutor": "Comprehensive study guides",
            "quiz_coach": "Adaptive quiz generation",
            "planner": "Study planning and scheduling",
            "flashcards": "Spaced-repetition flashcards"
        },
        "routing": {
            "method": "LLM-based intent analysis",
            "fallback": "Assistant agent for unknown intents",
            "confidence_tracking": True
        },
        "endpoints": {
            "upload": "POST /ingest",
            "chat": "POST /chat (intelligent routing)",
            "stats": "GET /stats/{user_id}/{course_id}",
            "submit_quiz": "POST /submit-quiz",
            "study_plan": "POST /study-plan",
            "generate_quiz": "POST /generate-quiz"
        }
    }


@app.post("/ingest")
async def ingest_pdf(
    user_id: str = Form(...),
    course_id: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload and index a PDF document."""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        doc_id = str(uuid.uuid4())[:8]
        dest = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

        # Save file
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)

        # Process in background (for large PDFs)
        stats = await asyncio.to_thread(
            upsert_pdf,
            user_id=user_id,
            course_id=course_id,
            doc_id=doc_id,
            title=title,
            path=dest
        )

        if stats["chunks"] == 0:
            return JSONResponse(
                {"ok": False, "error": "Could not extract text from PDF", "doc_id": doc_id},
                status_code=400
            )

        return {
            "ok": True,
            "doc_id": doc_id,
            "title": title,
            "chunks": stats["chunks"],
            "message": f"Successfully indexed {stats['chunks']} chunks from '{title}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Intelligent chat endpoint with LLM-based routing.
    
    Automatically detects intent and routes to the appropriate agent:
    - Summaries → Assistant agent
    - Study guides → Tutor agent  
    - Quizzes → Quiz coach agent
    - General Q&A → Assistant agent
    - Planning → Planner agent
    """
    try:
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        # Process through intelligent orchestrator
        response = await asyncio.to_thread(
            process_request,
            query=req.prompt,
            user_id=req.user_id,
            course_id=req.course_id,
            mode=req.mode,  # Optional hint
            difficulty=req.difficulty,
            num_questions=req.num_items or 6,
            top_k=req.top_k
        )

        if not response.get("ok"):
            return JSONResponse({
                "ok": False,
                "error": response.get("error", "Processing failed")
            }, status_code=500)

        # Unified response format
        return JSONResponse({
            "ok": True,
            "type": response.get("routing", {}).get("response_type", "chat"),
            "content_md": response["content"],
            "agent_used": response.get("agent", "orchestrator"),
            "routing": {
                "method": "llm_intent_detection",
                "agent": response.get("routing", {}).get("agent", "assistant"),
                "response_type": response.get("routing", {}).get("response_type", "chat"),
                "reasoning": response.get("routing", {}).get("reasoning", ""),
                "confidence": response.get("routing", {}).get("confidence", 0.0),
                "mode_hint": req.mode,
                "auto_routed": req.mode is None
            },
            "thought_process": response.get("thought_process", []),
            "citations": response.get("citations", []),
            "context": response.get("context", {})
        })

    except HTTPException:
        raise
    except Exception as e:
        print("=== CHAT ENDPOINT ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/generate-quiz")
async def generate_quiz(req: ChatRequest):
    """
    Generate quiz - strong mode hint to force quiz generation.
    """
    try:
        # Force quiz mode with clear query
        query = req.prompt
        if "quiz" not in query.lower():
            query = f"Generate a quiz: {query}"
        
        response = await asyncio.to_thread(
            process_request,
            query=query,
            user_id=req.user_id,
            course_id=req.course_id,
            mode="quiz",  # Strong hint for quiz
            difficulty=req.difficulty,
            num_questions=req.num_items or 6
        )

        if not response.get("ok"):
            return JSONResponse({
                "ok": False,
                "error": response.get("error", "Quiz generation failed")
            }, status_code=500)

        # Unified response format
        return JSONResponse({
            "ok": True,
            "type": "quiz",
            "content_md": response["content"],
            "agent_used": response.get("agent", "quiz_coach"),
            "routing": response.get("routing", {}),
            "thought_process": response.get("thought_process", []),
            "citations": response.get("citations", []),
            "difficulty": req.difficulty,
            "num_questions": req.num_items or 6,
            "context": response.get("context", {})
        })

    except Exception as e:
        print("=== QUIZ GENERATION ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@app.post("/study-plan")
async def create_study_plan(req: PlanRequest):
    """
    Generate study plan - strong mode hint to force planning.
    """
    try:
        response = await asyncio.to_thread(
            process_request,
            query=req.query,
            user_id=req.user_id,
            course_id=req.course_id,
            mode="plan",  # Strong hint for planning
            deadline=req.deadline,
            hours_per_day=req.hours_per_day
        )

        if not response.get("ok"):
            return JSONResponse({
                "ok": False,
                "error": response.get("error", "Study plan generation failed")
            }, status_code=500)

        # Unified response format
        return JSONResponse({
            "ok": True,
            "type": "study_plan",
            "content_md": response["content"],
            "agent_used": response.get("agent", "planner"),
            "routing": response.get("routing", {}),
            "thought_process": response.get("thought_process", []),
            "deadline": req.deadline,
            "hours_per_day": req.hours_per_day,
            "context": response.get("context", {})
        })

    except Exception as e:
        print("=== STUDY PLAN ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Study plan generation failed: {str(e)}")


@app.get("/stats/{user_id}/{course_id}")
async def get_stats(user_id: str, course_id: str):
    """Get comprehensive user statistics."""
    try:
        stats = await asyncio.to_thread(db.get_stats, user_id, course_id)
        collection_stats = await asyncio.to_thread(get_collection_stats, user_id, course_id)

        return {
            "ok": True,
            "user_id": user_id,
            "course_id": course_id,
            "stats": {
                **stats,
                "docs_uploaded": collection_stats["total_documents"],
                "total_chunks": collection_stats["total_chunks"],
                "doc_ids": collection_stats["doc_ids"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


@app.post("/submit-quiz")
async def submit_quiz(submission: QuizSubmission):
    """Submit quiz results and update mastery tracking."""
    try:
        if not 0.0 <= submission.score <= 1.0:
            raise HTTPException(status_code=400, detail="Score must be between 0.0 and 1.0")

        # Log quiz attempt
        await asyncio.to_thread(
            db.log_quiz_attempt,
            submission.user_id,
            submission.course_id,
            submission.topic,
            submission.score,
            submission.total_questions,
            submission.difficulty,
            submission.answers
        )

        # Get updated stats
        stats = await asyncio.to_thread(db.get_stats, submission.user_id, submission.course_id)
        topic_mastery = stats["mastery_scores"].get(submission.topic, {})

        # Generate feedback
        if submission.score >= 0.9:
            feedback = "🎉 EXCELLENT! You've mastered this topic."
            next_step = "Try a harder difficulty or explore advanced concepts."
        elif submission.score >= 0.7:
            feedback = "✅ GOOD! You have a solid understanding."
            next_step = "Review any missed questions and practice more."
        elif submission.score >= 0.5:
            feedback = "📈 PROGRESS! Making progress, but needs more review."
            next_step = "Go through the study guide again."
        else:
            feedback = "💪 PRACTICE! Keep practicing! This is challenging material."
            next_step = "Start with fundamentals and work through examples slowly."

        return {
            "ok": True,
            "message": "Quiz attempt logged successfully",
            "score": submission.score,
            "percentage": f"{submission.score * 100:.0f}%",
            "feedback": feedback,
            "next_step": next_step,
            "mastery_update": {
                "topic": submission.topic,
                "average_score": topic_mastery.get("avg", 0.0),
                "attempts": topic_mastery.get("attempts", 0)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")


@app.get("/agents")
async def list_agents():
    """List available agents and their capabilities."""
    return {
        "ok": True,
        "architecture": "AgentPro ReAct with LLM Orchestration",
        "routing": "Intelligent LLM-based intent detection",
        "agents": {
            "orchestrator": {
                "name": "Orchestrator",
                "role": "Intelligent routing based on intent analysis",
                "tools": ["RouterTool", "RAGTool", "MemoryTool"],
                "capabilities": ["intent_detection", "routing_decision", "context_management"]
            },
            "assistant": {
                "name": "General Assistant",
                "role": "Summaries, basic Q&A, conversational responses",
                "tools": ["AssistantTool", "RAGTool"],
                "modes": ["summary", "chat"]
            },
            "tutor": {
                "name": "Tutor Agent",
                "role": "Comprehensive study guides and detailed explanations",
                "tools": ["StudyGuideTool", "RAGTool", "MemoryTool"],
                "modes": ["guide"]
            },
            "quiz_coach": {
                "name": "Quiz Coach Agent",
                "role": "Adaptive quiz generation",
                "tools": ["QuizGeneratorTool", "RAGTool", "MemoryTool"],
                "modes": ["quiz"]
            },
            "planner": {
                "name": "Planner Agent",
                "role": "Study planning and scheduling",
                "tools": ["PlannerTool", "MemoryTool"],
                "modes": ["plan"]
            }
        }
    }


@app.get("/test-routing/{test_query}")
async def test_routing(test_query: str):
    """Test endpoint to see how queries get routed."""
    routing = route_request(test_query)
    
    return {
        "ok": True,
        "query": test_query,
        "routing_decision": {
            "agent": routing.agent,
            "response_type": routing.response_type,
            "reasoning": routing.reasoning,
            "confidence": routing.confidence,
            "requires_retrieval": routing.requires_retrieval
        },
        "explanation": f"Query '{test_query}' would be routed to '{routing.agent}' agent for '{routing.response_type}' response"
    }


@app.delete("/data/{user_id}/{course_id}")
async def delete_user_data(user_id: str, course_id: str):
    """Delete all user data for a course."""
    try:
        # Delete from database
        await asyncio.to_thread(db.delete_user_data, user_id, course_id)

        # Delete memory
        from agentpro_app.memory import _path
        import os
        mem_file = _path(user_id, course_id)
        if os.path.exists(mem_file):
            os.remove(mem_file)

        return {
            "ok": True,
            "message": f"All data deleted for user {user_id} in course {course_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data deletion failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)