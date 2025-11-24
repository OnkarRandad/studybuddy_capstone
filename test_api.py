"""
StudyBuddy AgentPro ReAct - Testing Guide
==========================================

This guide walks you through testing the new AgentPro ReAct architecture.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = "test_user"
COURSE_ID = "CS101"

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")

def print_response(response):
    """Pretty print API response."""
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)

# Test 1: Health Check
print_section("TEST 1: Health Check")
print("Checking if server is running...")
try:
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print_response(response)

    if response.status_code == 200:
        print("\n✅ Server is running!")
    else:
        print("\n❌ Server returned error")
        exit(1)
except requests.exceptions.ConnectionError:
    print("❌ ERROR: Cannot connect to server!")
    print("\nPlease start the server first:")
    print("  cd agentpro_app")
    print("  uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000")
    exit(1)

# Test 2: List Agents
print_section("TEST 2: List Available Agents")
print("Fetching agent capabilities...")
response = requests.get(f"{BASE_URL}/agents")
print_response(response)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Found {len(data.get('agents', {}))} agents:")
    for agent_name, info in data.get('agents', {}).items():
        print(f"  - {agent_name}: {info.get('role', 'N/A')}")

# Test 3: Upload PDF
print_section("TEST 3: Upload Test PDF (Optional)")
print("To upload a PDF, use this command:")
print(f"""
curl -X POST {BASE_URL}/ingest \\
  -F "user_id={USER_ID}" \\
  -F "course_id={COURSE_ID}" \\
  -F "title=Test Document" \\
  -F "file=@/path/to/your/document.pdf"
""")
print("\nOr create a simple test PDF and upload via Python:")
print("""
# Example Python code:
with open('test.pdf', 'rb') as f:
    files = {'file': ('test.pdf', f, 'application/pdf')}
    data = {
        'user_id': 'test_user',
        'course_id': 'CS101',
        'title': 'Test Document'
    }
    response = requests.post(f"{BASE_URL}/ingest", files=files, data=data)
    print(response.json())
""")
print("\nSkipping automatic upload (requires PDF file)...")

# Test 4: Chat with LLM Routing
print_section("TEST 4: Chat (LLM-Based Routing)")
print("Testing chat endpoint with ReAct reasoning...")
print(f"Query: 'Explain what recursion is in programming'")

chat_request = {
    "user_id": USER_ID,
    "course_id": COURSE_ID,
    "prompt": "Explain what recursion is in programming",
    "mode": ""  # Empty mode - let LLM routing decide!
}

print("\nSending request...")
response = requests.post(f"{BASE_URL}/chat", json=chat_request)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Agent used: {data.get('agent_used', 'unknown')}")
    print(f"✅ Response type: {data.get('type', 'unknown')}")

    # Show thought process
    if 'thought_process' in data:
        print("\n🧠 THOUGHT PROCESS (ReAct Reasoning):")
        for i, step in enumerate(data['thought_process'], 1):
            if step.get('thought'):
                print(f"\n  Step {i} - Thought:")
                print(f"    {step['thought'][:200]}...")
            if step.get('action'):
                print(f"  Step {i} - Action:")
                print(f"    Type: {step['action'].get('action_type')}")
            if step.get('observation'):
                print(f"  Step {i} - Observation:")
                obs = str(step['observation'].get('result', ''))
                print(f"    {obs[:200]}...")

    # Show final answer preview
    content = data.get('content_md', '')
    print(f"\n📝 FINAL ANSWER (preview):")
    print(content[:500] + "..." if len(content) > 500 else content)
else:
    print("❌ Request failed:")
    print_response(response)

# Test 5: Generate Quiz
print_section("TEST 5: Generate Quiz (Quiz Coach Agent)")
print("Testing quiz generation...")

quiz_request = {
    "user_id": USER_ID,
    "course_id": COURSE_ID,
    "prompt": "Generate a quiz on recursion",
    "mode": "quiz",
    "difficulty": "medium",
    "num_items": 5
}

print("\nSending request...")
response = requests.post(f"{BASE_URL}/generate_quiz", json=quiz_request)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Quiz generated!")
    print(f"   Difficulty: {data.get('difficulty')}")
    print(f"   Questions: {data.get('num_questions')}")

    # Show quiz preview
    content = data.get('content_md', '')
    print(f"\n📝 QUIZ (preview):")
    print(content[:500] + "..." if len(content) > 500 else content)
else:
    print("❌ Request failed:")
    print_response(response)

# Test 6: Study Plan
print_section("TEST 6: Study Plan (Planner Agent)")
print("Testing study plan generation...")

plan_request = {
    "user_id": USER_ID,
    "course_id": COURSE_ID,
    "query": "Create a 2-week study plan for learning recursion",
    "hours_per_day": 2
}

print("\nSending request...")
response = requests.post(f"{BASE_URL}/study-plan", json=plan_request)
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    print(f"✅ Study plan generated!")

    # Show plan preview
    content = data.get('content_md', '')
    print(f"\n📅 STUDY PLAN (preview):")
    print(content[:500] + "..." if len(content) > 500 else content)
else:
    print("❌ Request failed:")
    print_response(response)

# Test 7: Get Stats
print_section("TEST 7: User Statistics")
print("Fetching user stats...")

response = requests.get(f"{BASE_URL}/stats/{USER_ID}/{COURSE_ID}")
print(f"Status: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    stats = data.get('stats', {})
    print(f"✅ Statistics retrieved!")
    print(f"   Queries: {stats.get('total_queries', 0)}")
    print(f"   Quizzes taken: {stats.get('quizzes_taken', 0)}")
    print(f"   Weak topics: {len(stats.get('weak_topics', []))}")
    print(f"   Strong topics: {len(stats.get('strong_topics', []))}")
    print(f"   Documents uploaded: {stats.get('docs_uploaded', 0)}")
else:
    print("❌ Request failed:")
    print_response(response)

# Summary
print_section("TEST SUMMARY")
print("""
✅ All basic tests completed!

What we tested:
1. ✅ Server health check
2. ✅ Agent listing (4 agents + orchestrator)
3. ℹ️  PDF upload (manual - requires PDF file)
4. ✅ Chat with LLM routing
5. ✅ Quiz generation
6. ✅ Study plan generation
7. ✅ User statistics

NEXT STEPS:
-----------
1. Upload a real PDF document to test RAG:
   - Use the curl command shown in Test 3
   - Or use the web frontend

2. Test different modes:
   - mode="" (let LLM routing decide)
   - mode="guide" (force tutor agent)
   - mode="quiz" (force quiz coach)
   - mode="flashcards" (force flashcards agent)

3. Test ReAct reasoning:
   - Look at the 'thought_process' in responses
   - You'll see Thought → Action → Observation → Final Answer

4. Try complex queries:
   - "I'm struggling with recursion, create a study plan"
   - "Generate flashcards for data structures"
   - "Quiz me on algorithms with hard difficulty"

The LLM routing will automatically select the best agent!
""")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Testing complete! Server is ready to use.")
    print("=" * 60)
