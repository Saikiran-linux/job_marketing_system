import asyncio
from typing import Dict, Any, List
from datetime import datetime
import json
import os
from agents.base_agent import BaseAgent
from agents.job_search_agent import JobSearchAgent
from agents.skills_analysis_agent import SkillsAnalysisAgent
from agents.resume_analysis_agent import ResumeAnalysisAgent
from agents.resume_modification_agent import ResumeModificationAgent
from agents.application_agent import ApplicationAgent
from config import Config

class OrchestratorAgent(BaseAgent):
    """Main orchestrator agent that coordinates all other agents."""
    
    def __init__(self):
        super().__init__("OrchestratorAgent")
        
        # Initialize all sub-agents
        self.job_search_agent = JobSearchAgent()
        self.skills_analysis_agent = SkillsAnalysisAgent()
        self.resume_analysis_agent = ResumeAnalysisAgent()
        self.resume_modification_agent = ResumeModificationAgent()
        self.application_agent = ApplicationAgent()
        
        # Workflow state
        self.workflow_state = {}
        self.session_id = None
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete job search and application workflow."""
        
        # Validate required inputs
        required_fields = ["role", "resume_path"]
        if not self.validate_input(input_data, required_fields):
            return {"status": "error", "message": "Missing required fields: role and resume_path"}
        
        # Extract input parameters
        role = input_data.get("role")
        resume_path = input_data.get("resume_path")
        location = input_data.get("location", Config.DEFAULT_LOCATION)
        max_jobs = input_data.get("max_jobs", Config.MAX_JOBS_PER_SOURCE)
        auto_apply = input_data.get("auto_apply", False)
        
        # Generate session ID
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.log_action("WORKFLOW_START", f"Session: {self.session_id}, Role: {role}, Location: {location}")
        
        try:
            # Initialize workflow state
            self.workflow_state = {
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "input_parameters": input_data,
                "status": "running",
                "current_step": None,
                "steps_completed": [],
                "results": {}
            }
            
            # Step 1: Analyze current resume
            self.log_action("STEP_1", "Analyzing current resume")
            self.workflow_state["current_step"] = "resume_analysis"
            
            resume_analysis = await self.resume_analysis_agent.safe_execute({
                "resume_path": resume_path
            })
            
            if resume_analysis.get("status") == "error":
                return self._create_error_result("Resume analysis failed", resume_analysis)
            
            self.workflow_state["steps_completed"].append("resume_analysis")
            self.workflow_state["results"]["resume_analysis"] = resume_analysis
            
            # Step 2: Search for jobs
            self.log_action("STEP_2", "Searching for jobs")
            self.workflow_state["current_step"] = "job_search"
            
            job_search_result = await self.job_search_agent.safe_execute({
                "role": role,
                "location": location,
                "max_jobs": max_jobs
            })
            
            if job_search_result.get("status") == "error":
                return self._create_error_result("Job search failed", job_search_result)
            
            jobs_found = job_search_result.get("jobs", [])
            self.log_action("JOBS_FOUND", f"Found {len(jobs_found)} jobs")
            
            self.workflow_state["steps_completed"].append("job_search")
            self.workflow_state["results"]["job_search"] = job_search_result
            
            # Step 3: Process each job
            processed_jobs = []
            successful_applications = 0
            failed_applications = 0
            
            for i, job in enumerate(jobs_found):
                job_id = f"job_{i+1}"
                self.log_action("PROCESSING_JOB", f"{job_id}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                job_result = await self._process_single_job(
                    job, resume_analysis, job_id, auto_apply
                )
                
                processed_jobs.append(job_result)
                
                if job_result.get("application_status", {}).get("status") == "success":
                    successful_applications += 1
                elif job_result.get("application_status", {}).get("status") == "error":
                    failed_applications += 1
                
                # Rate limiting
                await asyncio.sleep(Config.APPLICATION_DELAY)
                
                # Check if we've reached daily limit
                if (successful_applications >= Config.MAX_DAILY_APPLICATIONS):
                    self.log_action("LIMIT_REACHED", f"Daily application limit ({Config.MAX_DAILY_APPLICATIONS}) reached")
                    break
            
            # Step 4: Generate final report
            self.workflow_state["current_step"] = "generating_report"
            final_report = self._generate_final_report(processed_jobs, resume_analysis)
            
            # Complete workflow
            self.workflow_state["status"] = "completed"
            self.workflow_state["end_time"] = datetime.now().isoformat()
            self.workflow_state["current_step"] = "completed"
            self.workflow_state["results"]["final_report"] = final_report
            
            # Save workflow state
            await self._save_workflow_state()
            
            self.log_action("WORKFLOW_COMPLETE", f"Processed {len(processed_jobs)} jobs, {successful_applications} applications submitted")
            
            return {
                "status": "success",
                "session_id": self.session_id,
                "summary": {
                    "jobs_found": len(jobs_found),
                    "jobs_processed": len(processed_jobs),
                    "applications_submitted": successful_applications,
                    "applications_failed": failed_applications,
                    "workflow_duration": self._calculate_duration()
                },
                "processed_jobs": processed_jobs,
                "final_report": final_report,
                "workflow_state": self.workflow_state
            }
            
        except Exception as e:
            self.log_action("WORKFLOW_ERROR", f"Workflow failed: {str(e)}")
            self.workflow_state["status"] = "error"
            self.workflow_state["error"] = str(e)
            self.workflow_state["end_time"] = datetime.now().isoformat()
            
            return {
                "status": "error",
                "message": f"Workflow failed: {str(e)}",
                "session_id": self.session_id,
                "workflow_state": self.workflow_state
            }
    
    async def _process_single_job(self, job: Dict[str, Any], resume_analysis: Dict[str, Any], 
                                job_id: str, auto_apply: bool) -> Dict[str, Any]:
        """Process a single job through the complete pipeline."""
        
        job_result = {
            "job_id": job_id,
            "job_info": job,
            "processing_steps": [],
            "skill_analysis": {},
            "resume_modification": {},
            "application_status": {},
            "processing_timestamp": datetime.now().isoformat()
        }
        
        try:
            # Step 3.1: Analyze job skills
            job_description = job.get("description", "")
            job_title = job.get("title", "")
            
            if job_description:
                skills_analysis = await self.skills_analysis_agent.safe_execute({
                    "job_description": job_description,
                    "job_title": job_title
                })
                
                job_result["skill_analysis"] = skills_analysis
                job_result["processing_steps"].append("skills_analysis")
                
                if skills_analysis.get("status") == "success":
                    required_skills = skills_analysis.get("required_skills", [])
                    
                    # Step 3.2: Modify resume for this job
                    resume_modification = await self.resume_modification_agent.safe_execute({
                        "current_resume": resume_analysis,
                        "required_skills": required_skills,
                        "job_description": job_description,
                        "job_title": job_title,
                        "company_name": job.get("company", "")
                    })
                    
                    job_result["resume_modification"] = resume_modification
                    job_result["processing_steps"].append("resume_modification")
                    
                    # Step 3.3: Apply to job (if enabled)
                    if auto_apply and resume_modification.get("status") == "success":
                        modified_resume_path = resume_modification.get("new_resume_path")
                        
                        if modified_resume_path and os.path.exists(modified_resume_path):
                            # Generate cover letter
                            cover_letter = await self.application_agent.generate_cover_letter(
                                job_description, job_title, job.get("company", ""),
                                resume_analysis.get("resume_content", "")
                            )
                            
                            # Apply to job
                            application_result = await self.application_agent.safe_execute({
                                "job_url": job.get("url", ""),
                                "resume_path": modified_resume_path,
                                "cover_letter": cover_letter,
                                "job_title": job_title,
                                "company_name": job.get("company", "")
                            })
                            
                            job_result["application_status"] = application_result
                            job_result["processing_steps"].append("application")
                        else:
                            job_result["application_status"] = {
                                "status": "skipped",
                                "message": "Modified resume not available"
                            }
                    else:
                        job_result["application_status"] = {
                            "status": "skipped",
                            "message": "Auto-apply disabled or resume modification failed"
                        }
                else:
                    job_result["application_status"] = {
                        "status": "skipped",
                        "message": "Skills analysis failed"
                    }
            else:
                job_result["application_status"] = {
                    "status": "skipped",
                    "message": "No job description available"
                }
            
        except Exception as e:
            job_result["application_status"] = {
                "status": "error",
                "message": f"Job processing failed: {str(e)}"
            }
            self.log_action("JOB_ERROR", f"{job_id}: {str(e)}")
        
        return job_result
    
    def _generate_final_report(self, processed_jobs: List[Dict[str, Any]], 
                             resume_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive final report."""
        
        # Calculate statistics
        total_jobs = len(processed_jobs)
        successful_applications = len([job for job in processed_jobs 
                                     if job.get("application_status", {}).get("status") == "success"])
        failed_applications = len([job for job in processed_jobs 
                                 if job.get("application_status", {}).get("status") == "error"])
        skipped_applications = total_jobs - successful_applications - failed_applications
        
        # Analyze skill gaps across all jobs
        all_required_skills = []
        for job in processed_jobs:
            skills = job.get("skill_analysis", {}).get("required_skills", [])
            all_required_skills.extend([skill.get("skill", "") for skill in skills])
        
        # Count skill frequencies
        from collections import Counter
        skill_frequencies = Counter(all_required_skills)
        top_skills = skill_frequencies.most_common(10)
        
        # Current skills from resume
        current_skills = [skill["skill"] for skill in resume_analysis.get("current_skills", [])]
        
        # Find skill gaps
        missing_skills = []
        for skill, frequency in top_skills:
            if skill.lower() not in [cs.lower() for cs in current_skills]:
                missing_skills.append({"skill": skill, "demand_frequency": frequency})
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            processed_jobs, missing_skills, successful_applications, total_jobs
        )
        
        return {
            "summary": {
                "total_jobs_processed": total_jobs,
                "successful_applications": successful_applications,
                "failed_applications": failed_applications,
                "skipped_applications": skipped_applications,
                "success_rate": (successful_applications / total_jobs * 100) if total_jobs > 0 else 0
            },
            "skill_analysis": {
                "top_required_skills": top_skills,
                "missing_skills": missing_skills[:10],
                "skill_gap_count": len(missing_skills)
            },
            "recommendations": recommendations,
            "job_details": [
                {
                    "job_id": job["job_id"],
                    "title": job["job_info"].get("title", ""),
                    "company": job["job_info"].get("company", ""),
                    "application_status": job["application_status"].get("status", "unknown"),
                    "skill_match_percentage": self._calculate_skill_match_percentage(job)
                }
                for job in processed_jobs
            ]
        }
    
    def _calculate_skill_match_percentage(self, job: Dict[str, Any]) -> float:
        """Calculate skill match percentage for a job."""
        
        required_skills = job.get("skill_analysis", {}).get("required_skills", [])
        if not required_skills:
            return 0.0
        
        # This would need access to current resume skills for accurate calculation
        # For now, return a placeholder
        return 75.0  # Placeholder
    
    def _generate_recommendations(self, processed_jobs: List[Dict[str, Any]], 
                                missing_skills: List[Dict[str, Any]], 
                                successful_applications: int, total_jobs: int) -> List[str]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        # Success rate recommendations
        if total_jobs > 0:
            success_rate = successful_applications / total_jobs * 100
            if success_rate < 30:
                recommendations.append("Consider improving resume content and tailoring it more specifically to job requirements")
            elif success_rate < 60:
                recommendations.append("Good progress! Focus on applying to jobs with better skill matches")
        
        # Skill gap recommendations
        if missing_skills:
            top_missing = missing_skills[:3]
            skills_list = ", ".join([skill["skill"] for skill in top_missing])
            recommendations.append(f"Consider learning these in-demand skills: {skills_list}")
        
        # Application recommendations
        if successful_applications == 0:
            recommendations.append("Review and improve resume formatting and content before the next application cycle")
        elif successful_applications < 5:
            recommendations.append("Increase application volume while maintaining quality")
        
        # Job targeting recommendations
        companies_applied = set()
        for job in processed_jobs:
            if job.get("application_status", {}).get("status") == "success":
                companies_applied.add(job["job_info"].get("company", ""))
        
        if len(companies_applied) < 3:
            recommendations.append("Diversify applications across more companies and industries")
        
        return recommendations
    
    async def _save_workflow_state(self):
        """Save workflow state to file for tracking and recovery."""
        
        try:
            # Create logs directory if it doesn't exist
            os.makedirs(Config.APPLICATION_LOG_DIR, exist_ok=True)
            
            # Save workflow state
            state_file = os.path.join(Config.APPLICATION_LOG_DIR, f"workflow_{self.session_id}.json")
            
            with open(state_file, 'w') as f:
                json.dump(self.workflow_state, f, indent=2, default=str)
            
            self.log_action("STATE_SAVED", f"Workflow state saved to {state_file}")
            
        except Exception as e:
            self.log_action("WARNING", f"Failed to save workflow state: {str(e)}")
    
    def _create_error_result(self, message: str, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized error result."""
        
        self.workflow_state["status"] = "error"
        self.workflow_state["error"] = message
        self.workflow_state["error_details"] = error_data
        self.workflow_state["end_time"] = datetime.now().isoformat()
        
        return {
            "status": "error",
            "message": message,
            "session_id": self.session_id,
            "workflow_state": self.workflow_state,
            "error_details": error_data
        }
    
    def _calculate_duration(self) -> str:
        """Calculate workflow duration."""
        
        if "start_time" in self.workflow_state and "end_time" in self.workflow_state:
            start = datetime.fromisoformat(self.workflow_state["start_time"])
            end = datetime.fromisoformat(self.workflow_state["end_time"])
            duration = end - start
            
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        return "Unknown"
    
    async def get_workflow_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a specific workflow session."""
        
        try:
            state_file = os.path.join(Config.APPLICATION_LOG_DIR, f"workflow_{session_id}.json")
            
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    workflow_state = json.load(f)
                
                return {
                    "status": "found",
                    "workflow_state": workflow_state
                }
            else:
                return {
                    "status": "not_found",
                    "message": f"No workflow found for session {session_id}"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to retrieve workflow status: {str(e)}"
            }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics from all agents."""
        
        return {
            "orchestrator": self.get_stats(),
            "job_search": self.job_search_agent.get_stats(),
            "skills_analysis": self.skills_analysis_agent.get_stats(),
            "resume_analysis": self.resume_analysis_agent.get_stats(),
            "resume_modification": self.resume_modification_agent.get_stats(),
            "application": self.application_agent.get_stats()
        }
