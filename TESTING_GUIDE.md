# 🧪 Testing Guide - StudyBuddy AgentPro ReAct

This guide shows you how to test the new AgentPro ReAct architecture.

---

## 🚀 Step 1: Start the Server

```bash
# Navigate to the app directory
cd /home/user/studybuddy_capstone/agentpro_app

# Start the FastAPI server
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
[STARTUP] StudyBuddy Pro v3.0 (AgentPro ReAct) starting up...
[OK] 4 specialized agents loaded
[OK] LLM-based routing enabled
```

---

## 🧪 Step 2: Run Automated Tests

### Option A: Python Test Script (Recommended)

```bash
# From the repository root
python test_api.py
```

This will:
- ✅ Check server health
- ✅ List all agents
- ✅ Test chat with LLM routing
- ✅ Generate a quiz
- ✅ Create a study plan
- ✅ Fetch user statistics
- ✅ Show ReAct thought process

### Option B: Bash Script (Quick Test)

```bash
# From the repository root
./test_api.sh
```

### Option C: Manual cURL Commands

See commands below ⬇️

---

## 📄 Step 3: Upload a Test PDF

### Create a Simple Test PDF

You can:
1. **Use any existing PDF** (lecture notes, textbook chapter, etc.)
2. **Create a test PDF** with programming content about recursion, data structures, etc.

### Upload via cURL

```bash
curl -X POST http://localhost:8000/ingest \
  -F "user_id=test_user" \
  -F "course_id=CS101" \
  -F "title=Recursion Notes" \
  -F "file=@/path/to/your/document.pdf"
```

**Replace** `/path/to/your/document.pdf` with your actual PDF path.

**Expected Response:**
```json
{
  "ok": true,
  "doc_id": "abc123",
  "title": "Recursion Notes",
  "chunks": 42,
  "message": "Successfully indexed 42 chunks from 'Recursion Notes'"
}
```

---

## 💬 Step 4: Test Chat (LLM Routing)

### Without specifying mode (LLM decides):

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Explain recursion in programming",
    "mode": ""
  }'
```

**What happens:**
1. 🔍 RAG retrieves relevant chunks from uploaded PDF
2. 🧠 **RoutingTool (LLM) analyzes** the query and decides which agent to use
3. 🤖 Selected agent (likely **TutorAgent**) runs ReAct loop:
   - **Thought**: "I need to retrieve materials on recursion"
   - **Action**: `retrieve_materials`
   - **Observation**: [8 relevant chunks found]
   - **Thought**: "Now I'll generate a comprehensive study guide"
   - **Action**: `generate_study_guide`
   - **Observation**: [Study guide content]
   - **Final Answer**: Complete study guide with citations

**Response includes:**
```json
{
  "ok": true,
  "agent_used": "tutor",
  "content_md": "## Recursion Overview\n...",
  "thought_process": [
    {
      "thought": "I need to retrieve materials...",
      "action": {"action_type": "retrieve_materials", "input": {...}},
      "observation": {"result": "..."}
    },
    ...
  ]
}
```

---

## 📝 Step 5: Test Quiz Generation

```bash
curl -X POST http://localhost:8000/generate_quiz \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Generate a quiz on recursion",
    "difficulty": "medium",
    "num_items": 6
  }'
```

**What happens:**
1. Routes to **QuizCoachAgent**
2. ReAct loop:
   - Retrieves materials
   - Checks user's quiz history (from memory)
   - Generates quiz with adapted difficulty
   - Returns quiz with answer key

---

## 📅 Step 6: Test Study Plan

```bash
curl -X POST http://localhost:8000/study-plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "query": "Create a 2-week study plan for learning recursion",
    "hours_per_day": 2
  }'
```

**What happens:**
1. Routes to **PlannerAgent**
2. ReAct loop:
   - Reads user memory (weak/strong topics)
   - Analyzes progress (optional)
   - Creates personalized weekly schedule
   - Includes spaced repetition

---

## 🎴 Step 7: Test Flashcards

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Create flashcards for recursion",
    "mode": "flashcards"
  }'
```

**What happens:**
1. Routes to **FlashcardsAgent**
2. Generates Q&A and cloze deletion flashcards
3. Includes spaced repetition schedule

---

## 📊 Step 8: Check Statistics

```bash
curl http://localhost:8000/stats/test_user/CS101
```

**Shows:**
- Total queries
- Quizzes taken
- Weak/strong topics
- Documents uploaded
- Mastery scores

---

## 🧠 Step 9: See LLM Routing in Action

Try these queries **without specifying mode** to see LLM routing decide:

### Query 1: Should route to Tutor
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "I dont understand how base cases work in recursion",
    "mode": ""
  }'
```
**Expected**: Routes to `tutor` (explanation needed)

### Query 2: Should route to Quiz Coach
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Test my knowledge of recursion with some questions",
    "mode": ""
  }'
```
**Expected**: Routes to `quiz_coach` (testing requested)

### Query 3: Should route to Planner
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Help me schedule my study time for the next 2 weeks",
    "mode": ""
  }'
```
**Expected**: Routes to `planner` (scheduling needed)

---

## 🔍 Step 10: View ReAct Reasoning

Look for `thought_process` in the response:

```python
import requests
import json

response = requests.post("http://localhost:8000/chat", json={
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Explain recursion",
    "mode": ""
})

data = response.json()

# Print thought process
print("🧠 REACT REASONING PROCESS:")
for i, step in enumerate(data['thought_process'], 1):
    print(f"\nStep {i}:")
    if step.get('thought'):
        print(f"  💭 Thought: {step['thought']}")
    if step.get('action'):
        print(f"  ⚡ Action: {step['action']['action_type']}")
    if step.get('observation'):
        print(f"  👁️  Observation: {str(step['observation']['result'])[:100]}...")

print(f"\n✅ Final Answer:\n{data['content_md'][:300]}...")
```

---

## 🎯 Testing Checklist

- [ ] ✅ Server starts without errors
- [ ] ✅ Health check (`/`) returns 200
- [ ] ✅ Agents endpoint shows 4 agents
- [ ] ✅ PDF upload works and returns chunk count
- [ ] ✅ Chat without mode uses LLM routing
- [ ] ✅ Quiz generation works
- [ ] ✅ Study plan generation works
- [ ] ✅ Flashcards generation works
- [ ] ✅ Statistics endpoint returns data
- [ ] ✅ Thought process is visible in responses
- [ ] ✅ LLM routing selects correct agents

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Check if .env has OPENAI_API_KEY
cat .env
```

### "No relevant materials found"
- Upload a PDF first using the `/ingest` endpoint
- Make sure the PDF has extractable text (not just images)

### LLM errors
- Verify `OPENAI_API_KEY` is set in `.env`
- Check `CHAT_MODEL` is set (should be `gpt-4o-mini`)

### Import errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 📝 Sample Test PDFs

You can create simple test PDFs with content like:

**recursion_notes.md** (then convert to PDF):
```markdown
# Recursion in Programming

## What is Recursion?
Recursion is when a function calls itself to solve a problem.

## Base Case
Every recursive function needs a base case to stop infinite recursion.

## Example: Factorial
def factorial(n):
    if n == 0:  # Base case
        return 1
    return n * factorial(n-1)  # Recursive case

## Common Mistakes
- Forgetting the base case
- Incorrect base case logic
- Stack overflow from deep recursion
```

Convert to PDF:
```bash
# Using pandoc (if available)
pandoc recursion_notes.md -o recursion_notes.pdf

# Or use any Markdown to PDF converter online
```

---

## 🎉 Success Indicators

You'll know it's working when you see:

1. **LLM Routing**: Server logs show `[ROUTING] Selected agent: tutor - Reason: ...`
2. **ReAct Loop**: Response includes `thought_process` array
3. **Tools Executing**: Actions like `retrieve_materials`, `generate_study_guide` in thought steps
4. **Different Agents**: Different queries route to different agents automatically

---

## 📚 Next Steps

Once testing is successful:
1. Test with real course materials (upload actual PDFs)
2. Try complex multi-step queries
3. Test quiz submission and progress tracking
4. Connect the frontend
5. Monitor thought processes for optimization

**You're all set to test the AgentPro ReAct architecture!** 🚀
