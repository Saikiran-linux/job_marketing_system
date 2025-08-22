"""
Scraper Agent - Job search and data extraction with parallel processing subgraph.
"""

import asyncio
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentState
from agents.job_search_agent import JobSearchAgent
from agents.glassdoor_web_agent import GlassdoorWebAgent
from agents.linkedin_web_agent import LinkedInWebAgent
from agents.parallel_job_search_orchestrator import ParallelJobSearchOrchestrator
from config import Config
from utils.logger import setup_logger
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

class ScraperAgent(BaseAgent):
    """Scraper agent that handles job search and data extraction with parallel processing."""
    
    def __init__(self):
        super().__init__("ScraperAgent")
        self.logger = setup_logger("ScraperAgent")
        
        # Initialize sub-agents for different job sources
        self.job_search_agent = JobSearchAgent()
        self.glassdoor_agent = GlassdoorWebAgent()
        self.linkedin_agent = LinkedInWebAgent()
        self.parallel_orchestrator = ParallelJobSearchOrchestrator()
        
        # Build the subgraph for parallel job search
        self.subgraph = self._build_subgraph()
        
    def _build_subgraph(self) -> StateGraph:
        """Build the subgraph for parallel job search and JD extraction."""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes for different job sources
        workflow.add_node("general_search", self._execute_general_search)
        workflow.add_node("glassdoor_search", self._execute_glassdoor_search)
        workflow.add_node("linkedin_search", self._execute_linkedin_search)
        workflow.add_node("extract_jd_details", self._extract_job_details)
        workflow.add_node("merge_results", self._merge_search_results)
        
        # Define the workflow
        workflow.set_entry_point("general_search")
        workflow.add_edge("general_search", "glassdoor_search")
        workflow.add_edge("glassdoor_search", "linkedin_search")
        workflow.add_edge("linkedin_search", "extract_jd_details")
        workflow.add_edge("extract_jd_details", "merge_results")
        workflow.add_edge("merge_results", END)
        
        return workflow.compile()
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the scraper agent workflow."""
        
        try:
            self.log_action("STARTING", "Starting job search and data extraction workflow")
            
            # Execute the subgraph for parallel job search
            result_state = await self.subgraph.ainvoke(state)
            
            if result_state.error:
                self.log_action("ERROR", f"Subgraph execution failed: {result_state.error}")
                state.error = result_state.error
                return state
            
            # Update the main state with results
            if hasattr(result_state, 'all_jobs'):
                state.all_jobs = result_state.all_jobs
            if hasattr(result_state, 'extracted_jds'):
                state.extracted_jds = result_state.extracted_jds
            if hasattr(result_state, 'job_links'):
                state.job_links = result_state.job_links
            
            self.log_action("SUCCESS", f"Job search completed - found {len(getattr(state, 'all_jobs', []))} jobs")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Scraper agent failed: {str(e)}")
            state.error = f"Scraper error: {str(e)}"
            return state
    
    async def _execute_general_search(self, state: AgentState) -> AgentState:
        """Execute general job search."""
        
        try:
            self.log_action("INFO", "Executing general job search")
            result = await self.job_search_agent.execute(state)
            
            if hasattr(result, 'all_jobs'):
                state.all_jobs = result.all_jobs
            elif hasattr(result, 'job_search_results'):
                state.all_jobs = result.job_search_results
            
            self.log_action("SUCCESS", f"General search found {len(getattr(state, 'all_jobs', []))} jobs")
            return state
            
        except Exception as e:
            self.log_action("WARNING", f"General search failed: {str(e)}")
            state.all_jobs = getattr(state, 'all_jobs', [])
            return state
    
    async def _execute_glassdoor_search(self, state: AgentState) -> AgentState:
        """Execute Glassdoor job search."""
        
        try:
            if not self._has_glassdoor_credentials():
                self.log_action("INFO", "Skipping Glassdoor search - no credentials")
                return state
            
            self.log_action("INFO", "Executing Glassdoor job search")
            result = await self.glassdoor_agent.execute(state)
            
            if hasattr(result, 'glassdoor_jobs'):
                glassdoor_jobs = result.glassdoor_jobs
            elif hasattr(result, 'filtered_glassdoor_jobs'):
                glassdoor_jobs = result.filtered_glassdoor_jobs
            else:
                glassdoor_jobs = []
            
            # Merge with existing jobs
            existing_jobs = getattr(state, 'all_jobs', [])
            state.all_jobs = existing_jobs + glassdoor_jobs
            
            self.log_action("SUCCESS", f"Glassdoor search added {len(glassdoor_jobs)} jobs")
            return state
            
        except Exception as e:
            self.log_action("WARNING", f"Glassdoor search failed: {str(e)}")
            return state
    
    async def _execute_linkedin_search(self, state: AgentState) -> AgentState:
        """Execute LinkedIn job search."""
        
        try:
            if not self._has_linkedin_credentials():
                self.log_action("INFO", "Skipping LinkedIn search - no credentials")
                return state
            
            self.log_action("INFO", "Executing LinkedIn job search")
            result = await self.linkedin_agent.execute(state)
            
            if hasattr(result, 'linkedin_jobs'):
                linkedin_jobs = result.linkedin_jobs
            elif hasattr(result, 'filtered_linkedin_jobs'):
                linkedin_jobs = result.filtered_linkedin_jobs
            else:
                linkedin_jobs = []
            
            # Merge with existing jobs
            existing_jobs = getattr(state, 'all_jobs', [])
            state.all_jobs = existing_jobs + linkedin_jobs
            
            self.log_action("SUCCESS", f"LinkedIn search added {len(linkedin_jobs)} jobs")
            return state
            
        except Exception as e:
            self.log_action("WARNING", f"LinkedIn search failed: {str(e)}")
            return state
    
    async def _extract_job_details(self, state: AgentState) -> AgentState:
        """Extract detailed job descriptions and important details."""
        
        try:
            self.log_action("INFO", "Extracting job details and descriptions")
            
            all_jobs = getattr(state, 'all_jobs', [])
            extracted_jds = []
            job_links = []
            
            for job in all_jobs:
                # Extract JD if available
                if 'description' in job:
                    extracted_jds.append({
                        'job_id': job.get('id'),
                        'title': job.get('title'),
                        'company': job.get('company'),
                        'description': job['description'],
                        'requirements': self._extract_requirements(job.get('description', '')),
                        'location': job.get('location'),
                        'salary': job.get('salary'),
                        'posted_date': job.get('posted_date')
                    })
                
                # Extract job links
                if 'url' in job:
                    job_links.append({
                        'job_id': job.get('id'),
                        'title': job.get('title'),
                        'company': job.get('company'),
                        'url': job['url'],
                        'source': job.get('source', 'unknown')
                    })
            
            state.extracted_jds = extracted_jds
            state.job_links = job_links
            
            self.log_action("SUCCESS", f"Extracted details for {len(extracted_jds)} jobs")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Job detail extraction failed: {str(e)}")
            state.extracted_jds = []
            state.job_links = []
            return state
    
    async def _merge_search_results(self, state: AgentState) -> AgentState:
        """Merge and deduplicate search results."""
        
        try:
            self.log_action("INFO", "Merging and deduplicating search results")
            
            all_jobs = getattr(state, 'all_jobs', [])
            unique_jobs = self._remove_duplicate_jobs(all_jobs)
            
            state.all_jobs = unique_jobs
            
            self.log_action("SUCCESS", f"Final result: {len(unique_jobs)} unique jobs")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Result merging failed: {str(e)}")
            return state
    
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract key requirements from job description."""
        
        requirements = []
        lines = description.split('\n')
        
        for line in lines:
            line = line.strip().lower()
            if any(keyword in line for keyword in ['requirements:', 'qualifications:', 'skills:', 'experience:']):
                # Extract the requirements section
                req_text = line.split(':', 1)[1] if ':' in line else line
                requirements.append(req_text)
        
        return requirements
    
    def _remove_duplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate job postings based on title and company."""
        
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            identifier = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
            
            if identifier not in seen and identifier != "|":
                seen.add(identifier)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _has_glassdoor_credentials(self) -> bool:
        """Check if Glassdoor credentials are available."""
        return bool(
            hasattr(Config, 'GLASSDOOR_EMAIL') and 
            hasattr(Config, 'GLASSDOOR_PASSWORD') and
            Config.GLASSDOOR_EMAIL and 
            Config.GLASSDOOR_PASSWORD
        )
    
    def _has_linkedin_credentials(self) -> bool:
        """Check if LinkedIn credentials are available."""
        return bool(
            hasattr(Config, 'LINKEDIN_EMAIL') and 
            hasattr(Config, 'LINKEDIN_PASSWORD') and
            Config.LINKEDIN_EMAIL and 
            Config.LINKEDIN_PASSWORD
        )
    
    async def close(self):
        """Clean up resources."""
        
        if hasattr(self.job_search_agent, 'close'):
            await self.job_search_agent.close()
        if hasattr(self.glassdoor_agent, 'close'):
            await self.glassdoor_agent.close()
        if hasattr(self.linkedin_agent, 'close'):
            await self.linkedin_agent.close()
        
        self.log_action("INFO", "Scraper agent resources cleaned up")
