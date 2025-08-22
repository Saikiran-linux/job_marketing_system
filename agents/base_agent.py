from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Annotated
import asyncio
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from utils.logger import setup_logger

class AgentState(BaseModel):
    """State object that flows through the LangGraph workflow."""
    session_id: str = Field(description="Unique session identifier")
    start_time: str = Field(description="Workflow start timestamp")
    current_step: str = Field(description="Current step being executed")
    steps_completed: list = Field(default_factory=list, description="List of completed steps")
    status: str = Field(default="running", description="Current workflow status")
    error: Optional[str] = Field(default=None, description="Error message if any")
    
    # Input parameters
    role: str = Field(description="Job role to search for")
    resume_path: str = Field(description="Path to the resume file")
    location: str = Field(description="Job search location")
    max_jobs: int = Field(description="Maximum number of jobs to process")
    auto_apply: bool = Field(description="Whether to automatically apply to jobs")
    
    # Results from each step
    resume_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Resume analysis results")
    job_search_results: Optional[Dict[str, Any]] = Field(default=None, description="Job search results")
    glassdoor_jobs: list = Field(default_factory=list, description="Jobs found on Glassdoor")
    filtered_glassdoor_jobs: list = Field(default_factory=list, description="Filtered Glassdoor jobs")
    glassdoor_applications: list = Field(default_factory=list, description="Glassdoor application results")
    processed_jobs: list = Field(default_factory=list, description="List of processed jobs")
    final_report: Optional[Dict[str, Any]] = Field(default=None, description="Final workflow report")
    
    # Additional fields for orchestrator workflow
    all_jobs: list = Field(default_factory=list, description="All jobs found across sources")
    extracted_jds: list = Field(default_factory=list, description="Extracted job descriptions")
    job_links: list = Field(default_factory=list, description="Job application links")
    tracking_results: Optional[Dict[str, Any]] = Field(default=None, description="Application tracking results")
    monitoring_results: Optional[Dict[str, Any]] = Field(default=None, description="Monitoring results")
    tracking_report: Optional[Dict[str, Any]] = Field(default=None, description="Tracking report")
    updated_statuses: Optional[Dict[str, Any]] = Field(default=None, description="Updated application statuses")
    monitoring_schedule: Optional[Dict[str, Any]] = Field(default=None, description="Monitoring schedule")
    
    # LinkedIn-specific fields
    linkedin_jobs: list = Field(default_factory=list, description="Jobs found on LinkedIn")
    filtered_linkedin_jobs: list = Field(default_factory=list, description="Filtered LinkedIn jobs")
    linkedin_applications: list = Field(default_factory=list, description="LinkedIn application results")
    
    # Metadata
    end_time: Optional[str] = Field(default=None, description="Workflow end timestamp")
    workflow_duration: Optional[str] = Field(default=None, description="Total workflow duration")
    
    # Error tracking
    errors: list = Field(default_factory=list, description="List of errors encountered during workflow")

class BaseAgent(ABC):
    """Base class for all agents in the job application system using LangGraph."""
    
    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.max_retries = max_retries
        self.logger = setup_logger(name)
        self.execution_count = 0
        self.last_execution = None
        
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the agent's main functionality and return updated state."""
        pass
    
    async def safe_execute(self, state: AgentState) -> AgentState:
        """Execute with error handling and retries."""
        self.execution_count += 1
        self.last_execution = datetime.now()
        
        for attempt in range(self.max_retries):
            try:
                self.log_action("STARTING", f"Attempt {attempt + 1}/{self.max_retries}")
                result = await self.execute(state)
                self.log_action("SUCCESS", f"Execution completed successfully")
                return result
                
            except Exception as e:
                self.log_action("ERROR", f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.max_retries - 1:
                    self.log_action("FAILED", f"All {self.max_retries} attempts failed")
                    state.status = "error"
                    state.error = f"{self.name} failed: {str(e)}"
                    return state
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        return state
    
    def log_action(self, action: str, details: str):
        """Log agent actions with consistent formatting."""
        self.logger.info(f"{self.name} [{action}]: {details}")
    
    def validate_input(self, state: AgentState, required_fields: list) -> bool:
        """Validate that required input fields are present in state."""
        missing_fields = []
        for field in required_fields:
            if not hasattr(state, field) or getattr(state, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            self.log_action("VALIDATION_ERROR", f"Missing required fields: {missing_fields}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None
        }
    
    def create_node(self) -> callable:
        """Create a LangGraph node function for this agent."""
        async def agent_node(state: AgentState) -> AgentState:
            """Node function that executes this agent."""
            try:
                return await self.safe_execute(state)
            except Exception as e:
                state.status = "error"
                state.error = f"{self.name} failed: {str(e)}"
                return state
        
        return agent_node
