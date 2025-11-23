# StudyBuddy Pro 2.0

AI-powered study assistant with RAG, hybrid search, quizzes, flashcards, and progress tracking.

## 🚀 Features

- **📚 Smart Document Processing**: Upload PDFs with intelligent chunking and hybrid retrieval (semantic + keyword)
- **💬 Multiple Study Modes**:
  - Quick answers
  - Comprehensive study guides
  - Auto-generated quizzes with answer keys
  - Spaced-repetition flashcards
- **📊 Progress Tracking**: Mastery scores, weak/strong topic identification, quiz history
- **🎯 Personalized Recommendations**: AI-powered study suggestions based on performance
- **🔍 Rich Citations**: Every answer includes source references with page numbers and relevance scores

## 🏗️ Architecture

```
StudyBuddy Pro
├── FastAPI Backend (main.py)
├── Hybrid RAG System (rag.py)
│   ├── Dense retrieval (OpenAI embeddings)
│   ├── BM25 keyword search
│   └── MMR deduplication
├── AI Tools (tools.py)
│   ├── Study guide generator
│   ├── Quiz generator
│   ├── Flashcard generator
│   └── Progress analyzer
├── Progress Agent (progress_agent.py)
│   └── AgentPro-compatible tool
└── Memory System (memory.py)
    ├── Quiz history tracking
    ├── Mastery scores
    └── Study patterns
```

## 📋 Prerequisites

- Python 3.8+
- OpenAI API key
- 4GB RAM minimum (for Chroma vectorstore)

## ⚙️ Installation

### 1. Clone or Download

```bash
# If you have the files
cd studybuddy-pro
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
CHAT_MODEL=gpt-4o-mini
MODEL_PROVIDER=openai

# Optional: for Claude
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# MODEL_PROVIDER=claude
```

### 5. Run the Server

```bash
uvicorn agentpro_app.main:app --reload --port 8080
```

Server will start at: http://localhost:8080

API docs: http://localhost:8080/docs

## 🎯 Quick Start

### 1. Upload a Document

```bash
curl -X POST http://localhost:8080/ingest \
  -F user_id=student1 \
  -F course_id=cs101 \
  -F title="Algorithms Chapter 3" \
  -F file=@chapter3.pdf
```

### 2. Get a Study Guide

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student1",
    "course_id": "cs101",
    "prompt": "binary search trees",
    "mode": "guide"
  }'
```

### 3. Generate a Quiz

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student1",
    "course_id": "cs101",
    "prompt": "sorting algorithms",
    "mode": "quiz",
    "difficulty": "medium",
    "num_items": 6
  }'
```

### 4. Create Flashcards

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student1",
    "course_id": "cs101",
    "prompt": "recursion",
    "mode": "flashcards",
    "num_items": 10
  }'
```

### 5. Check Progress

```bash
curl http://localhost:8080/stats/student1/cs101
```

### 6. Submit Quiz Results

```bash
curl -X POST http://localhost:8080/submit-quiz \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "student1",
    "course_id": "cs101",
    "topic": "binary search",
    "score": 0.83,
    "total_questions": 6,
    "difficulty": "medium"
  }'
```

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and API info |
| `/ingest` | POST | Upload and index a PDF |
| `/chat` | POST | Query with mode (chat/guide/quiz/flashcards) |
| `/stats/{user_id}/{course_id}` | GET | Get progress statistics |
| `/submit-quiz` | POST | Log quiz attempt |
| `/progress/analyze` | POST | Detailed progress analysis |
| `/study-plan` | POST | Generate study plan |
| `/data/{user_id}/{course_id}` | DELETE | Delete all user data |

## 🔧 Configuration

### Chat Modes

- **`chat`**: Quick, concise answers
- **`guide`**: Comprehensive study guides with examples and practice questions
- **`quiz`**: Auto-generated quizzes with answer keys and rationales
- **`flashcards`**: Spaced-repetition cards in Q&A and cloze formats

### Difficulty Levels

- **`easy`**: Basic concepts and definitions
- **`medium`**: Applied understanding (default)
- **`hard`**: Complex analysis and edge cases

### Retrieval Parameters

- **`top_k`**: Number of chunks to retrieve (default: 8)
- **`alpha`**: Dense vs BM25 weight (0.7 = 70% semantic, 30% keyword)
- **`threshold`**: Minimum similarity score (default: 0.3)

## 🧪 Testing

Run the test suite:

```bash
# Test document ingestion
./tests/test_ingest.sh

# Test all modes
./tests/test_chat_modes.sh

# Test progress tracking
./tests/test_progress.sh
```

## 📊 Progress Tracking

StudyBuddy Pro tracks:

- **Study Streak**: Number of queries/sessions
- **Quiz Performance**: Scores, trends, and mastery levels
- **Weak Topics**: Areas needing review (< 60% avg)
- **Strong Topics**: Mastered areas (> 80% avg)
- **Mastery Scores**: Per-topic averages with trend analysis

### Mastery Levels

- 🔴 **Needs Review**: < 60% average
- 🟡 **Proficient**: 60-80% average
- 🟢 **Mastered**: > 80% average

## 🤖 Using ProgressAgent with AgentPro

The ProgressAgent can be integrated with AgentPro's ReAct loop:

```python
from agentpro import ReactAgent, create_model
from agentpro_app.progress_agent import ProgressAgentTool

model = create_model(provider="openai", model_name="gpt-4o")
tools = [ProgressAgentTool()]

agent = ReactAgent(model=model, tools=tools)

response = agent.run(
    "Analyze progress for student1 in cs101 and suggest next steps"
)

print(response.final_answer)
```

## 🗂️ Project Structure

```
agentpro_app/
├── __init__.py
├── main.py                 # FastAPI server
├── rag.py                  # Hybrid retrieval system
├── tools.py                # AI generation tools
├── memory.py               # Progress tracking
├── progress_agent.py       # AgentPro tool
├── uploads/                # Uploaded PDFs
├── vectorstore/            # Chroma database
└── memory/                 # User progress JSON files
```

## 🔐 Security Notes

- **Development only**: This setup is for prototyping
- Never expose your API keys in code
- Add authentication before production deployment
- Consider rate limiting for public APIs

## 🚧 Roadmap

- [ ] Cross-encoder reranking
- [ ] Multi-modal support (images in PDFs)
- [ ] Study schedule generator
- [ ] Email/Slack notifications
- [ ] Collaborative study groups
- [ ] Mobile app integration
- [ ] LMS integration (Canvas, Blackboard)

## 🐛 Troubleshooting

### Chroma errors

```bash
# Reset vectorstore
rm -rf agentpro_app/vectorstore/
```

### Memory corruption

```bash
# Reset memory
rm -rf agentpro_app/memory/
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📝 License

MIT License - see LICENSE file

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📧 Support

- GitHub Issues: [Create an issue]
- Email: support@studybuddy.example.com
- Documentation: [Full docs]

---

Built with ❤️ using AgentPro, FastAPI, and OpenAI