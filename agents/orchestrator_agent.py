import asyncio
from typing import Dict, Any, List, Annotated
from datetime import datetime
import json
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent, AgentState
from agents.job_search_agent import JobSearchAgent
from agents.skills_analysis_agent import SkillsAnalysisAgent
from agents.resume_analysis_agent import ResumeAnalysisAgent
from agents.resume_modification_agent import ResumeModificationAgent
from agents.application_agent import ApplicationAgent
from config import Config

class OrchestratorAgent(BaseAgent):
    """Main orchestrator agent that coordinates all other agents using LangGraph."""
    
    def __init__(self):
        super().__init__("OrchestratorAgent")
        
        # Initialize all sub-agents
        self.job_search_agent = JobSearchAgent()
        self.skills_analysis_agent = SkillsAnalysisAgent()
        self.resume_analysis_agent = ResumeAnalysisAgent()
        self.resume_modification_agent = ResumeModificationAgent()
        self.application_agent = ApplicationAgent()
        
        # Create the LangGraph workflow
        self.workflow = self._create_workflow()
        
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with all nodes and edges."""
        
        # Create the workflow graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for each step
        workflow.add_node("resume_analysis", self.resume_analysis_agent.create_node())
        workflow.add_node("job_search", self.job_search_agent.create_node())
        workflow.add_node("process_jobs", self._create_job_processing_node())
        workflow.add_node("generate_report", self._create_report_generation_node())
        
        # Define the workflow flow
        workflow.set_entry_point("resume_analysis")
        workflow.add_edge("resume_analysis", "job_search")
        workflow.add_edge("job_search", "process_jobs")
        workflow.add_edge("process_jobs", "generate_report")
        workflow.add_edge("generate_report", END)
        
        # Compile the workflow
        return workflow.compile()
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the complete job search and application workflow using LangGraph."""
        
        # Validate required inputs
        required_fields = ["role", "resume_path"]
        if not self.validate_input(state, required_fields):
            state.status = "error"
            state.error = "Missing required fields: role and resume_path"
            return state
        
        # Generate session ID and initialize state
        state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        state.start_time = datetime.now().isoformat()
        state.current_step = "starting"
        
        self.log_action("WORKFLOW_START", f"Session: {state.session_id}, Role: {state.role}, Location: {state.location}")
        
        try:
            # Execute the workflow
            final_state = await self.workflow.ainvoke(state)
            
            # Calculate duration
            if final_state.start_time and final_state.end_time:
                start = datetime.fromisoformat(final_state.start_time)
                end = datetime.fromisoformat(final_state.end_time)
                duration = end - start
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                final_state.workflow_duration = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            
            # Save workflow state
            await self._save_workflow_state(final_state)
            
            self.log_action("WORKFLOW_COMPLETE", f"Session {final_state.session_id} completed successfully")
            
            return final_state
            
        except Exception as e:
            self.log_action("WORKFLOW_ERROR", f"Workflow failed: {str(e)}")
            state.status = "error"
            state.error = f"Workflow failed: {str(e)}"
            state.end_time = datetime.now().isoformat()
            return state
    
    def _create_job_processing_node(self) -> callable:
        """Create a node for processing individual jobs."""
        async def process_jobs_node(state: AgentState) -> AgentState:
            """Process each job through skills analysis, resume modification, and application."""
            
            if not state.job_search_results or state.job_search_results.get("status") != "success":
                state.error = "Job search failed, cannot process jobs"
                return state
            
            jobs_found = state.job_search_results.get("jobs", [])
            self.log_action("PROCESSING_JOBS", f"Processing {len(jobs_found)} jobs")
            
            processed_jobs = []
            successful_applications = 0
            failed_applications = 0
            
            for i, job in enumerate(jobs_found):
                job_id = f"job_{i+1}"
                self.log_action("PROCESSING_JOB", f"{job_id}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                job_result = await self._process_single_job(
                    job, state.resume_analysis, job_id, state.auto_apply
                )
                
                processed_jobs.append(job_result)
                
                if job_result.get("application_status", {}).get("status") == "success":
                    successful_applications += 1
                elif job_result.get("application_status", {}).get("status") == "error":
                    failed_applications += 1
                
                # Rate limiting
                await asyncio.sleep(Config.APPLICATION_DELAY)
                
                # Check if we've reached daily limit
                if successful_applications >= Config.MAX_DAILY_APPLICATIONS:
                    self.log_action("LIMIT_REACHED", f"Daily application limit ({Config.MAX_DAILY_APPLICATIONS}) reached")
                    break
            
            state.processed_jobs = processed_jobs
            state.steps_completed.append("job_processing")
            state.current_step = "job_processing_complete"
            
            self.log_action("JOBS_PROCESSED", f"Processed {len(processed_jobs)} jobs, {successful_applications} applications submitted")
            
            return state
        
        return process_jobs_node
    
    def _create_report_generation_node(self) -> callable:
        """Create a node for generating the final report."""
        async def generate_report_node(state: AgentState) -> AgentState:
            """Generate comprehensive final report."""
            
            if not state.processed_jobs:
                state.error = "No jobs processed, cannot generate report"
                return state
            
            final_report = self._generate_final_report(state.processed_jobs, state.resume_analysis)
            state.final_report = final_report
            state.steps_completed.append("report_generation")
            state.current_step = "completed"
            state.status = "completed"
            state.end_time = datetime.now().isoformat()
            
            return state
        
        return generate_report_node
    
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
            # Step 1: Analyze job skills
            job_description = job.get("description", "")
            job_title = job.get("title", "")
            
            if job_description:
                # Create temporary state for skills analysis
                temp_state = AgentState(
                    session_id="temp",
                    role="temp",
                    resume_path="temp",
                    location="temp",
                    max_jobs=1,
                    auto_apply=False
                )
                
                skills_analysis = await self.skills_analysis_agent.safe_execute(temp_state)
                
                if skills_analysis.status == "error":
                    job_result["skill_analysis"] = {"status": "error", "error": skills_analysis.error}
                else:
                    job_result["skill_analysis"] = skills_analysis.dict()
                    job_result["processing_steps"].append("skills_analysis")
                    
                    # Step 2: Modify resume for this job
                    resume_modification = await self.resume_modification_agent.safe_execute(temp_state)
                    
                    if resume_modification.status == "error":
                        job_result["resume_modification"] = {"status": "error", "error": resume_modification.error}
                    else:
                        job_result["resume_modification"] = resume_modification.dict()
                        job_result["processing_steps"].append("resume_modification")
                        
                        # Step 3: Apply to job (if enabled)
                        if auto_apply:
                            application_result = await self.application_agent.safe_execute(temp_state)
                            
                            if application_result.status == "error":
                                job_result["application_status"] = {"status": "error", "error": application_result.error}
                            else:
                                job_result["application_status"] = application_result.dict()
                                job_result["processing_steps"].append("application")
                        else:
                            job_result["application_status"] = {
                                "status": "skipped",
                                "message": "Auto-apply disabled"
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
            if isinstance(skills, list):
                all_required_skills.extend([skill.get("skill", "") for skill in skills])
        
        # Count skill frequencies
        from collections import Counter
        skill_frequencies = Counter(all_required_skills)
        top_skills = skill_frequencies.most_common(10)
        
        # Current skills from resume
        current_skills = []
        if resume_analysis and isinstance(resume_analysis, dict):
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
    
    async def _save_workflow_state(self, state: AgentState):
        """Save workflow state to file for tracking and recovery."""
        
        try:
            # Create logs directory if it doesn't exist
            os.makedirs(Config.APPLICATION_LOG_DIR, exist_ok=True)
            
            # Save workflow state
            state_file = os.path.join(Config.APPLICATION_LOG_DIR, f"workflow_{state.session_id}.json")
            
            with open(state_file, 'w') as f:
                json.dump(state.dict(), f, indent=2, default=str)
            
            self.log_action("STATE_SAVED", f"Workflow state saved to {state_file}")
            
        except Exception as e:
            self.log_action("WARNING", f"Failed to save workflow state: {str(e)}")
    
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
    
    def get_workflow_graph(self):
        """Get the LangGraph workflow for inspection or modification."""
        return self.workflow
