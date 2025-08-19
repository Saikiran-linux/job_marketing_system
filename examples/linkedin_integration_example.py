#!/usr/bin/env python3
"""
LinkedIn Integration Example

This example demonstrates how to use the LinkedIn API integration
to search for jobs and apply to them directly through the API.

Prerequisites:
1. Set up LinkedIn Developer account at https://www.linkedin.com/developers/
2. Create a LinkedIn application
3. Configure environment variables (see env_template.txt)
4. Install required dependencies

Environment Variables Required:
- LINKEDIN_CLIENT_ID
- LINKEDIN_CLIENT_SECRET  
- LINKEDIN_REFRESH_TOKEN
- OPENAI_API_KEY (for AI-powered cover letters)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to the path to import the agents
sys.path.append(str(Path(__file__).parent.parent))

from agents.linkedin_agent import LinkedInAgent
from agents.application_agent import ApplicationAgent
from agents.job_search_agent import JobSearchAgent
from config import Config

async def linkedin_job_search_example():
    """Example of searching for jobs on LinkedIn using the API."""
    
    print("🔍 LinkedIn Job Search Example")
    print("=" * 50)
    
    # Initialize LinkedIn agent
    linkedin_agent = LinkedInAgent()
    
    try:
        # Search for jobs
        search_input = {
            "operation": "search",
            "keywords": "Python Developer",
            "location": "Remote",
            "max_results": 10,
            "experience_level": "entry",
            "job_type": "full-time"
        }
        
        print(f"Searching for: {search_input['keywords']} in {search_input['location']}")
        result = await linkedin_agent.execute(search_input)
        
        if result.get("status") == "success":
            jobs = result.get("jobs", [])
            print(f"✅ Found {len(jobs)} jobs on LinkedIn")
            
            # Display job results
            for i, job in enumerate(jobs[:5], 1):  # Show first 5 jobs
                print(f"\n{i}. {job.get('title', 'Unknown Title')}")
                print(f"   Company: {job.get('company', 'Unknown Company')}")
                print(f"   Location: {job.get('location', 'Unknown Location')}")
                print(f"   Easy Apply: {'✅' if job.get('easy_apply') else '❌'}")
                print(f"   URL: {job.get('url', 'N/A')}")
                
                if job.get('description'):
                    desc = job['description'][:100] + "..." if len(job['description']) > 100 else job['description']
                    print(f"   Description: {desc}")
            
            return jobs
        else:
            print(f"❌ Job search failed: {result.get('message')}")
            return []
            
    except Exception as e:
        print(f"❌ Error during job search: {str(e)}")
        return []
    finally:
        await linkedin_agent.close()

async def linkedin_job_details_example(job_id: str):
    """Example of getting detailed job information."""
    
    print(f"\n📋 Job Details Example for Job ID: {job_id}")
    print("=" * 50)
    
    linkedin_agent = LinkedInAgent()
    
    try:
        details_input = {
            "operation": "get_job_details",
            "job_id": job_id
        }
        
        result = await linkedin_agent.execute(details_input)
        
        if result.get("status") == "success":
            job = result.get("job", {})
            print(f"✅ Job Details Retrieved")
            print(f"Title: {job.get('title', 'Unknown')}")
            print(f"Company: {job.get('company', 'Unknown')}")
            print(f"Location: {job.get('location', 'Unknown')}")
            print(f"Experience Level: {job.get('experience_level', 'Unknown')}")
            print(f"Job Type: {job.get('job_type', 'Unknown')}")
            print(f"Easy Apply: {'✅' if job.get('easy_apply') else '❌'}")
            print(f"Application Count: {job.get('application_count', 'Unknown')}")
            
            if job.get('requirements'):
                print(f"Requirements: {job['requirements'][:200]}...")
                
            return job
        else:
            print(f"❌ Failed to get job details: {result.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting job details: {str(e)}")
        return None
    finally:
        await linkedin_agent.close()

async def linkedin_application_example(job_id: str, resume_path: str):
    """Example of applying to a job on LinkedIn using the API."""
    
    print(f"\n📝 LinkedIn Application Example")
    print("=" * 50)
    
    linkedin_agent = LinkedInAgent()
    
    try:
        # Generate a sample cover letter
        cover_letter = """Dear Hiring Manager,

I am writing to express my strong interest in this position. With my background in software development and passion for creating innovative solutions, I believe I would be a valuable addition to your team.

I am particularly drawn to the opportunity to work with cutting-edge technologies and contribute to meaningful projects. I am excited about the possibility of joining your organization and would welcome the chance to discuss how I can contribute to your continued success.

Thank you for considering my application.

Best regards,
[Your Name]"""
        
        application_input = {
            "operation": "apply",
            "job_id": job_id,
            "resume_path": resume_path,
            "cover_letter": cover_letter
        }
        
        print(f"Applying to job ID: {job_id}")
        print(f"Resume: {resume_path}")
        print("Cover Letter: [Generated cover letter]")
        
        result = await linkedin_agent.execute(application_input)
        
        if result.get("status") == "success":
            print("✅ Application submitted successfully!")
            print(f"Application ID: {result.get('application_id', 'N/A')}")
        elif result.get("status") == "not_supported":
            print("⚠️ Easy Apply not available for this job via API")
            print("Consider using web automation instead")
        else:
            print(f"❌ Application failed: {result.get('message')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Error during application: {str(e)}")
        return {"status": "error", "message": str(e)}
    finally:
        await linkedin_agent.close()

async def linkedin_applications_history_example():
    """Example of retrieving application history."""
    
    print(f"\n📊 Application History Example")
    print("=" * 50)
    
    linkedin_agent = LinkedInAgent()
    
    try:
        history_input = {
            "operation": "get_applications"
        }
        
        result = await linkedin_agent.execute(history_input)
        
        if result.get("status") == "success":
            applications = result.get("applications", [])
            print(f"✅ Retrieved {len(applications)} applications")
            
            for i, app in enumerate(applications[:5], 1):  # Show first 5
                print(f"\n{i}. {app.get('job_title', 'Unknown Title')}")
                print(f"   Company: {app.get('company', 'Unknown Company')}")
                print(f"   Applied: {app.get('application_date', 'Unknown Date')}")
                print(f"   Status: {app.get('status', 'Unknown Status')}")
                
            return applications
        else:
            print(f"❌ Failed to get applications: {result.get('message')}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting applications: {str(e)}")
        return []
    finally:
        await linkedin_agent.close()

async def integrated_job_search_example():
    """Example of using the integrated job search with LinkedIn API."""
    
    print(f"\n🔍 Integrated Job Search Example")
    print("=" * 50)
    
    job_search_agent = JobSearchAgent()
    
    try:
        search_input = {
            "role": "Software Engineer",
            "location": "Remote",
            "max_jobs": 20
        }
        
        print(f"Searching for: {search_input['role']} in {search_input['location']}")
        result = await job_search_agent.execute(search_input)
        
        if result.get("status") == "success":
            jobs = result.get("jobs", [])
            print(f"✅ Found {len(jobs)} total jobs across all sources")
            
            # Count jobs by source
            source_counts = {}
            for job in jobs:
                source = job.get("source", "unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
            
            print("\nJobs by source:")
            for source, count in source_counts.items():
                print(f"  {source}: {count} jobs")
                
            return jobs
        else:
            print(f"❌ Job search failed: {result.get('message')}")
            return []
            
    except Exception as e:
        print(f"❌ Error during integrated search: {str(e)}")
        return []
    finally:
        await job_search_agent._close_linkedin_agent()

async def main():
    """Main function demonstrating LinkedIn integration features."""
    
    print("🚀 LinkedIn API Integration Demo")
    print("=" * 60)
    
    # Check configuration
    if not Config.validate_config():
        print("⚠️ Configuration validation failed. Please check your environment variables.")
        print("Required: LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REFRESH_TOKEN")
        return
    
    # Check LinkedIn API configuration
    linkedin_configured = all([
        Config.LINKEDIN_CLIENT_ID,
        Config.LINKEDIN_CLIENT_SECRET,
        Config.LINKEDIN_REFRESH_TOKEN
    ])
    
    if not linkedin_configured:
        print("❌ LinkedIn API credentials not configured")
        print("Please set the following environment variables:")
        print("- LINKEDIN_CLIENT_ID")
        print("- LINKEDIN_CLIENT_SECRET")
        print("- LINKEDIN_REFRESH_TOKEN")
        return
    
    print("✅ LinkedIn API credentials configured")
    
    try:
        # Example 1: Search for jobs
        jobs = await linkedin_job_search_example()
        
        if jobs:
            # Example 2: Get job details for the first job
            first_job = jobs[0]
            job_id = first_job.get("id")
            
            if job_id:
                await linkedin_job_details_example(job_id)
                
                # Example 3: Application (simulated - won't actually submit)
                print("\n⚠️ Note: Application example is simulated for safety")
                resume_path = "./data/sample_resume.pdf"  # Placeholder path
                
                # Check if job supports Easy Apply
                if first_job.get("easy_apply"):
                    await linkedin_application_example(job_id, resume_path)
                else:
                    print("This job doesn't support Easy Apply via API")
        
        # Example 4: Application history
        await linkedin_applications_history_example()
        
        # Example 5: Integrated search
        await integrated_job_search_example()
        
        print("\n🎉 LinkedIn Integration Demo Completed!")
        print("\nNext Steps:")
        print("1. Configure your actual LinkedIn API credentials")
        print("2. Update resume paths to your actual resume files")
        print("3. Test with real job applications")
        print("4. Monitor application status and responses")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
