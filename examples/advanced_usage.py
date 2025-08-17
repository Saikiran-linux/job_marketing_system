#!/usr/bin/env python3
"""
Advanced usage examples for the Multi-Agent Job Application System.
"""

import asyncio
import os
import sys
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator_agent import OrchestratorAgent
from agents.job_search_agent import JobSearchAgent
from agents.skills_analysis_agent import SkillsAnalysisAgent
from agents.resume_modification_agent import ResumeModificationAgent
from agents.application_agent import ApplicationAgent
from utils.database import ApplicationDatabase
from utils.report_generator import ReportGenerator
from config import Config

async def example_1_custom_job_filtering():
    """Example 1: Custom job filtering and ranking."""
    
    print("=" * 60)
    print("ADVANCED EXAMPLE 1: Custom Job Filtering")
    print("=" * 60)
    
    job_search_agent = JobSearchAgent()
    
    # Search for jobs
    result = await job_search_agent.execute({
        "role": "Machine Learning Engineer",
        "location": "remote",
        "max_jobs": 20
    })
    
    if result.get("status") == "success":
        jobs = result.get("jobs", [])
        
        # Custom filtering logic
        filtered_jobs = custom_filter_jobs(jobs, {
            "required_keywords": ["python", "machine learning", "tensorflow"],
            "excluded_keywords": ["junior", "intern"],
            "min_description_length": 200,
            "preferred_companies": ["google", "microsoft", "amazon"]
        })
        
        print(f"✅ Filtered {len(jobs)} jobs down to {len(filtered_jobs)} matches")
        
        # Rank jobs by custom scoring
        ranked_jobs = rank_jobs_by_relevance(filtered_jobs, "Machine Learning Engineer")
        
        print(f"\n🏆 Top 5 ranked jobs:")
        for i, (job, score) in enumerate(ranked_jobs[:5], 1):
            print(f"   {i}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
            print(f"      Score: {score:.2f}/10")
            print(f"      URL: {job.get('url', 'No URL')[:50]}...")
            print()

async def example_2_batch_resume_optimization():
    """Example 2: Optimize resume for multiple job types."""
    
    print("=" * 60)
    print("ADVANCED EXAMPLE 2: Batch Resume Optimization")
    print("=" * 60)
    
    # Different job profiles to optimize for
    job_profiles = [
        {
            "role": "Backend Developer",
            "skills": ["python", "django", "postgresql", "redis", "aws"],
            "description": "Backend development with Python and cloud technologies"
        },
        {
            "role": "Data Scientist",
            "skills": ["python", "pandas", "scikit-learn", "tensorflow", "sql"],
            "description": "Data analysis and machine learning model development"
        },
        {
            "role": "DevOps Engineer", 
            "skills": ["docker", "kubernetes", "jenkins", "terraform", "aws"],
            "description": "Infrastructure automation and deployment pipelines"
        }
    ]
    
    resume_mod_agent = ResumeModificationAgent()
    
    # Create sample resume analysis (you'd normally get this from ResumeAnalysisAgent)
    sample_resume = {
        "resume_content": "Software Engineer with Python experience...",
        "current_skills": [
            {"skill": "python", "mention_count": 3},
            {"skill": "sql", "mention_count": 2},
            {"skill": "aws", "mention_count": 1}
        ]
    }
    
    optimized_resumes = []
    
    for profile in job_profiles:
        print(f"\n🔧 Optimizing resume for {profile['role']}...")
        
        # Convert skills to required format
        required_skills = [
            {"skill": skill, "confidence": 0.8} for skill in profile["skills"]
        ]
        
        result = await resume_mod_agent.execute({
            "current_resume": sample_resume,
            "required_skills": required_skills,
            "job_description": profile["description"],
            "job_title": profile["role"],
            "company_name": "Target Company"
        })
        
        if result.get("status") == "success":
            optimized_resumes.append({
                "role": profile["role"],
                "resume_path": result.get("new_resume_path"),
                "modifications": result.get("modifications_made", [])
            })
            print(f"   ✅ Resume optimized: {result.get('new_resume_path')}")
            print(f"   📝 Modifications: {len(result.get('modifications_made', []))}")
        else:
            print(f"   ❌ Optimization failed: {result.get('message')}")
    
    print(f"\n📋 Generated {len(optimized_resumes)} optimized resumes")

async def example_3_skill_gap_analysis():
    """Example 3: Comprehensive skill gap analysis across multiple jobs."""
    
    print("\n" + "=" * 60)
    print("ADVANCED EXAMPLE 3: Skill Gap Analysis")
    print("=" * 60)
    
    # Simulate multiple job descriptions
    job_descriptions = [
        "Python developer with Django, PostgreSQL, and AWS experience required",
        "Data scientist needed with Python, pandas, scikit-learn, and TensorFlow",
        "DevOps engineer with Docker, Kubernetes, Jenkins, and Terraform experience",
        "Full-stack developer with React, Node.js, MongoDB, and TypeScript skills",
        "Machine learning engineer with PyTorch, MLflow, and cloud deployment experience"
    ]
    
    skills_agent = SkillsAnalysisAgent()
    all_required_skills = []
    
    # Analyze skills from all job descriptions
    for i, description in enumerate(job_descriptions, 1):
        print(f"Analyzing job {i}...")
        
        result = await skills_agent.execute({
            "job_description": description,
            "job_title": f"Job {i}"
        })
        
        if result.get("status") == "success":
            required_skills = result.get("required_skills", [])
            all_required_skills.extend(required_skills)
    
    # Analyze skill demand patterns
    skill_demand = analyze_skill_demand(all_required_skills)
    
    print(f"\n📊 Skill Demand Analysis:")
    print(f"   Total unique skills: {len(skill_demand)}")
    
    print(f"\n🔥 Most in-demand skills:")
    for skill, data in list(skill_demand.items())[:10]:
        frequency = data["frequency"]
        avg_confidence = data["avg_confidence"]
        print(f"   • {skill}: {frequency} jobs (confidence: {avg_confidence:.2f})")
    
    # Generate learning recommendations
    recommendations = generate_learning_recommendations(skill_demand)
    
    print(f"\n💡 Learning Recommendations:")
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"   {i}. {rec}")

async def example_4_application_monitoring():
    """Example 4: Application tracking and monitoring."""
    
    print("\n" + "=" * 60)
    print("ADVANCED EXAMPLE 4: Application Monitoring")
    print("=" * 60)
    
    # Initialize database and application agent
    db = ApplicationDatabase()
    app_agent = ApplicationAgent()
    
    # Simulate some application data
    sample_applications = [
        {
            "session_id": "demo_session_1",
            "job_id": "job_1",
            "job_title": "Python Developer",
            "company_name": "TechCorp",
            "job_url": "https://example.com/job1",
            "application_status": "success",
            "resume_path": "./output/resume_python_dev.docx"
        },
        {
            "session_id": "demo_session_1", 
            "job_id": "job_2",
            "job_title": "Data Scientist",
            "company_name": "DataInc",
            "job_url": "https://example.com/job2", 
            "application_status": "failed",
            "resume_path": "./output/resume_data_scientist.docx"
        }
    ]
    
    # Save sample applications
    for app_data in sample_applications:
        app_id = db.save_application(app_data)
        print(f"📝 Saved application {app_id}: {app_data['job_title']} at {app_data['company_name']}")
    
    # Get application statistics
    stats = db.get_application_statistics(days=30)
    
    print(f"\n📊 Application Statistics (last 30 days):")
    print(f"   Total applications: {stats['total_applications']}")
    print(f"   Success rate: {stats.get('applications_by_status', {}).get('success', 0)} successful")
    print(f"   Top companies: {len(stats.get('top_companies', []))}")
    
    # Get agent stats
    agent_stats = app_agent.get_application_stats()
    print(f"\n🤖 Application Agent Stats:")
    print(f"   Applications today: {agent_stats['applications_today']}")
    print(f"   Daily limit: {agent_stats['daily_limit']}")
    print(f"   Remaining: {agent_stats['remaining_applications']}")

async def example_5_workflow_customization():
    """Example 5: Custom workflow with conditional logic."""
    
    print("\n" + "=" * 60)
    print("ADVANCED EXAMPLE 5: Custom Workflow")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent()
    
    # Custom workflow parameters
    workflow_config = {
        "role": "Software Engineer",
        "resume_path": "./data/sample_resume.docx", 
        "location": "remote",
        "max_jobs": 10,
        "skill_threshold": 0.7,  # Only apply if skill match > 70%
        "company_preferences": ["google", "microsoft", "amazon"],
        "auto_apply": False
    }
    
    print(f"🚀 Starting custom workflow for {workflow_config['role']}")
    
    # Create sample resume if needed
    if not os.path.exists(workflow_config["resume_path"]):
        from examples.basic_usage import create_sample_resume
        os.makedirs(os.path.dirname(workflow_config["resume_path"]), exist_ok=True)
        create_sample_resume(workflow_config["resume_path"])
    
    # Execute with custom logic
    result = await orchestrator.execute(workflow_config)
    
    if result.get("status") == "success":
        processed_jobs = result.get("processed_jobs", [])
        
        # Apply custom post-processing
        high_match_jobs = []
        preferred_company_jobs = []
        
        for job in processed_jobs:
            job_info = job.get("job_info", {})
            company = job_info.get("company", "").lower()
            
            # Check if company is in preferences
            if any(pref in company for pref in workflow_config["company_preferences"]):
                preferred_company_jobs.append(job)
            
            # Check skill match (this would need actual calculation)
            # For demo, we'll simulate
            simulated_skill_match = 0.75  # Would be calculated from skill analysis
            if simulated_skill_match > workflow_config["skill_threshold"]:
                high_match_jobs.append(job)
        
        print(f"✅ Workflow completed with custom filtering:")
        print(f"   Total jobs processed: {len(processed_jobs)}")
        print(f"   High skill match (>{workflow_config['skill_threshold']*100}%): {len(high_match_jobs)}")
        print(f"   Preferred companies: {len(preferred_company_jobs)}")
        
        # Generate custom recommendations
        if len(high_match_jobs) < 3:
            print(f"\n💡 Recommendation: Broaden search criteria or lower skill threshold")
        
        if len(preferred_company_jobs) == 0:
            print(f"\n💡 Recommendation: Consider expanding company preferences")

def custom_filter_jobs(jobs: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filter jobs based on custom criteria."""
    
    filtered = []
    
    for job in jobs:
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()
        company = job.get("company", "").lower()
        
        # Check required keywords
        required_keywords = criteria.get("required_keywords", [])
        has_required = all(keyword.lower() in description for keyword in required_keywords)
        
        # Check excluded keywords
        excluded_keywords = criteria.get("excluded_keywords", [])
        has_excluded = any(keyword.lower() in title or keyword.lower() in description 
                          for keyword in excluded_keywords)
        
        # Check description length
        min_length = criteria.get("min_description_length", 0)
        long_enough = len(description) >= min_length
        
        # Check preferred companies (bonus, not required)
        preferred_companies = criteria.get("preferred_companies", [])
        is_preferred = any(pref.lower() in company for pref in preferred_companies)
        
        # Apply filters
        if has_required and not has_excluded and long_enough:
            job["is_preferred_company"] = is_preferred
            filtered.append(job)
    
    return filtered

def rank_jobs_by_relevance(jobs: List[Dict[str, Any]], target_role: str) -> List[tuple]:
    """Rank jobs by relevance score."""
    
    scored_jobs = []
    
    for job in jobs:
        score = calculate_job_score(job, target_role)
        scored_jobs.append((job, score))
    
    # Sort by score (descending)
    scored_jobs.sort(key=lambda x: x[1], reverse=True)
    
    return scored_jobs

def calculate_job_score(job: Dict[str, Any], target_role: str) -> float:
    """Calculate relevance score for a job."""
    
    score = 0.0
    
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    company = job.get("company", "").lower()
    
    # Title similarity (simple keyword matching)
    target_keywords = target_role.lower().split()
    title_matches = sum(1 for keyword in target_keywords if keyword in title)
    score += title_matches * 2.0
    
    # Description length (more detailed = better)
    desc_length = len(description)
    if desc_length > 500:
        score += 1.0
    elif desc_length > 200:
        score += 0.5
    
    # Company preference bonus
    if job.get("is_preferred_company", False):
        score += 2.0
    
    # Has URL (can apply)
    if job.get("url"):
        score += 0.5
    
    # Salary mentioned (more complete posting)
    if job.get("salary"):
        score += 0.5
    
    return min(score, 10.0)  # Cap at 10

def analyze_skill_demand(all_skills: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Analyze skill demand patterns."""
    
    skill_stats = {}
    
    for skill_data in all_skills:
        skill_name = skill_data.get("skill", "").lower()
        confidence = skill_data.get("confidence", 0)
        
        if skill_name not in skill_stats:
            skill_stats[skill_name] = {
                "frequency": 0,
                "total_confidence": 0,
                "avg_confidence": 0
            }
        
        skill_stats[skill_name]["frequency"] += 1
        skill_stats[skill_name]["total_confidence"] += confidence
    
    # Calculate averages
    for skill_name, data in skill_stats.items():
        if data["frequency"] > 0:
            data["avg_confidence"] = data["total_confidence"] / data["frequency"]
    
    # Sort by frequency then confidence
    sorted_skills = dict(sorted(
        skill_stats.items(),
        key=lambda x: (x[1]["frequency"], x[1]["avg_confidence"]),
        reverse=True
    ))
    
    return sorted_skills

def generate_learning_recommendations(skill_demand: Dict[str, Dict[str, Any]]) -> List[str]:
    """Generate learning recommendations based on skill demand."""
    
    recommendations = []
    
    top_skills = list(skill_demand.items())[:10]
    
    # High-demand skills
    high_demand = [skill for skill, data in top_skills if data["frequency"] >= 3]
    if high_demand:
        recommendations.append(f"Focus on high-demand skills: {', '.join(high_demand[:3])}")
    
    # Skills with high confidence (employers really want them)
    high_confidence = [skill for skill, data in top_skills if data["avg_confidence"] > 0.8]
    if high_confidence:
        recommendations.append(f"Critical skills to learn: {', '.join(high_confidence[:3])}")
    
    # Technology trends
    cloud_skills = [skill for skill in skill_demand.keys() if any(cloud in skill for cloud in ["aws", "azure", "docker", "kubernetes"])]
    if cloud_skills:
        recommendations.append(f"Cloud technologies are trending: {', '.join(cloud_skills[:2])}")
    
    # Programming languages
    prog_langs = [skill for skill in skill_demand.keys() if skill in ["python", "javascript", "java", "typescript", "go"]]
    if prog_langs:
        recommendations.append(f"Consider strengthening: {', '.join(prog_langs[:2])}")
    
    return recommendations

async def main():
    """Run all advanced examples."""
    
    print("🚀 Multi-Agent Job Application System - Advanced Examples")
    print("=" * 70)
    print("These examples demonstrate advanced features and customization options.")
    print()
    
    try:
        await example_1_custom_job_filtering()
        await example_2_batch_resume_optimization()
        await example_3_skill_gap_analysis()
        await example_4_application_monitoring()
        await example_5_workflow_customization()
        
        print("\n" + "=" * 70)
        print("✅ All advanced examples completed!")
        print("=" * 70)
        print("\nAdvanced features demonstrated:")
        print("• Custom job filtering and ranking")
        print("• Batch resume optimization for multiple roles")
        print("• Comprehensive skill gap analysis")
        print("• Application tracking and monitoring")
        print("• Custom workflow with conditional logic")
        print("\nNext steps:")
        print("• Modify examples for your specific use cases")
        print("• Implement custom filtering logic")
        print("• Create role-specific optimization profiles")
        
    except KeyboardInterrupt:
        print("\n❌ Advanced examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Advanced example failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
