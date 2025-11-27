# StudyBuddy AgentPro ReAct Architecture

## Overview

StudyBuddy has been completely refactored to use the **AgentPro ReAct architecture**, replacing the previous rule-based routing system with LLM-powered reasoning agents.

## Architecture Changes

### Before (v2.0)
```
FastAPI → Rule-Based Orchestrator → Agents (Direct LLM Calls) → Response
```

### After (v3.0 - AgentPro ReAct)
```
FastAPI → ReAct Orchestrator → LLM Routing → Specialized ReactAgent → Tools (LLM Calls) →
Thought → Action → Observation → Final Answer
```

## Core Components

### 1. AgentPro Framework (`agentpro/`)

#### Base Classes
- **`agent.py`**: Core data structures
  - `Action`: Tool invocation with action_type and input
  - `Observation`: Result from tool execution
  - `ThoughtStep`: Single reasoning step (thought, action, observation)
  - `AgentResponse`: Complete response with thought process and final answer

- **`react_agent.py`**: ReactAgent implementation
  - Implements Thought → Action → Observation → Final Answer loop
  - Manages tool registry and execution
  - Parses LLM responses for actions and final answers
  - Maintains complete reasoning history

- **`tools/base_tool.py`**: Tool base class
  - All tools inherit from `Tool`
  - Required attributes: name, description, action_type, input_format
  - Abstract method: `run(input_data) -> str`

### 2. Tools (`agentpro/tools/`)

All functionality has been converted to Tools. **Agents never call LLMs directly** - only tools do.

#### RAG and Retrieval
- **`RAGTool`** (`rag_tool.py`)
  - Action type: `retrieve_materials`
  - Performs hybrid retrieval (dense + BM25)
  - Returns JSON with hits, scores, and quality assessment

#### Study Materials
- **`GenerateStudyGuideTool`** (`study_guide_tool.py`)
  - Action type: `generate_study_guide`
  - Creates comprehensive study guides with citations
  - Personalizes based on user stats (weak/strong topics)
  - **Contains LLM call** for guide generation

#### Assessment
- **`GenerateQuizTool`** (`quiz_tool.py`)
  - Action type: `generate_quiz`
  - Generates adaptive quizzes with answer keys
  - Adjusts difficulty based on user performance
  - **Contains LLM call** for quiz generation

#### Flashcards
- **`GenerateFlashcardsTool`** (`flashcards_tool.py`)
  - Action type: `generate_flashcards`
  - Creates Q&A and cloze deletion flashcards
  - Includes spaced repetition schedules
  - **Contains LLM call** for flashcard generation

#### Planning
- **`CreateStudyPlanTool`** (`planner_tool.py`)
  - Action type: `create_study_plan`
  - Generates weekly schedules with spaced repetition
  - Prioritizes weak topics (60%), strong (20%), new (20%)
  - **Contains LLM call** for plan generation

#### Progress Analysis
- **`AnalyzeProgressTool`** (`progress_tool.py`)
  - Action type: `analyze_progress`
  - Analyzes quiz performance and mastery trends
  - Identifies learning gaps
  - **Contains LLM call** for detailed insights (optional)

#### Memory
- **`MemoryReadTool`** (`memory_tool.py`)
  - Action type: `read_memory`
  - Retrieves user learning history and preferences
  - Returns JSON with weak/strong topics, quiz history, goals

- **`MemoryWriteTool`** (`memory_tool.py`)
  - Action type: `write_memory`
  - Updates user memory with new information

#### Orchestration
- **`RoutingTool`** (`routing_tool.py`) ⭐ **KEY INNOVATION**
  - Action type: `route`
  - **LLM-based intelligent routing** (replaces rule-based routing)
  - Analyzes query, mode, context, and user stats
  - Returns: `{"agent": "tutor|quiz_coach|planner|flashcards", "reasoning": "..."}`
  - **Contains LLM call** for routing decision

### 3. Specialized ReactAgents (`react_agents/`)

Each agent is configured with specific tools and a specialized system prompt.

#### TutorReActAgent (`tutor_agent.py`)
- **Purpose**: Study guides and explanations
- **Tools**: RAGTool, GenerateStudyGuideTool, MemoryReadTool
- **Process**:
  1. Retrieve materials
  2. Read user memory
  3. Generate personalized study guide
  4. Return final answer

#### QuizCoachReActAgent (`quiz_coach_agent.py`)
- **Purpose**: Adaptive quiz generation
- **Tools**: RAGTool, GenerateQuizTool, MemoryReadTool
- **Process**:
  1. Retrieve materials for questions
  2. Check performance history
  3. Generate quiz with adapted difficulty
  4. Return final answer

#### PlannerReActAgent (`planner_agent.py`)
- **Purpose**: Study planning and scheduling
- **Tools**: MemoryReadTool, AnalyzeProgressTool, CreateStudyPlanTool
- **Process**:
  1. Read user profile
  2. Analyze progress (optional)
  3. Create personalized study plan
  4. Return final answer

#### FlashcardsReActAgent (`flashcards_agent.py`)
- **Purpose**: Flashcard generation
- **Tools**: RAGTool, GenerateFlashcardsTool, MemoryReadTool
- **Process**:
  1. Retrieve materials
  2. Read user focus areas
  3. Generate flashcard set
  4. Return final answer

### 4. Orchestrator (`react_agents/orchestrator.py`)

The **OrchestratorAgent** is the entry point for all requests.

#### Key Features
1. **LLM-Based Routing**: Uses `RoutingTool` to decide which agent to use
2. **Context Building**: Prepares context with RAG results and user stats
3. **Agent Delegation**: Routes to appropriate ReactAgent
4. **Response Formatting**: Returns structured responses with thought process

#### Request Flow
```
1. User Request → FastAPI Endpoint
2. OrchestratorAgent.process()
3. RAG Retrieval (if needed)
4. Get User Stats from Database
5. RoutingTool.run() → LLM decides agent
6. Selected ReactAgent.run()
   ├─ Thought: "I need to retrieve materials"
   ├─ Action: {"action_type": "retrieve_materials", "input": {...}}
   ├─ Observation: [retrieval results]
   ├─ Thought: "Now I'll generate a study guide"
   ├─ Action: {"action_type": "generate_study_guide", "input": {...}}
   ├─ Observation: [study guide content]
   └─ Final Answer: [complete study guide]
7. Log Query to Database
8. Return Response with thought_process and final_answer
```

## FastAPI Endpoints (`main_v2.py`)

All endpoints now use the new ReAct pipeline:

### Core Endpoints
- **`POST /chat`**: General chat with LLM routing
  - Uses orchestrator to route to appropriate agent
  - Returns agent used, content, and thought process

- **`POST /generate_quiz`**: Quiz generation
  - Forces mode="quiz" to route to QuizCoachReActAgent
  - Supports adaptive difficulty

- **`POST /study-plan`**: Study plan generation
  - Forces mode="plan" to route to PlannerReActAgent
  - Includes deadline and hours_per_day

- **`POST /ingest`**: PDF upload and indexing (unchanged)

- **`GET /stats/{user_id}/{course_id}`**: User statistics (unchanged)

- **`POST /submit-quiz`**: Quiz submission (unchanged)

- **`GET /agents`**: List all agents and their capabilities

- **`DELETE /data/{user_id}/{course_id}`**: Delete user data

## Key Improvements

### 1. LLM-Based Orchestration ✅
- **Before**: Rule-based routing (mode → agent mapping)
- **After**: LLM analyzes query, context, and user stats to decide best agent
- **Benefit**: More intelligent routing, handles ambiguous requests

### 2. True ReAct Loop ✅
- **Before**: Agents produced content directly
- **After**: Agents use Thought → Action → Observation → Final Answer
- **Benefit**: Transparent reasoning, better debugging, chainable actions

### 3. All LLM Calls in Tools ✅
- **Before**: Agents called LLMs directly
- **After**: Only tools contain LLM calls
- **Benefit**: Clear separation of concerns, reusable tools

### 4. Tool-Based Architecture ✅
- **Before**: Monolithic agent methods
- **After**: Modular, reusable tools
- **Benefit**: Easy to add new tools, better testability

### 5. Transparent Reasoning ✅
- **Before**: Black box agent responses
- **After**: Complete thought process returned with every response
- **Benefit**: Debugging, user trust, educational value

## Preserved Capabilities ✅

All original StudyBuddy features are preserved:

1. ✅ **Adaptive Quizzes**: Still adapts difficulty based on performance
2. ✅ **Citation-Rich Study Guides**: Tools include citation formatting
3. ✅ **Flashcards with Spaced Repetition**: Full schedule generation
4. ✅ **Personalized Planning**: Prioritizes weak topics, includes deadlines
5. ✅ **Progress Tracking**: Mastery scores, quiz history, trends
6. ✅ **RAG Retrieval**: Hybrid dense + BM25 search
7. ✅ **Memory/Context**: User preferences, goals, learning patterns
8. ✅ **Mode Switching**: guide, quiz, plan, flashcards

## File Structure

```
agentpro_app/
├── agentpro/                      # AgentPro Framework
│   ├── __init__.py
│   ├── agent.py                   # ThoughtStep, Action, Observation, AgentResponse
│   ├── react_agent.py             # ReactAgent implementation
│   └── tools/
│       ├── __init__.py
│       ├── base_tool.py           # Tool base class
│       ├── rag_tool.py            # RAGTool
│       ├── study_guide_tool.py    # GenerateStudyGuideTool
│       ├── quiz_tool.py           # GenerateQuizTool
│       ├── flashcards_tool.py     # GenerateFlashcardsTool
│       ├── planner_tool.py        # CreateStudyPlanTool
│       ├── progress_tool.py       # AnalyzeProgressTool
│       ├── memory_tool.py         # MemoryReadTool, MemoryWriteTool
│       └── routing_tool.py        # RoutingTool (LLM-based routing)
├── react_agents/                  # ReactAgent-based Agents
│   ├── __init__.py
│   ├── tutor_agent.py             # TutorReActAgent
│   ├── quiz_coach_agent.py        # QuizCoachReActAgent
│   ├── planner_agent.py           # PlannerReActAgent
│   ├── flashcards_agent.py        # FlashcardsReActAgent
│   └── orchestrator.py            # OrchestratorAgent (top-level)
├── main_v2.py                     # FastAPI app (ReAct version)
├── main_v2_backup.py              # Old version backup
├── rag.py                         # RAG implementation (unchanged)
├── persistence/                   # Database layer (unchanged)
├── memory.py                      # Memory management (unchanged)
└── config.py                      # Configuration (unchanged)
```

## Migration Notes

### Removed Files (Old Architecture)
- `agents/base.py` - Replaced by ReactAgent pattern
- `agents/tutor_agent.py` - Replaced by react_agents/tutor_agent.py
- `agents/quiz_coach_agent.py` - Replaced by react_agents/quiz_coach_agent.py
- `agents/planner_agent.py` - Replaced by react_agents/planner_agent.py
- `agents/orchestrator.py` - Replaced by react_agents/orchestrator.py

### Database Schema
No changes required - existing SQLite database is fully compatible.

### Frontend Compatibility
Frontend should work with minimal changes:
- Responses now include `thought_process` field (optional to display)
- `type` field renamed to `agent` in some responses
- All existing fields (content_md, citations, etc.) preserved

## Testing

Run the server:
```bash
cd agentpro_app
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
```

Test endpoints:
```bash
# Health check
curl http://localhost:8000/

# List agents
curl http://localhost:8000/agents

# Chat (will use LLM routing)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "course_id": "CS101",
    "prompt": "Explain recursion",
    "mode": ""
  }'
```

## Example: ReAct Reasoning Process

### User Query: "Explain recursion"

#### Orchestrator Routing
```
Thought: Analyzing query to select appropriate agent
Action: {"action_type": "route", "input": {"query": "Explain recursion", "mode": ""}}
Observation: {"agent": "tutor", "reasoning": "User wants explanation, use tutor agent"}
```

#### Tutor Agent Execution
```
Thought: User wants to learn about recursion. I should retrieve materials first.
Action: {"action_type": "retrieve_materials", "input": {"query": "recursion", "user_id": "test", "course_id": "CS101"}}
Observation: {"status": "success", "hits": [...], "count": 8, "quality": "high"}

Thought: Good materials found. Now I'll generate a comprehensive study guide.
Action: {"action_type": "generate_study_guide", "input": {"query": "recursion", "context": [...]}}
Observation: [Study guide content with citations and examples]

Final Answer: [Complete study guide on recursion]
```

## Benefits of ReAct Architecture

1. **Transparency**: Complete reasoning process visible
2. **Debuggability**: Can see exactly what the agent is thinking and doing
3. **Flexibility**: Easy to add new tools or modify behavior
4. **Consistency**: Standardized action-observation pattern
5. **Chainability**: Agents can perform multiple actions in sequence
6. **Testability**: Tools can be tested independently
7. **Maintainability**: Clear separation between reasoning and execution

## Future Enhancements

Possible extensions with this architecture:

1. **Tool Composition**: Agents using multiple tools in complex sequences
2. **Multi-Agent Collaboration**: Agents calling other agents as tools
3. **Dynamic Tool Loading**: Load tools based on course type
4. **Streaming Responses**: Stream thought process in real-time
5. **Caching**: Cache tool results for common queries
6. **Custom Tools**: Users define custom tools via plugins
7. **Feedback Loop**: Agents learn from user feedback on responses

## Conclusion

The AgentPro ReAct refactoring transforms StudyBuddy from a rule-based system into an intelligent, reasoning-driven platform while preserving all existing functionality and improving transparency, maintainability, and extensibility.
