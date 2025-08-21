"""
Web Automation Example - Demonstrates using email/password authentication for job search.
"""

import asyncio
import os
from dotenv import load_dotenv
from agents.smart_orchestrator_agent import SmartOrchestratorAgent
from agents.base_agent import AgentState
from config import Config

async def main():
    """Main function demonstrating web automation for job search."""
    
    print("🚀 Web Automation Job Search Example")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Create smart orchestrator
    orchestrator = SmartOrchestratorAgent()
    
    # Show available job sources
    print("\n📋 Available Job Sources:")
    sources = orchestrator.get_available_sources()
    for source, method in sources.items():
        print(f"  • {source.title()}: {method}")
    
    # Show credential status
    print("\n🔐 Credential Status:")
    cred_status = orchestrator.get_credential_status()
    for platform, status in cred_status.items():
        print(f"  • {platform.title()}:")
        print(f"    - Web Credentials: {'✅' if status['web_credentials'] else '❌'}")
    
    # Check if we have any working credentials
    has_credentials = any(
        status['web_credentials']
        for status in cred_status.values()
    )
    
    if not has_credentials:
        print("\n❌ No credentials available!")
        print("Please set up your .env file with:")
        print("  • LinkedIn email/password (LINKEDIN_EMAIL, LINKEDIN_PASSWORD)")
        print("  • Glassdoor email/password (GLASSDOOR_EMAIL, GLASSDOOR_PASSWORD)")
        return
    
    # Create initial state
    state = AgentState()
    state.role = "Software Engineer"
    state.location = "Remote"
    state.max_jobs = 5
    state.auto_apply = False  # Set to True to enable automatic applications
    state.keywords = ["python", "machine learning", "AI"]
    state.min_salary = 80000
    state.max_salary = 150000
    state.job_type = ["full-time", "remote"]
    state.experience_level = ["entry", "mid-level"]
    
    # Set resume path if available
    resume_path = getattr(Config, 'DEFAULT_RESUME_PATH', None)
    if resume_path and os.path.exists(resume_path):
        state.resume_path = resume_path
        print(f"\n📄 Using resume: {resume_path}")
    
    print(f"\n🎯 Job Search Parameters:")
    print(f"  • Role: {state.role}")
    print(f"  • Location: {state.location}")
    print(f"  • Max Jobs: {state.max_jobs}")
    print(f"  • Keywords: {', '.join(state.keywords)}")
    print(f"  • Salary Range: ${state.min_salary:,} - ${state.max_salary:,}")
    print(f"  • Job Types: {', '.join(state.job_type)}")
    print(f"  • Experience Level: {', '.join(state.experience_level)}")
    print(f"  • Auto-apply: {'Yes' if state.auto_apply else 'No'}")
    
    # Execute the workflow
    print(f"\n🚀 Starting job search workflow...")
    try:
        result_state = await orchestrator.execute(state)
        
        if result_state.error:
            print(f"\n❌ Workflow failed: {result_state.error}")
            return
        
        # Display results
        print(f"\n✅ Workflow completed successfully!")
        print(f"📊 Results Summary:")
        
        if hasattr(result_state, 'all_jobs') and result_state.all_jobs:
            print(f"  • Total Jobs Found: {len(result_state.all_jobs)}")
            
            # Group jobs by source
            jobs_by_source = {}
            for job in result_state.all_jobs:
                source = job.get('source', 'unknown')
                if source not in jobs_by_source:
                    jobs_by_source[source] = []
                jobs_by_source[source].append(job)
            
            for source, jobs in jobs_by_source.items():
                print(f"  • {source.title()}: {len(jobs)} jobs")
                
                # Show top 3 jobs from each source
                for i, job in enumerate(jobs[:3]):
                    print(f"    {i+1}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                    if job.get('salary'):
                        print(f"       💰 {job.get('salary')}")
                    if job.get('location'):
                        print(f"       📍 {job.get('location')}")
                    print()
        
        if hasattr(result_state, 'all_applications') and result_state.all_applications:
            print(f"  • Applications Submitted: {len(result_state.all_applications)}")
            
            # Count successful applications
            successful = sum(1 for app in result_state.all_applications if app.get('status') == 'success')
            print(f"  • Successful Applications: {successful}")
            
            # Show application details
            for app in result_state.all_applications[:3]:  # Show first 3
                print(f"    • {app.get('job_id', 'Unknown')}: {app.get('status', 'Unknown')}")
                if app.get('message'):
                    print(f"      {app.get('message')}")
        
        # Show completed steps
        if hasattr(result_state, 'steps_completed') and result_state.steps_completed:
            print(f"\n📋 Completed Steps:")
            for step in result_state.steps_completed:
                print(f"  ✅ {step}")
        
    except Exception as e:
        print(f"\n❌ Error during workflow execution: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await orchestrator.close()

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
