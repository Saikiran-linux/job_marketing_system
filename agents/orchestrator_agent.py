"""
LangGraph-based Orchestrator Agent - Main coordinator for the simplified 6-agent architecture.
Uses LangGraph for workflow management with error handling, state validation, and parallel execution.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent, AgentState
from agents.scraper_agent import ScraperAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.resume_agent import ResumeAgent
from agents.application_agent import ApplicationAgent
from agents.tracker_agent import TrackerAgent
from config import Config
from utils.logger import setup_logger

class OrchestratorAgent(BaseAgent):
    """LangGraph-based orchestrator that coordinates the 6-agent job application workflow."""
    
    def __init__(self):
        super().__init__("OrchestratorAgent")
        self.logger = setup_logger("OrchestratorAgent")
        
        # Initialize the 6 core agents
        self.agents = {}
        self._initialize_agents()
        
        # Create the LangGraph workflow
        self.workflow = self._create_workflow()
        
    def _initialize_agents(self):
        """Initialize the 6 core agents."""
        
        self.agents['scraper'] = ScraperAgent()
        self.agents['analyzer'] = AnalyzerAgent()
        self.agents['resume'] = ResumeAgent()
        self.agents['application'] = ApplicationAgent()
        self.agents['tracker'] = TrackerAgent()
        
        self.logger.info("Initialized 6 core agents: scraper, analyzer, resume, application, tracker")
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with nodes, edges, and conditional routing."""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add agent execution nodes
        workflow.add_node("scraper_node", self.agents['scraper'].create_node())
        workflow.add_node("analyzer_node", self.agents['analyzer'].create_node())
        workflow.add_node("resume_node", self.agents['resume'].create_node())
        workflow.add_node("application_node", self.agents['application'].create_node())
        workflow.add_node("tracker_node", self.agents['tracker'].create_node())
        
        # Add validation and error handling nodes
        workflow.add_node("validate_scraper_output", self._create_validation_node("scraper"))
        workflow.add_node("validate_analyzer_output", self._create_validation_node("analyzer"))
        workflow.add_node("validate_resume_output", self._create_validation_node("resume"))
        workflow.add_node("validate_application_output", self._create_validation_node("application"))
        workflow.add_node("validate_tracker_output", self._create_validation_node("tracker"))
        
        # Add error handling nodes
        workflow.add_node("handle_scraper_error", self._create_error_handler_node("scraper"))
        workflow.add_node("handle_analyzer_error", self._create_error_handler_node("analyzer"))
        workflow.add_node("handle_resume_error", self._create_error_handler_node("resume"))
        workflow.add_node("handle_application_error", self._create_error_handler_node("application"))
        workflow.add_node("handle_tracker_error", self._create_error_handler_node("tracker"))
        
        # Add parallel execution node for resume and application
        workflow.add_node("parallel_resume_application", self._create_parallel_node())
        
        # Add conditional routing nodes
        workflow.add_node("should_auto_apply", self._create_conditional_node("auto_apply"))
        workflow.add_node("should_continue_after_error", self._create_conditional_node("continue_after_error"))
        
        # Set entry point
        workflow.set_entry_point("scraper_node")
        
        # Add edges with conditional routing
        # Scraper -> Validation -> Analyzer or Error Handler
        workflow.add_edge("scraper_node", "validate_scraper_output")
        workflow.add_conditional_edges(
            "validate_scraper_output",
            self._route_validation_result,
            {
                "success": "analyzer_node",
                "error": "handle_scraper_error"
            }
        )
        
        # Analyzer -> Validation -> Resume or Error Handler
        workflow.add_edge("analyzer_node", "validate_analyzer_output")
        workflow.add_conditional_edges(
            "validate_analyzer_output",
            self._route_validation_result,
            {
                "success": "resume_node",
                "error": "handle_analyzer_error"
            }
        )
        
        # Resume -> Validation -> Parallel Execution or Error Handler
        workflow.add_edge("resume_node", "validate_resume_output")
        workflow.add_conditional_edges(
            "validate_resume_output",
            self._route_validation_result,
            {
                "success": "should_auto_apply",
                "error": "handle_resume_error"
            }
        )
        
        # Conditional routing for auto-apply
        workflow.add_conditional_edges(
            "should_auto_apply",
            self._route_auto_apply,
            {
                "apply": "parallel_resume_application",
                "skip": "tracker_node"
            }
        )
        
        # Parallel execution -> Validation -> Tracker or Error Handler
        workflow.add_edge("parallel_resume_application", "validate_application_output")
        workflow.add_conditional_edges(
            "validate_application_output",
            self._route_validation_result,
            {
                "success": "tracker_node",
                "error": "handle_application_error"
            }
        )
        
        # Tracker -> Validation -> End or Error Handler
        workflow.add_edge("tracker_node", "validate_tracker_output")
        workflow.add_conditional_edges(
            "validate_tracker_output",
            self._route_validation_result,
            {
                "success": END,
                "error": "handle_tracker_error"
            }
        )
        
        # Error handler routing
        workflow.add_conditional_edges(
            "handle_scraper_error",
            self._route_error_recovery,
            {
                "retry": "scraper_node",
                "continue": "analyzer_node",
                "fail": END
            }
        )
        
        workflow.add_conditional_edges(
            "handle_analyzer_error",
            self._route_error_recovery,
            {
                "retry": "analyzer_node",
                "continue": "resume_node",
                "fail": END
            }
        )
        
        workflow.add_conditional_edges(
            "handle_resume_error",
            self._route_error_recovery,
            {
                "retry": "resume_node",
                "continue": "should_auto_apply",
                "fail": END
            }
        )
        
        workflow.add_conditional_edges(
            "handle_application_error",
            self._route_error_recovery,
            {
                "retry": "parallel_resume_application",
                "continue": "tracker_node",
                "fail": END
            }
        )
        
        workflow.add_conditional_edges(
            "handle_tracker_error",
            self._route_error_recovery,
            {
                "retry": "tracker_node",
                "continue": END,
                "fail": END
            }
        )
        
        return workflow
    
    def _create_validation_node(self, agent_name: str):
        """Create a validation node for a specific agent's output."""
        
        async def validation_node(state: AgentState) -> AgentState:
            """Validate the output of a specific agent."""
            try:
                self.log_action("VALIDATION", f"Validating {agent_name} output")
                
                # Update current step
                state.current_step = f"validating_{agent_name}"
                
                # Agent-specific validation logic
                if agent_name == "scraper":
                    if not state.job_search_results or not state.glassdoor_jobs:
                        state.error = f"{agent_name} validation failed: No job data found"
                        return state
                
                elif agent_name == "analyzer":
                    if not state.processed_jobs:
                        state.error = f"{agent_name} validation failed: No processed jobs found"
                        return state
                
                elif agent_name == "resume":
                    if not state.resume_analysis:
                        state.error = f"{agent_name} validation failed: No resume analysis found"
                        return state
                
                elif agent_name == "application":
                    if not state.glassdoor_applications:
                        state.error = f"{agent_name} validation failed: No application results found"
                        return state
                
                elif agent_name == "tracker":
                    if not state.final_report:
                        state.error = f"{agent_name} validation failed: No final report generated"
                        return state
                
                # Mark step as completed
                state.steps_completed.append(f"{agent_name}_validation")
                self.log_action("SUCCESS", f"{agent_name} validation passed")
                
                return state
                
            except Exception as e:
                state.error = f"Validation error for {agent_name}: {str(e)}"
                return state
        
        return validation_node
    
    def _create_error_handler_node(self, agent_name: str):
        """Create an error handling node for a specific agent."""
        
        async def error_handler_node(state: AgentState) -> AgentState:
            """Handle errors from a specific agent."""
            try:
                self.log_action("ERROR_HANDLING", f"Handling error from {agent_name}")
                
                # Update current step
                state.current_step = f"error_handling_{agent_name}"
                
                # Log the error
                error_msg = state.error or f"Unknown error from {agent_name}"
                self.log_action("ERROR", f"{agent_name} error: {error_msg}")
                
                # Add error to state for tracking
                if not hasattr(state, 'errors'):
                    state.errors = []
                state.errors.append({
                    'agent': agent_name,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Mark step as completed
                state.steps_completed.append(f"{agent_name}_error_handled")
                
                return state
                
            except Exception as e:
                state.error = f"Error handler failed for {agent_name}: {str(e)}"
                return state
        
        return error_handler_node
    
    def _create_parallel_node(self):
        """Create a node for parallel execution of resume and application agents."""
        
        async def parallel_node(state: AgentState) -> AgentState:
            """Execute resume and application agents in parallel where possible."""
            try:
                self.log_action("PARALLEL", "Starting parallel execution of resume and application agents")
                
                # Update current step
                state.current_step = "parallel_resume_application"
                
                # Check if we can run in parallel
                if state.auto_apply and state.processed_jobs:
                    # Run both agents concurrently
                    tasks = [
                        self.agents['resume'].safe_execute(state),
                        self.agents['application'].safe_execute(state)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            self.log_action("ERROR", f"Parallel execution failed: {str(result)}")
                            state.error = f"Parallel execution error: {str(result)}"
                            return state
                        elif isinstance(result, AgentState):
                            # Update state with results from the last successful result
                            if not result.error:
                                state = result
                
                else:
                    # Fallback to sequential execution
                    self.log_action("INFO", "Falling back to sequential execution")
                    state = await self.agents['resume'].safe_execute(state)
                    if state.error:
                        return state
                    
                    if state.auto_apply:
                        state = await self.agents['application'].safe_execute(state)
                        if state.error:
                            return state
                
                # Mark step as completed
                state.steps_completed.append("parallel_resume_application")
                self.log_action("SUCCESS", "Parallel execution completed")
                
                return state
                
            except Exception as e:
                state.error = f"Parallel execution failed: {str(e)}"
                return state
        
        return parallel_node
    
    def _create_conditional_node(self, condition_type: str):
        """Create a conditional routing node."""
        
        async def conditional_node(state: AgentState) -> AgentState:
            """Route based on specific conditions."""
            try:
                self.log_action("CONDITIONAL", f"Evaluating condition: {condition_type}")
                
                # Update current step
                state.current_step = f"conditional_{condition_type}"
                
                # Mark step as completed
                state.steps_completed.append(f"conditional_{condition_type}")
                
                return state
                
            except Exception as e:
                state.error = f"Conditional routing failed: {str(e)}"
                return state
        
        return conditional_node
    
    def _route_validation_result(self, state: AgentState) -> str:
        """Route based on validation result."""
        if state.error:
            return "error"
        return "success"
    
    def _route_auto_apply(self, state: AgentState) -> str:
        """Route based on auto-apply setting and job availability."""
        if state.auto_apply and state.processed_jobs:
            return "apply"
        return "skip"
    
    def _route_error_recovery(self, state: AgentState) -> str:
        """Route based on error recovery strategy."""
        # Check if we should retry based on error count
        if hasattr(state, 'errors'):
            recent_errors = [e for e in state.errors if e['agent'] in state.current_step]
            if len(recent_errors) < 2:  # Allow up to 2 retries
                return "retry"
        
        # Check if we can continue without this step
        if state.current_step in ["scraper", "analyzer"]:
            return "continue"  # Critical steps, can't continue
        elif state.current_step in ["resume", "application"]:
            return "continue"  # Can continue without these
        else:
            return "fail"  # Default to fail
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the complete LangGraph-based job application workflow."""
        
        try:
            self.log_action("STARTING", "Starting LangGraph-based job application workflow")
            
            # Set initial state
            state.start_time = datetime.now().isoformat()
            state.current_step = "orchestrator_start"
            state.status = "running"
            
            # Compile and run the workflow
            app = self.workflow.compile()
            
            # Execute the workflow
            final_state = await app.ainvoke(state)
            
            # Update final state
            final_state.end_time = datetime.now().isoformat()
            final_state.status = "completed" if not final_state.error else "error"
            
            # Calculate duration
            start_time = datetime.fromisoformat(state.start_time)
            end_time = datetime.fromisoformat(final_state.end_time)
            duration = end_time - start_time
            final_state.workflow_duration = str(duration)
            
            self.log_action("COMPLETE", f"LangGraph workflow completed in {duration}")
            return final_state
            
        except Exception as e:
            self.log_action("ERROR", f"LangGraph workflow failed: {str(e)}")
            state.error = f"Orchestrator error: {str(e)}"
            state.status = "error"
            state.end_time = datetime.now().isoformat()
            return state
    
    async def close(self):
        """Clean up resources."""
        
        for agent in self.agents.values():
            if hasattr(agent, 'close'):
                await agent.close()
        
        self.log_action("INFO", "All agents closed successfully")
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents."""
        
        return {
            "scraper": "Job search and data extraction",
            "analyzer": "Job description analysis",
            "resume": "Dynamic resume modification",
            "application": "Form filling and submission",
            "tracker": "Application status monitoring"
        }
    
    def get_workflow_graph(self) -> str:
        """Get a visual representation of the workflow graph."""
        return str(self.workflow)
