import os, uuid
from typing import Optional, List, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .rag import upsert_pdf, hybrid_retrieve, get_collection_stats
from .tools import (
    study_guide, 
    quiz_from_context, 
    flashcards_from_context,
    analyze_progress,
    generate_study_plan
)
from . import memory as mem

app = FastAPI(
    title="StudyBuddy Pro",
    description="AI-powered study assistant with RAG, quizzes, and flashcards",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatReq(BaseModel):
    user_id: str
    course_id: str
    prompt: str
    mode: Optional[str] = "chat"
    top_k: Optional[int] = 8
    difficulty: Optional[str] = "medium"
    num_items: Optional[int] = None

class QuizSubmission(BaseModel):
    user_id: str
    course_id: str
    topic: str
    score: float
    total_questions: int
    difficulty: str
    answers: Optional[List[Dict]] = None

@app.get("/")
def root():
    return {
        "ok": True, 
        "message": "StudyBuddy Pro API",
        "version": "2.0.0",
        "endpoints": {
            "upload": "POST /ingest",
            "chat": "POST /chat",
            "stats": "GET /stats/{user_id}/{course_id}",
            "submit_quiz": "POST /submit-quiz"
        }
    }

@app.post("/ingest")
async def ingest_pdf(
    user_id: str = Form(...),
    course_id: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        doc_id = str(uuid.uuid4())[:8]
        dest = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")
        
        with open(dest, "wb") as f:
            f.write(await file.read())
        
        stats = upsert_pdf(user_id=user_id, course_id=course_id, doc_id=doc_id, title=title, path=dest)
        
        if stats["chunks"] == 0:
            return JSONResponse({"ok": False, "error": "Could not extract text from PDF", "doc_id": doc_id}, status_code=400)
        
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
def chat(req: ChatReq):
    try:
        if not req.prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
        hits = hybrid_retrieve(req.user_id, req.course_id, req.prompt, k=req.top_k)
        
        if not hits:
            return JSONResponse({
                "ok": False,
                "type": "error",
                "content_md": "## 📭 No relevant materials found\n\nI couldn't find any course materials related to your question.\n\n**Suggestions:**\n- 📤 Upload course materials using the file uploader\n- 🔄 Try rephrasing your question with different keywords\n- ✅ Check if you're in the correct course\n",
                "suggestions": ["Upload lecture notes or textbook chapters", "Try broader search terms", "Break complex questions into smaller parts"],
                "citations": []
            })
        
        avg_score = sum(h.get('score', 0) for h in hits) / len(hits)
        
        if req.mode == "guide":
            result = study_guide(req.prompt, hits)
        elif req.mode == "quiz":
            num_q = req.num_items or 6
            result = quiz_from_context(req.prompt, hits, num_q=num_q, difficulty=req.difficulty)
        elif req.mode == "flashcards":
            num_cards = req.num_items or 10
            result = flashcards_from_context(req.prompt, hits, num_cards=num_cards)
        else:
            result = study_guide(f"Briefly answer: {req.prompt}", hits)
            result["type"] = "chat"
        
        mem.log_query(req.user_id, req.course_id, req.prompt, req.mode)
        
        if avg_score < 0.4:
            result["warning"] = "⚠️ Low confidence in results. Consider uploading more materials or rephrasing your question."
            result["suggestions"] = ["Try more specific search terms", "Upload additional course materials", "Break your question into smaller parts"]
        
        result["ok"] = True
        result["retrieval_quality"] = "high" if avg_score > 0.7 else "medium" if avg_score > 0.4 else "low"
        
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/stats/{user_id}/{course_id}")
def get_stats(user_id: str, course_id: str):
    try:
        m = mem.load(user_id, course_id)
        stats = mem.get_stats(user_id, course_id)
        collection_stats = get_collection_stats(user_id, course_id)
        
        return {
            "ok": True,
            "user_id": user_id,
            "course_id": course_id,
            "stats": {
                **stats,
                "docs_uploaded": collection_stats["total_documents"],
                "total_chunks": collection_stats["total_chunks"],
                "doc_ids": collection_stats["doc_ids"],
                "created_at": m.get("created_at"),
                "last_updated": m.get("last_updated")
            },
            "progress": analyze_progress(m, m.get("quiz_history", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.post("/submit-quiz")
def submit_quiz(submission: QuizSubmission):
    try:
        if not 0.0 <= submission.score <= 1.0:
            raise HTTPException(status_code=400, detail="Score must be between 0.0 and 1.0")
        
        mem.log_quiz_attempt(
            submission.user_id, submission.course_id, submission.topic,
            submission.score, submission.total_questions, submission.difficulty
        )
        
        stats = mem.get_stats(submission.user_id, submission.course_id)
        topic_mastery = stats["mastery_scores"].get(submission.topic, {})
        
        if submission.score >= 0.9:
            feedback = "🌟 Excellent! You've mastered this topic."
            next_step = "Try a harder difficulty or explore advanced concepts."
        elif submission.score >= 0.7:
            feedback = "✅ Good job! You have a solid understanding."
            next_step = "Review any missed questions and practice more."
        elif submission.score >= 0.5:
            feedback = "📚 Making progress, but needs more review."
            next_step = "Go through the study guide again."
        else:
            feedback = "💪 Keep practicing! This is challenging material."
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
                "attempts": len(topic_mastery.get("scores", []))
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quiz submission failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)