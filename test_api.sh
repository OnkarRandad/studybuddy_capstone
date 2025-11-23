#!/bin/bash

# StudyBuddy Pro API Test Script
# Tests all major endpoints and features

BASE_URL="http://localhost:8080"
USER_ID="test_student"
COURSE_ID="test_course"

echo "🧪 StudyBuddy Pro API Test Suite"
echo "=================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
response=$(curl -s "$BASE_URL/")
if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server not responding${NC}"
    exit 1
fi
echo ""

# Test 2: Upload a document (you need a test PDF)
echo -e "${BLUE}Test 2: Document Upload${NC}"
if [ -f "test.pdf" ]; then
    response=$(curl -s -X POST "$BASE_URL/ingest" \
        -F user_id=$USER_ID \
        -F course_id=$COURSE_ID \
        -F title="Test Document" \
        -F file=@test.pdf)
    
    if [[ $response == *"ok"* ]]; then
        echo -e "${GREEN}✓ Document uploaded successfully${NC}"
        chunks=$(echo $response | grep -o '"chunks":[0-9]*' | cut -d':' -f2)
        echo "  Indexed $chunks chunks"
    else
        echo -e "${RED}✗ Upload failed${NC}"
        echo "  Response: $response"
    fi
else
    echo -e "${RED}✗ test.pdf not found - skipping upload test${NC}"
    echo "  Create a test.pdf file to test document upload"
fi
echo ""

# Test 3: Chat - Quick Answer
echo -e "${BLUE}Test 3: Chat Mode (Quick Answer)${NC}"
response=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"prompt\": \"What is a binary search tree?\",
        \"mode\": \"chat\"
    }")

if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ Chat response received${NC}"
else
    echo -e "${RED}✗ Chat failed${NC}"
    echo "  Response: $response"
fi
echo ""

# Test 4: Study Guide
echo -e "${BLUE}Test 4: Study Guide Generation${NC}"
response=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"prompt\": \"binary search\",
        \"mode\": \"guide\"
    }")

if [[ $response == *"study_guide"* ]]; then
    echo -e "${GREEN}✓ Study guide generated${NC}"
    quality=$(echo $response | grep -o '"quality":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    echo "  Quality: $quality"
else
    echo -e "${RED}✗ Study guide generation failed${NC}"
fi
echo ""

# Test 5: Quiz Generation
echo -e "${BLUE}Test 5: Quiz Generation${NC}"
response=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"prompt\": \"sorting algorithms\",
        \"mode\": \"quiz\",
        \"difficulty\": \"medium\",
        \"num_items\": 5
    }")

if [[ $response == *"quiz"* ]]; then
    echo -e "${GREEN}✓ Quiz generated${NC}"
else
    echo -e "${RED}✗ Quiz generation failed${NC}"
fi
echo ""

# Test 6: Flashcards
echo -e "${BLUE}Test 6: Flashcard Generation${NC}"
response=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"prompt\": \"recursion\",
        \"mode\": \"flashcards\",
        \"num_items\": 8
    }")

if [[ $response == *"flashcards"* ]]; then
    echo -e "${GREEN}✓ Flashcards generated${NC}"
else
    echo -e "${RED}✗ Flashcard generation failed${NC}"
fi
echo ""

# Test 7: Submit Quiz
echo -e "${BLUE}Test 7: Quiz Submission${NC}"
response=$(curl -s -X POST "$BASE_URL/submit-quiz" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"topic\": \"sorting algorithms\",
        \"score\": 0.75,
        \"total_questions\": 5,
        \"difficulty\": \"medium\"
    }")

if [[ $response == *"ok"* ]]; then
    echo -e "${GREEN}✓ Quiz submitted successfully${NC}"
else
    echo -e "${RED}✗ Quiz submission failed${NC}"
fi
echo ""

# Test 8: Progress Stats
echo -e "${BLUE}Test 8: Progress Statistics${NC}"
response=$(curl -s "$BASE_URL/stats/$USER_ID/$COURSE_ID")

if [[ $response == *"study_streak"* ]]; then
    echo -e "${GREEN}✓ Stats retrieved${NC}"
    streak=$(echo $response | grep -o '"study_streak":[0-9]*' | cut -d':' -f2)
    quizzes=$(echo $response | grep -o '"quizzes_taken":[0-9]*' | cut -d':' -f2)
    echo "  Study streak: $streak"
    echo "  Quizzes taken: $quizzes"
else
    echo -e "${RED}✗ Stats retrieval failed${NC}"
fi
echo ""

# Test 9: Progress Analysis
echo -e "${BLUE}Test 9: Detailed Progress Analysis${NC}"
response=$(curl -s -X POST "$BASE_URL/progress/analyze" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\"
    }")

if [[ $response == *"analysis"* ]]; then
    echo -e "${GREEN}✓ Progress analysis completed${NC}"
else
    echo -e "${RED}✗ Progress analysis failed${NC}"
fi
echo ""

# Test 10: Study Plan
echo -e "${BLUE}Test 10: Study Plan Generation${NC}"
response=$(curl -s -X POST "$BASE_URL/study-plan" \
    -H "Content-Type: application/json" \
    -d "{
        \"user_id\": \"$USER_ID\",
        \"course_id\": \"$COURSE_ID\",
        \"hours_per_day\": 2
    }")

if [[ $response == *"plan"* ]]; then
    echo -e "${GREEN}✓ Study plan generated${NC}"
else
    echo -e "${RED}✗ Study plan generation failed${NC}"
fi
echo ""

# Summary
echo "=================================="
echo -e "${BLUE}Test Suite Complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Check the Swagger docs at: $BASE_URL/docs"
echo "2. Upload your course PDFs"
echo "3. Start studying!"
echo ""
echo "To clean up test data, run:"
echo "curl -X DELETE $BASE_URL/data/$USER_ID/$COURSE_ID"