#!/bin/bash

# StudyBuddy AgentPro ReAct - Quick Testing Script
# ==================================================

BASE_URL="http://localhost:8000"
USER_ID="test_user"
COURSE_ID="CS101"

echo "===================================="
echo "  StudyBuddy Testing Script"
echo "===================================="
echo ""

# Test 1: Health Check
echo "📊 TEST 1: Health Check"
echo "------------------------"
curl -s "$BASE_URL/" | jq '.' 2>/dev/null || curl -s "$BASE_URL/"
echo ""
echo ""

# Test 2: List Agents
echo "🤖 TEST 2: List Available Agents"
echo "---------------------------------"
curl -s "$BASE_URL/agents" | jq '.' 2>/dev/null || curl -s "$BASE_URL/agents"
echo ""
echo ""

# Test 3: PDF Upload Instructions
echo "📄 TEST 3: Upload PDF (Manual Step)"
echo "------------------------------------"
echo "To upload a PDF, run:"
echo ""
echo "curl -X POST $BASE_URL/ingest \\"
echo "  -F \"user_id=$USER_ID\" \\"
echo "  -F \"course_id=$COURSE_ID\" \\"
echo "  -F \"title=Test Document\" \\"
echo "  -F \"file=@/path/to/your/document.pdf\""
echo ""
echo "Replace /path/to/your/document.pdf with your actual PDF file path"
echo ""
echo ""

# Test 4: Chat with LLM Routing
echo "💬 TEST 4: Chat (LLM-Based Routing)"
echo "------------------------------------"
echo "Sending: 'Explain recursion in programming'"
echo ""
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"course_id\": \"$COURSE_ID\",
    \"prompt\": \"Explain what recursion is in programming\",
    \"mode\": \"\"
  }" | jq '.agent_used, .type, .content_md[:300]' 2>/dev/null || echo "Install 'jq' for better formatting or check server logs"
echo ""
echo ""

# Test 5: Generate Quiz
echo "📝 TEST 5: Generate Quiz"
echo "------------------------"
echo "Generating a quiz on recursion..."
echo ""
curl -s -X POST "$BASE_URL/generate_quiz" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"course_id\": \"$COURSE_ID\",
    \"prompt\": \"Generate a quiz on recursion\",
    \"mode\": \"quiz\",
    \"difficulty\": \"medium\",
    \"num_items\": 5
  }" | jq '.type, .difficulty, .content_md[:300]' 2>/dev/null || echo "Install 'jq' for better formatting"
echo ""
echo ""

# Summary
echo "===================================="
echo "  ✅ Testing Complete!"
echo "===================================="
echo ""
