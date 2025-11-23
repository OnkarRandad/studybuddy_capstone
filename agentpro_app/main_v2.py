"""
StudyBuddy Pro v2.0 - Multi-Agent FastAPI Backend
Enhanced with async operations, agent orchestration, and SQLite persistence.
"""

import os
from agentpro_app.config import OPENAI_API_KEY

print("[DEBUG] Loaded key:", OPENAI_API_KEY)

import uuid
from typing import Optional, List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import traceback

from .rag import upsert_pdf, hybrid_retrieve, get_collection_stats
from .persistence import database as db
from .agents.orchestrator import get_orchestrator, AgentContext
from .agents.quiz_coach_agent import QuizCoachAgent
from .persistence.database import get_chunks_for_course

# Directory for uploaded PDF files
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI(
    title="StudyBuddy Pro v2.0",
    description="Multi-agent AI study assistant with adaptive learning",
    version="2.0.0"
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

# Get orchestrator
orchestrator = get_orchestrator()


class ChatRequest(BaseModel):
    user_id: str
    course_id: str
    prompt: str
    mode: Optional[str] = "chat"
    top_k: Optional[int] = 8
    difficulty: Optional[str] = "medium"
    num_items: Optional[int] = None
    stream: Optional[bool] = False
    enable_chaining: Optional[bool] = True


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
    deadline: Optional[str] = None
    hours_per_day: Optional[int] = 2


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("[STARTUP] StudyBuddy Pro v2.0 starting up...")
    print("[OK] Database initialized")
    print("[OK] Agent orchestrator ready")
    print(f"[OK] {len(orchestrator.agents)} agents loaded")


@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "ok": True,
        "message": "StudyBuddy Pro v2.0 - Multi-Agent Edition",
        "version": "2.0.0",
        "features": {
            "multi_agent": True,
            "adaptive_learning": True,
            "persistence": "SQLite",
            "streaming": True
        },
        "agents": orchestrator.get_agent_capabilities(),
        "endpoints": {
            "upload": "POST /ingest",
            "chat": "POST /chat",
            "stats": "GET /stats/{user_id}/{course_id}",
            "submit_quiz": "POST /submit-quiz",
            "study_plan": "POST /study-plan"
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
    """Multi-agent chat endpoint with streaming support."""
    try:
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        # Retrieve relevant context
        hits = await asyncio.to_thread(
            hybrid_retrieve,
            req.user_id,
            req.course_id,
            req.prompt,
            k=req.top_k
        )

        if not hits:
            return JSONResponse({
                "ok": False,
                "type": "error",
                "content_md": "## No relevant materials found\n\nUpload course materials to get started.",
                "suggestions": ["Upload lecture notes", "Try broader search terms"],
                "citations": []
            })

        # Get user stats
        stats = await asyncio.to_thread(db.get_stats, req.user_id, req.course_id)

        # Build agent context
        context = AgentContext(
            user_id=req.user_id,
            course_id=req.course_id,
            query=req.prompt,
            mode=req.mode,
            retrieval_results=hits,
            user_stats=stats,
            memory_state={
                "last_queries": await asyncio.to_thread(
                    db.get_recent_queries,
                    req.user_id,
                    req.course_id
                )
            },
            metadata={
                "difficulty": req.difficulty,
                "num_items": req.num_items
            }
        )

        # Process through orchestrator
        responses = await orchestrator.process(context, enable_chaining=req.enable_chaining)

        # Log query
        await asyncio.to_thread(db.log_query, req.user_id, req.course_id, req.prompt, req.mode)

        # Format response
        output = orchestrator.format_responses(responses)

        return JSONResponse(output)

    except HTTPException:
        raise
    except Exception as e:
        print("=== CHAT ENDPOINT ERROR ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


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
            feedback = "[EXCELLENT] You've mastered this topic."
            next_step = "Try a harder difficulty or explore advanced concepts."
        elif submission.score >= 0.7:
            feedback = "[GOOD] You have a solid understanding."
            next_step = "Review any missed questions and practice more."
        elif submission.score >= 0.5:
            feedback = "[PROGRESS] Making progress, but needs more review."
            next_step = "Go through the study guide again."
        else:
            feedback = "[PRACTICE] Keep practicing! This is challenging material."
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")


@app.post("/study-plan")
async def generate_study_plan(req: PlanRequest):
    """Generate a personalized study plan."""
    try:
        # Get user stats
        stats = await asyncio.to_thread(db.get_stats, req.user_id, req.course_id)
        
        # Build context for planner agent
        context = AgentContext(
            user_id=req.user_id,
            course_id=req.course_id,
            query=req.query,
            mode='plan',
            retrieval_results=[],  # Planner doesn't need retrieval
            user_stats=stats,
            memory_state={},
            metadata={
                "deadline": req.deadline,
                "hours_per_day": req.hours_per_day
            }
        )
        
        # Process through planner agent
        responses = await orchestrator.process(context, enable_chaining=False)
        output = orchestrator.format_responses(responses)
        
        return JSONResponse(output)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")


@app.delete("/data/{user_id}/{course_id}")
async def delete_user_data(user_id: str, course_id: str):
    """Delete all user data for a course."""
    try:
        success = await asyncio.to_thread(db.delete_user_data, user_id, course_id)
        
        if success:
            return {"ok": True, "message": "All user data deleted successfully"}
        else:
            return {"ok": False, "message": "No data found for this user/course"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@app.get("/agents")
async def get_agents():
    """Get information about available agents."""
    return {
        "ok": True,
        "agents": orchestrator.get_agent_capabilities()
    }


from fastapi import Request

@app.post("/generate_quiz")
async def generate_quiz(request: Request):
    try:
        payload = await request.json()
        user_id = payload.get("user_id")
        course_id = payload.get("course_id")
        num_questions = int(payload.get("num_questions", 5))
        difficulty = (payload.get("difficulty") or "medium").lower()

        if not user_id or not course_id:
            raise HTTPException(status_code=400, detail="user_id and course_id are required")

        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"

        query = (
            "Create a comprehensive practice quiz covering the most important concepts for this course."
        )

        # Retrieve course materials
        hits = await asyncio.to_thread(
            hybrid_retrieve,
            user_id,
            course_id,
            query,
            max(num_questions * 3, 8),
        )

        if not hits:
            raise HTTPException(
                status_code=400,
                detail="No course materials found. Upload PDFs before generating a quiz.",
            )

        quiz_coach = QuizCoachAgent()

        # Normalize hits into a list of dicts with "text" keys
        normalized_hits = []
        for h in hits:
            if isinstance(h, dict):
                normalized_hits.append({"text": h.get("text", ""), **h})
            else:
                normalized_hits.append({"text": str(h)})

        # Generate quiz
        quiz = await asyncio.to_thread(
            quiz_coach.generate_quiz,
            normalized_hits,
            num_questions,
            difficulty,
        )

        return quiz

    except HTTPException:
        raise
    except Exception as e:
        print("QUIZ ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)