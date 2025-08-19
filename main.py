#!/usr/bin/env python3
"""
Main entry point for the LangGraph-based Job Application System.
This system uses LangGraph to orchestrate multiple agents for automated job searching and application.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from agents.base_agent import AgentState
from config import Config
from utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger("main")

async def main():
    """Main function to run the job application workflow."""
    
    print("🚀 LangGraph-based Job Application System")
    print("=" * 50)
    
    # Initialize the orchestrator agent
    orchestrator = OrchestratorAgent()
    
    # Create initial state
    initial_state = AgentState(
        session_id="",
        start_time="",
        current_step="",
        steps_completed=[],
        status="",
        error=None,
        role="Software Engineer",
        resume_path="./resume.docx",  # Update this path to your actual resume
        location="San Francisco, CA",
        max_jobs=5,
        auto_apply=False,  # Set to True if you want to automatically apply
        resume_analysis=None,
        job_search_results=None,
        processed_jobs=[],
        final_report=None,
        end_time=None,
        workflow_duration=None
    )
    
    try:
        print(f"📋 Starting workflow for role: {initial_state.role}")
        print(f"📍 Location: {initial_state.location}")
        print(f"🎯 Max jobs to process: {initial_state.max_jobs}")
        print(f"🤖 Auto-apply: {'Yes' if initial_state.auto_apply else 'No'}")
        print(f"📄 Resume path: {initial_state.resume_path}")
        print("-" * 50)
        
        # Execute the workflow
        print("🔄 Executing workflow...")
        final_state = await orchestrator.execute(initial_state)
        
        # Display results
        print("\n✅ Workflow completed!")
        print("=" * 50)
        
        if final_state.status == "completed":
            print(f"📊 Summary:")
            print(f"   • Session ID: {final_state.session_id}")
            print(f"   • Duration: {final_state.workflow_duration}")
            print(f"   • Steps completed: {', '.join(final_state.steps_completed)}")
            
            if final_state.job_search_results:
                jobs_found = final_state.job_search_results.get("total_found", 0)
                print(f"   • Jobs found: {jobs_found}")
            
            if final_state.processed_jobs:
                processed_count = len(final_state.processed_jobs)
                successful_applications = len([
                    job for job in final_state.processed_jobs 
                    if job.get("application_status", {}).get("status") == "success"
                ])
                print(f"   • Jobs processed: {processed_count}")
                print(f"   • Applications submitted: {successful_applications}")
            
            if final_state.final_report:
                report = final_state.final_report
                print(f"\n📈 Final Report:")
                print(f"   • Success rate: {report.get('summary', {}).get('success_rate', 0):.1f}%")
                
                skill_analysis = report.get("skill_analysis", {})
                if skill_analysis:
                    top_skills = skill_analysis.get("top_required_skills", [])
                    missing_skills = skill_analysis.get("missing_skills", [])
                    
                    if top_skills:
                        print(f"   • Top required skills: {', '.join([skill[0] for skill in top_skills[:5]])}")
                    
                    if missing_skills:
                        print(f"   • Missing skills: {', '.join([skill['skill'] for skill in missing_skills[:3]])}")
                
                recommendations = report.get("recommendations", [])
                if recommendations:
                    print(f"\n💡 Recommendations:")
                    for i, rec in enumerate(recommendations[:3], 1):
                        print(f"   {i}. {rec}")
        
        elif final_state.status == "error":
            print(f"❌ Workflow failed: {final_state.error}")
        
        # Save workflow state
        if final_state.session_id:
            print(f"\n💾 Workflow state saved with session ID: {final_state.session_id}")
        
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        print(f"❌ Execution failed: {str(e)}")
        return 1
    
    return 0

async def run_example_workflow():
    """Run a simplified example workflow to demonstrate the system."""
    
    print("🧪 Running Example Workflow")
    print("=" * 30)
    
    # Create a simple state for demonstration
    example_state = AgentState(
        session_id="",
        start_time="",
        current_step="",
        steps_completed=[],
        status="",
        error=None,
        role="Data Scientist",
        resume_path="./example_resume.docx",
        location="New York, NY",
        max_jobs=3,
        auto_apply=False,
        resume_analysis=None,
        job_search_results=None,
        processed_jobs=[],
        final_report=None,
        end_time=None,
        workflow_duration=None
    )
    
    try:
        orchestrator = OrchestratorAgent()
        
        # Get the workflow graph for inspection
        workflow_graph = orchestrator.get_workflow_graph()
        print(f"📊 Workflow graph created with {len(workflow_graph.nodes)} nodes")
        
        # Show workflow structure
        print("\n🔄 Workflow Structure:")
        for node_name in workflow_graph.nodes:
            print(f"   • {node_name}")
        
        print("\n✅ Example workflow setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Example workflow failed: {str(e)}")
        return 1
    
    return 0

def show_usage():
    """Show usage information."""
    
    print("Usage:")
    print("  python main.py                    # Run the full workflow")
    print("  python main.py --example          # Run example workflow")
    print("  python main.py --usage            # Show this help")
    print("\nEnvironment Variables:")
    print("  OPENAI_API_KEY                    # OpenAI API key for AI features")
    print("  LINKEDIN_CLIENT_ID                # LinkedIn API client ID")
    print("  LINKEDIN_CLIENT_SECRET            # LinkedIn API client secret")
    print("  LINKEDIN_ACCESS_TOKEN             # LinkedIn API access token")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="LangGraph-based Job Application System")
    parser.add_argument("--example", action="store_true", help="Run example workflow")
    parser.add_argument("--usage", action="store_true", help="Show usage information")
    
    args = parser.parse_args()
    
    if args.usage:
        show_usage()
        sys.exit(0)
    
    try:
        if args.example:
            exit_code = asyncio.run(run_example_workflow())
        else:
            exit_code = asyncio.run(main())
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
