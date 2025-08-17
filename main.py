#!/usr/bin/env python3
"""
Main entry point for the Multi-Agent Job Application System.

This script provides a command-line interface to run the job search and application workflow.
"""

import asyncio
import argparse
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator_agent import OrchestratorAgent
from config import Config
from utils.logger import setup_logger

logger = setup_logger("MainRunner")

async def main():
    """Main entry point for the application."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Multi-Agent Job Application System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --role "Software Engineer" --resume "./resume.docx"
  python main.py --role "Data Scientist" --location "San Francisco" --max-jobs 20 --auto-apply
  python main.py --role "Python Developer" --resume "./resume.docx" --location "remote" --dry-run
        """
    )
    
    parser.add_argument(
        "--role", 
        required=True, 
        help="Target job role/title to search for"
    )
    
    parser.add_argument(
        "--resume", 
        required=True, 
        help="Path to your resume file (.docx or .txt)"
    )
    
    parser.add_argument(
        "--location", 
        default=Config.DEFAULT_LOCATION, 
        help=f"Job location (default: {Config.DEFAULT_LOCATION})"
    )
    
    parser.add_argument(
        "--max-jobs", 
        type=int, 
        default=Config.MAX_JOBS_PER_SOURCE, 
        help=f"Maximum number of jobs to process (default: {Config.MAX_JOBS_PER_SOURCE})"
    )
    
    parser.add_argument(
        "--auto-apply", 
        action="store_true", 
        help="Automatically apply to jobs (use with caution)"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Run without actually applying to jobs"
    )
    
    parser.add_argument(
        "--config-check", 
        action="store_true", 
        help="Check configuration and exit"
    )
    
    parser.add_argument(
        "--session-id", 
        help="Resume a previous workflow session"
    )
    
    args = parser.parse_args()
    
    # Check configuration
    if args.config_check:
        check_configuration()
        return
    
    # Validate configuration
    if not Config.validate_config():
        logger.error("Configuration validation failed. Please check your .env file.")
        return
    
    # Create necessary directories
    Config.create_directories()
    
    # Validate resume file
    if not os.path.exists(args.resume):
        logger.error(f"Resume file not found: {args.resume}")
        return
    
    # Log startup
    logger.info("=" * 60)
    logger.info("Multi-Agent Job Application System Starting")
    logger.info("=" * 60)
    logger.info(f"Role: {args.role}")
    logger.info(f"Resume: {args.resume}")
    logger.info(f"Location: {args.location}")
    logger.info(f"Max Jobs: {args.max_jobs}")
    logger.info(f"Auto Apply: {args.auto_apply}")
    logger.info(f"Dry Run: {args.dry_run}")
    
    try:
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        # Resume existing session or start new workflow
        if args.session_id:
            result = await resume_workflow(orchestrator, args.session_id)
        else:
            result = await run_workflow(orchestrator, args)
        
        # Display results
        display_results(result)
        
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        raise

async def run_workflow(orchestrator: OrchestratorAgent, args) -> Dict[str, Any]:
    """Run the complete workflow."""
    
    input_data = {
        "role": args.role,
        "resume_path": args.resume,
        "location": args.location,
        "max_jobs": args.max_jobs,
        "auto_apply": args.auto_apply and not args.dry_run
    }
    
    logger.info("Starting workflow execution...")
    start_time = datetime.now()
    
    result = await orchestrator.safe_execute(input_data)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info(f"Workflow completed in {duration}")
    
    return result

async def resume_workflow(orchestrator: OrchestratorAgent, session_id: str) -> Dict[str, Any]:
    """Resume a previous workflow session."""
    
    logger.info(f"Attempting to resume workflow session: {session_id}")
    
    status_result = await orchestrator.get_workflow_status(session_id)
    
    if status_result.get("status") == "found":
        workflow_state = status_result.get("workflow_state", {})
        logger.info(f"Found session {session_id} with status: {workflow_state.get('status', 'unknown')}")
        
        if workflow_state.get("status") == "completed":
            logger.info("Session already completed")
            return {"status": "already_completed", "workflow_state": workflow_state}
        else:
            logger.warning("Session resumption not fully implemented - displaying last known state")
            return {"status": "resumed", "workflow_state": workflow_state}
    else:
        logger.error(f"Session {session_id} not found")
        return {"status": "not_found"}

def display_results(result: Dict[str, Any]):
    """Display workflow results in a user-friendly format."""
    
    print("\n" + "=" * 60)
    print("WORKFLOW RESULTS")
    print("=" * 60)
    
    if result.get("status") == "success":
        summary = result.get("summary", {})
        
        print(f"Session ID: {result.get('session_id', 'Unknown')}")
        print(f"Jobs Found: {summary.get('jobs_found', 0)}")
        print(f"Jobs Processed: {summary.get('jobs_processed', 0)}")
        print(f"Applications Submitted: {summary.get('applications_submitted', 0)}")
        print(f"Applications Failed: {summary.get('applications_failed', 0)}")
        print(f"Workflow Duration: {summary.get('workflow_duration', 'Unknown')}")
        
        # Display job details
        processed_jobs = result.get("processed_jobs", [])
        if processed_jobs:
            print("\nJOB PROCESSING DETAILS:")
            print("-" * 40)
            
            for job in processed_jobs[:10]:  # Show first 10 jobs
                job_info = job.get("job_info", {})
                app_status = job.get("application_status", {})
                
                print(f"• {job_info.get('title', 'Unknown Title')} at {job_info.get('company', 'Unknown Company')}")
                print(f"  Status: {app_status.get('status', 'unknown')}")
                
                if len(processed_jobs) > 10:
                    print(f"... and {len(processed_jobs) - 10} more jobs")
        
        # Display recommendations
        final_report = result.get("final_report", {})
        recommendations = final_report.get("recommendations", [])
        
        if recommendations:
            print("\nRECOMMENDATIONS:")
            print("-" * 40)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        
        # Display skill analysis
        skill_analysis = final_report.get("skill_analysis", {})
        missing_skills = skill_analysis.get("missing_skills", [])
        
        if missing_skills:
            print("\nTOP MISSING SKILLS:")
            print("-" * 40)
            for skill_data in missing_skills[:5]:
                skill = skill_data.get("skill", "")
                frequency = skill_data.get("demand_frequency", 0)
                print(f"• {skill} (mentioned in {frequency} jobs)")
    
    elif result.get("status") == "error":
        print(f"❌ Workflow failed: {result.get('message', 'Unknown error')}")
        
        error_details = result.get("error_details", {})
        if error_details:
            print(f"Error details: {error_details}")
    
    else:
        print(f"Workflow status: {result.get('status', 'unknown')}")
        print(f"Message: {result.get('message', 'No message')}")
    
    print("\n" + "=" * 60)

def check_configuration():
    """Check and display configuration status."""
    
    print("\n" + "=" * 60)
    print("CONFIGURATION CHECK")
    print("=" * 60)
    
    # Check required configuration
    config_status = {
        "OpenAI API Key": "✅" if Config.OPENAI_API_KEY else "❌",
        "Output Resume Directory": "✅" if os.path.exists(Config.OUTPUT_RESUME_DIR) else "⚠️ (will be created)",
        "Application Log Directory": "✅" if os.path.exists(Config.APPLICATION_LOG_DIR) else "⚠️ (will be created)",
    }
    
    print("Required Configuration:")
    for item, status in config_status.items():
        print(f"  {item}: {status}")
    
    # Check optional configuration
    optional_config = {
        "LinkedIn Email": "✅" if Config.LINKEDIN_EMAIL else "❌ (LinkedIn applications disabled)",
        "Indeed Email": "✅" if Config.INDEED_EMAIL else "❌ (Indeed applications may be limited)",
    }
    
    print("\nOptional Configuration:")
    for item, status in optional_config.items():
        print(f"  {item}: {status}")
    
    # Display current settings
    print(f"\nCurrent Settings:")
    print(f"  Max Jobs Per Source: {Config.MAX_JOBS_PER_SOURCE}")
    print(f"  Application Delay: {Config.APPLICATION_DELAY} seconds")
    print(f"  Max Daily Applications: {Config.MAX_DAILY_APPLICATIONS}")
    print(f"  Default Location: {Config.DEFAULT_LOCATION}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
