"""
Smart Orchestrator Agent - Uses web-based agents with email/password authentication.
"""

import asyncio
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentState
from agents.glassdoor_web_agent import GlassdoorWebAgent
from agents.linkedin_web_agent import LinkedInWebAgent
from agents.job_search_agent import JobSearchAgent
from agents.resume_analysis_agent import ResumeAnalysisAgent
from agents.resume_modification_agent import ResumeModificationAgent
from agents.application_agent import ApplicationAgent
from agents.skills_analysis_agent import SkillsAnalysisAgent
from config import Config
from utils.logger import setup_logger

class SmartOrchestratorAgent(BaseAgent):
    """Smart orchestrator that uses web-based agents for job search and application."""
    
    def __init__(self):
        super().__init__("SmartOrchestratorAgent")
        self.logger = setup_logger("SmartOrchestratorAgent")
        
        # Initialize all available agents
        self.agents = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize available agents based on configuration."""
        
        # Core agents (always available)
        self.agents['resume_analysis'] = ResumeAnalysisAgent()
        self.agents['resume_modification'] = ResumeModificationAgent()
        self.agents['skills_analysis'] = SkillsAnalysisAgent()
        self.agents['application'] = ApplicationAgent()
        self.agents['job_search'] = JobSearchAgent()
        
        # LinkedIn web agent - check if credentials are available
        if self._has_linkedin_web_credentials():
            self.logger.info("Using LinkedIn Web agent (email/password)")
            self.agents['linkedin'] = LinkedInWebAgent()
        else:
            self.logger.warning("No LinkedIn credentials available - LinkedIn integration disabled")
        
        # Glassdoor web agent - check if credentials are available
        if self._has_glassdoor_web_credentials():
            self.logger.info("Using Glassdoor Web agent (email/password)")
            self.agents['glassdoor'] = GlassdoorWebAgent()
        else:
            self.logger.warning("No Glassdoor credentials available - Glassdoor integration disabled")
    
    def _has_linkedin_web_credentials(self) -> bool:
        """Check if LinkedIn web credentials are available."""
        return bool(
            Config.LINKEDIN_EMAIL and 
            Config.LINKEDIN_PASSWORD
        )
    
    def _has_glassdoor_web_credentials(self) -> bool:
        """Check if Glassdoor web credentials are available."""
        return bool(
            Config.GLASSDOOR_EMAIL and 
            Config.GLASSDOOR_PASSWORD
        )
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the complete job application workflow using web-based agents."""
        
        try:
            self.log_action("STARTING", "Starting web-based job application workflow")
            
            # Step 1: Resume Analysis
            if 'resume_analysis' in self.agents:
                state = await self.agents['resume_analysis'].execute(state)
                if state.error:
                    return state
                self.log_action("SUCCESS", "Resume analysis completed")
            
            # Step 2: Skills Analysis
            if 'skills_analysis' in self.agents:
                state = await self.agents['skills_analysis'].execute(state)
                if state.error:
                    return state
                self.log_action("SUCCESS", "Skills analysis completed")
            
            # Step 3: Job Search (using available sources)
            job_search_results = await self._execute_job_search(state)
            if job_search_results:
                state.all_jobs = job_search_results
                self.log_action("SUCCESS", f"Job search completed - found {len(job_search_results)} total jobs")
            else:
                state.error = "No jobs found from any source"
                return state
            
            # Step 4: Resume Modification (if needed)
            if 'resume_modification' in self.agents and state.all_jobs:
                state = await self.agents['resume_modification'].execute(state)
                if state.error:
                    return state
                self.log_action("SUCCESS", "Resume modification completed")
            
            # Step 5: Job Applications (if auto-apply is enabled)
            if state.auto_apply and state.all_jobs:
                application_results = await self._execute_job_applications(state)
                state.all_applications = application_results
                self.log_action("SUCCESS", f"Job applications completed - {len(application_results)} applications submitted")
            
            self.log_action("COMPLETE", "Web-based workflow completed successfully")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Web-based workflow failed: {str(e)}")
            state.error = f"Orchestrator error: {str(e)}"
            return state
    
    async def _execute_job_search(self, state: AgentState) -> List[Dict[str, Any]]:
        """Execute job search using all available sources."""
        
        all_jobs = []
        
        # Use general job search agent
        if 'job_search' in self.agents:
            try:
                search_state = await self.agents['job_search'].execute(state)
                if hasattr(search_state, 'all_jobs') and search_state.all_jobs:
                    all_jobs.extend(search_state.all_jobs)
            except Exception as e:
                self.log_action("WARNING", f"General job search failed: {str(e)}")
        
        # Use LinkedIn web agent if available
        if 'linkedin' in self.agents:
            try:
                linkedin_state = await self.agents['linkedin'].execute(state)
                if hasattr(linkedin_state, 'linkedin_jobs') and linkedin_state.linkedin_jobs:
                    all_jobs.extend(linkedin_state.linkedin_jobs)
                elif hasattr(linkedin_state, 'filtered_linkedin_jobs') and linkedin_state.filtered_linkedin_jobs:
                    all_jobs.extend(linkedin_state.filtered_linkedin_jobs)
            except Exception as e:
                self.log_action("WARNING", f"LinkedIn job search failed: {str(e)}")
        
        # Use Glassdoor web agent if available
        if 'glassdoor' in self.agents:
            try:
                glassdoor_state = await self.agents['glassdoor'].execute(state)
                if hasattr(glassdoor_state, 'glassdoor_jobs') and glassdoor_state.glassdoor_jobs:
                    all_jobs.extend(glassdoor_state.glassdoor_jobs)
                elif hasattr(glassdoor_state, 'filtered_glassdoor_jobs') and glassdoor_state.filtered_glassdoor_jobs:
                    all_jobs.extend(glassdoor_state.filtered_glassdoor_jobs)
            except Exception as e:
                self.log_action("WARNING", f"Glassdoor job search failed: {str(e)}")
        
        # Remove duplicates and return
        unique_jobs = self._remove_duplicate_jobs(all_jobs)
        return unique_jobs
    
    async def _execute_job_applications(self, state: AgentState) -> List[Dict[str, Any]]:
        """Execute job applications using the application agent."""
        
        if 'application' not in self.agents:
            return []
        
        try:
            # Prepare jobs for application (limit to avoid overwhelming)
            max_applications = getattr(state, 'max_daily_applications', 10)
            jobs_to_apply = state.all_jobs[:max_applications]
            
            application_results = []
            for job in jobs_to_apply:
                try:
                    # Create a temporary state for this job
                    job_state = AgentState()
                    job_state.job_info = job
                    job_state.resume_path = getattr(state, 'resume_path', None)
                    job_state.resume_analysis = getattr(state, 'resume_analysis', None)
                    
                    # Apply to the job
                    result = await self.agents['application'].apply_to_job(job_state)
                    application_results.append(result)
                    
                    # Add delay between applications
                    await asyncio.sleep(getattr(state, 'application_delay', 5))
                    
                except Exception as e:
                    self.log_action("ERROR", f"Failed to apply to job {job.get('title', 'Unknown')}: {str(e)}")
                    application_results.append({
                        "job_id": job.get('id'),
                        "status": "error",
                        "error": str(e)
                    })
            
            return application_results
            
        except Exception as e:
            self.log_action("ERROR", f"Job applications failed: {str(e)}")
            return []
    
    def _remove_duplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate job postings based on title and company."""
        
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            identifier = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
            
            if identifier not in seen and identifier != "|":
                seen.add(identifier)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def get_available_sources(self) -> Dict[str, str]:
        """Get information about available job sources."""
        
        sources = {}
        
        if 'linkedin' in self.agents:
            sources['linkedin'] = "Web-based (email/password)"
        
        if 'glassdoor' in self.agents:
            sources['glassdoor'] = "Web-based (email/password)"
        
        if 'job_search' in self.agents:
            sources['general'] = "General web search"
        
        return sources
    
    def get_credential_status(self) -> Dict[str, Dict[str, bool]]:
        """Get status of available credentials."""
        
        return {
            "linkedin": {
                "web_credentials": self._has_linkedin_web_credentials()
            },
            "glassdoor": {
                "web_credentials": self._has_glassdoor_web_credentials()
            }
        }
    
    async def close(self):
        """Clean up resources."""
        
        for agent in self.agents.values():
            if hasattr(agent, 'close'):
                await agent.close()
