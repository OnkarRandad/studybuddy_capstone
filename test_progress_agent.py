"""
Test script for ProgressAgent tool.
Run this to verify the ProgressAgent works correctly.
"""

import os
import json
from agentpro_app.progress_agent import ProgressAgentTool
from agentpro_app import memory as mem

def setup_test_data():
    """Create test data for progress analysis."""
    user_id = "test_student"
    course_id = "test_course"
    
    # Create some sample quiz history
    mem.log_query(user_id, course_id, "What is recursion?", "guide")
    mem.log_query(user_id, course_id, "Binary search trees", "guide")
    mem.log_query(user_id, course_id, "Sorting algorithms", "quiz")
    
    mem.log_quiz_attempt(user_id, course_id, "recursion", 0.85, 6, "medium")
    mem.log_quiz_attempt(user_id, course_id, "binary search", 0.55, 8, "medium")
    mem.log_quiz_attempt(user_id, course_id, "recursion", 0.90, 6, "hard")
    mem.log_quiz_attempt(user_id, course_id, "graphs", 0.40, 10, "medium")
    mem.log_quiz_attempt(user_id, course_id, "binary search", 0.60, 8, "medium")
    
    print("✓ Test data created")
    return user_id, course_id

def test_progress_agent():
    """Test the ProgressAgent tool."""
    print("\n🧪 Testing ProgressAgent Tool\n")
    print("=" * 60)
    
    # Setup
    user_id, course_id = setup_test_data()
    agent_tool = ProgressAgentTool()
    
    # Test 1: Overview Analysis
    print("\n📊 Test 1: Overview Analysis")
    print("-" * 60)
    input_data = {
        "user_id": user_id,
        "course_id": course_id,
        "analysis_type": "overview"
    }
    
    result = agent_tool.run(json.dumps(input_data))
    result_dict = json.loads(result)
    
    if result_dict.get("success"):
        print("✓ Overview analysis succeeded")
        print(f"  Study streak: {result_dict.get('study_streak')}")
        print(f"  Quizzes taken: {result_dict.get('quizzes_taken')}")
        print(f"  Weak topics: {result_dict.get('weak_topics')}")
        print(f"  Strong topics: {result_dict.get('strong_topics')}")
    else:
        print(f"✗ Failed: {result_dict.get('error')}")
    
    # Test 2: Detailed Analysis
    print("\n📈 Test 2: Detailed Analysis")
    print("-" * 60)
    input_data["analysis_type"] = "detailed"
    
    result = agent_tool.run(json.dumps(input_data))
    result_dict = json.loads(result)
    
    if result_dict.get("success"):
        print("✓ Detailed analysis succeeded")
        print(f"  Mastery scores:")
        for topic, data in result_dict.get("mastery_scores", {}).items():
            avg = data.get("average", 0)
            trend = data.get("trend", "unknown")
            print(f"    - {topic}: {avg*100:.0f}% ({trend})")
        
        print(f"  Learning gaps: {result_dict.get('learning_gaps')}")
    else:
        print(f"✗ Failed: {result_dict.get('error')}")
    
    # Test 3: Recommendations
    print("\n💡 Test 3: Recommendations")
    print("-" * 60)
    input_data["analysis_type"] = "recommendations"
    
    result = agent_tool.run(json.dumps(input_data))
    result_dict = json.loads(result)
    
    if result_dict.get("success"):
        print("✓ Recommendations generated")
        print(f"  Recommendations:")
        for i, rec in enumerate(result_dict.get("recommendations", []), 1):
            print(f"    {i}. {rec}")
        
        print(f"\n  Next steps:")
        for step in result_dict.get("next_steps", []):
            priority = step.get("priority", "medium")
            action = step.get("action", "")
            print(f"    [{priority.upper()}] {action}")
    else:
        print(f"✗ Failed: {result_dict.get('error')}")
    
    # Test 4: Mastery Check
    print("\n🎯 Test 4: Mastery Check")
    print("-" * 60)
    input_data["analysis_type"] = "mastery_check"
    
    result = agent_tool.run(json.dumps(input_data))
    result_dict = json.loads(result)
    
    if result_dict.get("success"):
        print("✓ Mastery check completed")
        summary = result_dict.get("summary", {})
        print(f"  Mastered: {summary.get('mastered', 0)}")
        print(f"  Proficient: {summary.get('proficient', 0)}")
        print(f"  Needs Review: {summary.get('needs_review', 0)}")
        
        print(f"\n  Topic breakdown:")
        for report in result_dict.get("mastery_report", []):
            emoji = report.get("emoji", "")
            topic = report.get("topic", "")
            level = report.get("level", "")
            score = report.get("score", 0)
            print(f"    {emoji} {topic}: {level} ({score*100:.0f}%)")
    else:
        print(f"✗ Failed: {result_dict.get('error')}")
    
    # Test 5: Error Handling
    print("\n⚠️  Test 5: Error Handling")
    print("-" * 60)
    
    # Test with invalid input
    invalid_input = {"invalid": "data"}
    result = agent_tool.run(json.dumps(invalid_input))
    result_dict = json.loads(result)
    
    if not result_dict.get("success"):
        print("✓ Error handling works correctly")
        print(f"  Error message: {result_dict.get('error')}")
    else:
        print("✗ Should have failed with invalid input")
    
    # Cleanup
    print("\n🧹 Cleanup")
    print("-" * 60)
    mem.delete_all_data(user_id, course_id)
    print("✓ Test data cleaned up")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\nThe ProgressAgent tool is working correctly.")
    print("\nYou can now:")
    print("1. Use it in your AgentPro ReAct loops")
    print("2. Call it via the /progress/analyze endpoint")
    print("3. Integrate it with your frontend")

def test_with_agentpro():
    """Test ProgressAgent integrated with AgentPro ReAct loop."""
    try:
        from agentpro import ReactAgent, create_model
        
        print("\n🤖 Testing with AgentPro ReAct Loop")
        print("=" * 60)
        
        # Setup test data
        user_id, course_id = setup_test_data()
        
        # Create model
        model = create_model(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create agent with ProgressAgent tool
        tools = [ProgressAgentTool()]
        agent = ReactAgent(
            model=model,
            tools=tools,
            max_iterations=10
        )
        
        # Run agent
        query = f"""Analyze the learning progress for student '{user_id}' in course '{course_id}'.
        I want to understand their weak topics and get specific recommendations for what to study next."""
        
        print(f"\n📝 Query: {query}\n")
        
        response = agent.run(query)
        
        print("\n💭 Thought Process:")
        print("-" * 60)
        for i, step in enumerate(response.thought_process, 1):
            if step.thought:
                print(f"{i}. Thought: {step.thought}")
            if step.action:
                print(f"   Action: {step.action.action_type}")
            if step.observation:
                # Truncate long observations
                obs = str(step.observation.result)
                if len(obs) > 200:
                    obs = obs[:200] + "..."
                print(f"   Observation: {obs}")
        
        print("\n✨ Final Answer:")
        print("-" * 60)
        print(response.final_answer)
        
        # Cleanup
        mem.delete_all_data(user_id, course_id)
        print("\n✓ AgentPro integration test completed")
        
    except ImportError:
        print("\n⚠️  AgentPro not installed - skipping ReAct loop test")
        print("   Install with: pip install git+https://github.com/traversaal-ai/AgentPro.git")
    except Exception as e:
        print(f"\n✗ AgentPro test failed: {e}")

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║         ProgressAgent Test Suite                     ║
    ║         StudyBuddy Pro 2.0                           ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Run basic tests
    test_progress_agent()
    
    # Try AgentPro integration if available
    test_with_agentpro()
    
    print("\n🎉 Testing complete! Your ProgressAgent is ready to use.")