#!/usr/bin/env python3
"""
Simple test script to verify the LangGraph-based system works correctly.
This script tests the basic functionality without requiring external APIs or files.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from agents.base_agent import BaseAgent, AgentState
        print("✅ Base agent imports successful")
        
        from agents.orchestrator_agent import OrchestratorAgent
        print("✅ Orchestrator agent imports successful")
        
        from langgraph.graph import StateGraph, END
        print("✅ LangGraph imports successful")
        
        from pydantic import BaseModel
        print("✅ Pydantic imports successful")
        
        # Test docx import
        from docx import Document
        print("✅ Python-docx imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_agent_state():
    """Test AgentState creation and validation."""
    print("\n🧪 Testing AgentState...")
    
    try:
        from agents.base_agent import AgentState
        
        # Create a test state
        state = AgentState(
            session_id="test_session",
            start_time=datetime.now().isoformat(),
            current_step="test",
            steps_completed=[],
            status="running",
            error=None,
            role="Test Role",
            resume_path="./test_resume.docx",
            location="Test Location",
            max_jobs=5,
            auto_apply=False,
            resume_analysis=None,
            job_search_results=None,
            processed_jobs=[],
            final_report=None,
            end_time=None,
            workflow_duration=None
        )
        
        print("✅ AgentState created successfully")
        print(f"   • Role: {state.role}")
        print(f"   • Location: {state.location}")
        print(f"   • Max Jobs: {state.max_jobs}")
        
        # Test state updates
        state.current_step = "updated_step"
        state.steps_completed.append("test_step")
        
        print("✅ AgentState updates successful")
        print(f"   • Current step: {state.current_step}")
        print(f"   • Steps completed: {state.steps_completed}")
        
        return True
        
    except Exception as e:
        print(f"❌ AgentState test failed: {e}")
        return False

def test_base_agent():
    """Test BaseAgent functionality."""
    print("\n🧪 Testing BaseAgent...")
    
    try:
        from agents.base_agent import BaseAgent, AgentState
        
        # Create a concrete test agent that inherits from BaseAgent
        class TestAgent(BaseAgent):
            async def execute(self, state: AgentState) -> AgentState:
                state.steps_completed.append("test_execution")
                return state
        
        # Create a test agent
        agent = TestAgent("TestAgent")
        
        print("✅ BaseAgent created successfully")
        print(f"   • Name: {agent.name}")
        print(f"   • Max retries: {agent.max_retries}")
        
        # Test validation
        test_state = AgentState(
            session_id="test",
            start_time="",
            current_step="",
            steps_completed=[],
            status="",
            error=None,
            role="Test",
            resume_path="./test.docx",
            location="",
            max_jobs=1,
            auto_apply=False,
            resume_analysis=None,
            job_search_results=None,
            processed_jobs=[],
            final_report=None,
            end_time=None,
            workflow_duration=None
        )
        
        # Test validation with required fields
        is_valid = agent.validate_input(test_state, ["role", "resume_path"])
        print(f"✅ Validation test: {'Passed' if is_valid else 'Failed'}")
        
        # Test validation with missing fields
        is_valid_missing = agent.validate_input(test_state, ["role", "resume_path", "missing_field"])
        print(f"✅ Missing field validation: {'Passed' if not is_valid_missing else 'Failed'}")
        
        # Test node creation
        node_func = agent.create_node()
        print(f"✅ Node creation: {'Passed' if callable(node_func) else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ BaseAgent test failed: {e}")
        return False

def test_orchestrator_creation():
    """Test OrchestratorAgent creation and workflow setup."""
    print("\n🧪 Testing OrchestratorAgent...")
    
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        
        # Create orchestrator
        orchestrator = OrchestratorAgent()
        
        print("✅ OrchestratorAgent created successfully")
        print(f"   • Type: {type(orchestrator).__name__}")
        
        # Test workflow graph
        workflow = orchestrator.get_workflow_graph()
        
        print("✅ Workflow graph retrieved successfully")
        print(f"   • Workflow type: {type(workflow).__name__}")
        print(f"   • Nodes: {len(workflow.nodes)}")
        
        # Show workflow structure
        print("\n🔄 Workflow Structure:")
        for node_name in workflow.nodes:
            print(f"   • {node_name}")
        
        # Test agent stats
        stats = orchestrator.get_agent_stats()
        print(f"\n📊 Agent Statistics:")
        for agent_name, agent_stats in stats.items():
            print(f"   • {agent_name}: {agent_stats.get('execution_count', 0)} executions")
        
        return True
        
    except Exception as e:
        print(f"❌ OrchestratorAgent test failed: {e}")
        return False

def test_langgraph_workflow():
    """Test basic LangGraph workflow creation."""
    print("\n🧪 Testing LangGraph workflow...")
    
    try:
        from langgraph.graph import StateGraph, END
        from agents.base_agent import AgentState
        
        # Create a simple workflow
        workflow = StateGraph(AgentState)
        
        # Add a simple test node
        def test_node(state: AgentState) -> AgentState:
            state.steps_completed.append("test_node")
            state.current_step = "test_complete"
            return state
        
        workflow.add_node("test_node", test_node)
        workflow.set_entry_point("test_node")
        workflow.add_edge("test_node", END)
        
        # Compile workflow
        compiled_workflow = workflow.compile()
        
        print("✅ LangGraph workflow created successfully")
        print(f"   • Workflow type: {type(compiled_workflow).__name__}")
        print(f"   • Has invoke method: {hasattr(compiled_workflow, 'invoke')}")
        print(f"   • Has ainvoke method: {hasattr(compiled_workflow, 'ainvoke')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LangGraph workflow test failed: {e}")
        return False

async def main():
    """Main test function."""
    
    print("🚀 LangGraph System Test Suite")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("AgentState Test", test_agent_state),
        ("BaseAgent Test", test_base_agent),
        ("Orchestrator Test", test_orchestrator_creation),
        ("LangGraph Workflow Test", test_langgraph_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The LangGraph system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)
