#!/usr/bin/env python3
"""
Example demonstrating the LangGraph-based Job Application System.
This example shows how to create and execute workflows using the new architecture.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator_agent import OrchestratorAgent
from agents.base_agent import AgentState
from langgraph.graph import StateGraph

async def demonstrate_workflow_creation():
    """Demonstrate how the LangGraph workflow is created."""
    
    print("🔧 LangGraph Workflow Creation Demo")
    print("=" * 40)
    
    # Create the orchestrator agent
    orchestrator = OrchestratorAgent()
    
    # Get the workflow graph
    workflow = orchestrator.get_workflow_graph()
    
    print(f"📊 Workflow created successfully!")
    print(f"   • Type: {type(workflow).__name__}")
    print(f"   • Nodes: {len(workflow.nodes)}")
    print(f"   • Entry point: analyze_resume")
    
    print("\n🔄 Workflow Nodes:")
    for node_name in workflow.nodes:
        print(f"   • {node_name}")
    
    print("\n🔄 Workflow Flow:")
    print("   1. analyze_resume → 2. search_jobs → 3. process_jobs → 4. generate_report")
    
    return workflow

async def demonstrate_state_management():
    """Demonstrate how the AgentState works."""
    
    print("\n📋 AgentState Management Demo")
    print("=" * 35)
    
    # Create a sample state
    sample_state = AgentState(
        session_id="demo_session_123",
        start_time=datetime.now().isoformat(),
        current_step="demo",
        steps_completed=["setup"],
        status="running",
        error=None,
        role="Python Developer",
        resume_path="./sample_resume.docx",
        location="Remote",
        max_jobs=3,
        auto_apply=False,
        resume_analysis=None,
        job_search_results=None,
        processed_jobs=[],
        final_report=None,
        end_time=None,
        workflow_duration=None
    )
    
    print(f"✅ State created successfully!")
    print(f"   • Session ID: {sample_state.session_id}")
    print(f"   • Role: {sample_state.role}")
    print(f"   • Location: {sample_state.location}")
    print(f"   • Max Jobs: {sample_state.max_jobs}")
    print(f"   • Auto-apply: {sample_state.auto_apply}")
    
    # Demonstrate state updates
    sample_state.current_step = "resume_analysis"
    sample_state.steps_completed.append("resume_analysis")
    
    print(f"\n🔄 State updated:")
    print(f"   • Current step: {sample_state.current_step}")
    print(f"   • Steps completed: {', '.join(sample_state.steps_completed)}")
    
    return sample_state

async def demonstrate_agent_integration():
    """Demonstrate how agents integrate with the workflow."""
    
    print("\n🤖 Agent Integration Demo")
    print("=" * 30)
    
    # Create the orchestrator
    orchestrator = OrchestratorAgent()
    
    # Show agent statistics
    stats = orchestrator.get_agent_stats()
    
    print("📊 Agent Statistics:")
    for agent_name, agent_stats in stats.items():
        print(f"   • {agent_name}: {agent_stats.get('execution_count', 0)} executions")
    
    # Show workflow structure
    workflow = orchestrator.get_workflow_graph()
    
    print(f"\n🔄 Workflow Structure:")
    print(f"   • Total nodes: {len(workflow.nodes)}")
    print(f"   • Compiled: {hasattr(workflow, 'invoke')}")
    
    return orchestrator

async def demonstrate_error_handling():
    """Demonstrate error handling in the workflow."""
    
    print("\n⚠️  Error Handling Demo")
    print("=" * 25)
    
    # Create a state with missing required fields
    invalid_state = AgentState(
        session_id="error_demo",
        start_time=datetime.now().isoformat(),
        current_step="",
        steps_completed=[],
        status="",
        error=None,
        role="",  # Missing required field
        resume_path="",  # Missing required field
        location="",
        max_jobs=0,
        auto_apply=False,
        resume_analysis=None,
        job_search_results=None,
        processed_jobs=[],
        final_report=None,
        end_time=None,
        workflow_duration=None
    )
    
    print("🔍 Testing validation with invalid state...")
    
    # Test validation using the orchestrator agent
    from agents.orchestrator_agent import OrchestratorAgent
    test_agent = OrchestratorAgent()
    
    is_valid = test_agent.validate_input(invalid_state, ["role", "resume_path"])
    print(f"   • Validation result: {'❌ Invalid' if not is_valid else '✅ Valid'}")
    
    if not is_valid:
        print("   • Expected: Missing required fields: role and resume_path")
    
    return invalid_state

async def main():
    """Main demonstration function."""
    
    print("🚀 LangGraph Job Application System - Demo")
    print("=" * 55)
    
    try:
        # Demonstrate workflow creation
        workflow = await demonstrate_workflow_creation()
        
        # Demonstrate state management
        sample_state = await demonstrate_state_management()
        
        # Demonstrate agent integration
        orchestrator = await demonstrate_agent_integration()
        
        # Demonstrate error handling
        invalid_state = await demonstrate_error_handling()
        
        print("\n" + "=" * 55)
        print("✅ All demonstrations completed successfully!")
        print("\n💡 Key Benefits of LangGraph Architecture:")
        print("   • Declarative workflow definition")
        print("   • Built-in state management")
        print("   • Easy error handling and recovery")
        print("   • Scalable and maintainable code")
        print("   • Clear separation of concerns")
        
        print("\n🚀 Ready to run the full workflow!")
        print("   Use: python main.py --example")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Demonstration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
