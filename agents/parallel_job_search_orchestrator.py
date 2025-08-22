import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from agents.base_agent import BaseAgent, AgentState
from job_config import JobConfig
import logging

class ParallelJobSearchOrchestrator(BaseAgent):
    """Orchestrates parallel job search across multiple sources with advanced error handling."""
    
    def __init__(self):
        super().__init__("ParallelJobSearchOrchestrator")
        self.session = None
        self.search_timeout = JobConfig.SEARCH_TIMEOUT_PER_SOURCE
        self.max_concurrent = JobConfig.MAX_CONCURRENT_SEARCHES
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute parallel job search across all enabled sources."""
        
        # Validate required inputs
        required_fields = ["role"]
        if not self.validate_input(state, required_fields):
            state.status = "error"
            state.error = "Missing required fields: role"
            return state
        
        role = state.role
        location = state.location
        max_jobs = state.max_jobs
        
        self.log_action("START", f"Parallel job search for {role} in {location}")
        
        # Initialize session
        await self._init_session()
        
        try:
            # Get enabled sources from configuration
            enabled_sources = JobConfig.get_enabled_sources()
            self.log_action("INFO", f"Searching {len(enabled_sources)} sources: {', '.join(enabled_sources)}")
            
            # Create search tasks with priorities
            search_tasks = self._create_prioritized_tasks(enabled_sources, role, location, max_jobs)
            
            # Execute searches with concurrency control
            all_jobs, search_results = await self._execute_parallel_searches(search_tasks)
            
            # Remove duplicates and rank results
            unique_jobs = self._remove_duplicates_and_rank(all_jobs)
            
            self.log_action("COMPLETE", f"Found {len(unique_jobs)} unique jobs from {len(search_results)} sources")
            
            # Update state with results
            state.job_search_results = {
                "status": "success",
                "jobs": unique_jobs,
                "total_found": len(unique_jobs),
                "source_results": search_results,
                "search_metadata": {
                    "role": role,
                    "location": location,
                    "max_jobs": max_jobs,
                    "timestamp": datetime.now().isoformat(),
                    "execution_mode": "parallel",
                    "sources_searched": enabled_sources,
                    "total_sources": len(enabled_sources)
                }
            }
            
            state.steps_completed.append("parallel_job_search")
            state.current_step = "job_search_complete"
            
        except Exception as e:
            self.log_action("ERROR", f"Parallel job search failed: {str(e)}")
            state.status = "error"
            state.error = f"Parallel job search error: {str(e)}"
        
        finally:
            # Close session
            await self._close_session()
        
        return state
    
    def _create_prioritized_tasks(self, sources: List[str], role: str, location: str, max_jobs: int) -> List[tuple]:
        """Create prioritized search tasks based on source configuration."""
        tasks = []
        
        for source in sources:
            source_config = JobConfig.get_source_config(source)
            if source_config and source_config["enabled"]:
                priority = source_config.get("priority", 3)
                max_per_source = source_config.get("max_jobs_per_source", max_jobs // len(sources))
                
                task = (priority, source, self._search_source(source, role, location, max_per_source))
                tasks.append(task)
        
        # Sort by priority (lower number = higher priority)
        tasks.sort(key=lambda x: x[0])
        return tasks
    
    async def _execute_parallel_searches(self, search_tasks: List[tuple]) -> tuple[List[Dict], Dict]:
        """Execute searches in parallel with concurrency control."""
        all_jobs = []
        search_results = {}
        
        if not search_tasks:
            return all_jobs, search_results
        
        # Group tasks by priority for staggered execution
        priority_groups = {}
        for priority, source, task in search_tasks:
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append((source, task))
        
        # Execute priority groups sequentially, but sources within each group in parallel
        for priority in sorted(priority_groups.keys()):
            group_tasks = priority_groups[priority]
            sources = [source for source, _ in group_tasks]
            coroutines = [task for _, task in group_tasks]
            
            self.log_action("INFO", f"Executing priority {priority} sources: {', '.join(sources)}")
            
            try:
                # Execute sources in this priority group in parallel
                results = await asyncio.gather(*coroutines, return_exceptions=True)
                
                # Process results for this priority group
                for source, result in zip(sources, results):
                    if isinstance(result, Exception):
                        self.log_action("SOURCE_ERROR", f"{source}: {str(result)}")
                        search_results[source] = {
                            "count": 0,
                            "status": "error",
                            "error": str(result),
                            "priority": priority
                        }
                    else:
                        all_jobs.extend(result)
                        search_results[source] = {
                            "count": len(result),
                            "status": "success",
                            "priority": priority
                        }
                        self.log_action("SOURCE_COMPLETE", f"{source}: {len(result)} jobs found")
                
                # Small delay between priority groups to avoid overwhelming servers
                if len(priority_groups) > 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.log_action("ERROR", f"Priority group {priority} failed: {str(e)}")
                # Mark all sources in this group as failed
                for source, _ in group_tasks:
                    search_results[source] = {
                        "count": 0,
                        "status": "error",
                        "error": f"Group execution failed: {str(e)}",
                        "priority": priority
                    }
        
        return all_jobs, search_results
    
    async def _search_source(self, source_name: str, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search a specific job source with timeout protection."""
        try:
            # Create a task with timeout
            search_task = self._execute_source_search(source_name, role, location, max_jobs)
            
            # Execute with timeout
            jobs = await asyncio.wait_for(search_task, timeout=self.search_timeout)
            return jobs
            
        except asyncio.TimeoutError:
            self.log_action("TIMEOUT", f"{source_name}: Search timed out after {self.search_timeout}s")
            raise Exception(f"Search timeout after {self.search_timeout} seconds")
        except Exception as e:
            self.log_action("ERROR", f"{source_name}: Search failed - {str(e)}")
            raise
    
    async def _execute_source_search(self, source_name: str, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Execute the actual search for a source."""
        # Integrate with the existing search methods from JobSearchAgent
        try:
            # Create a temporary JobSearchAgent to use its search methods
            from agents.job_search_agent import JobSearchAgent
            temp_agent = JobSearchAgent()
            
            # Initialize session for the temporary agent
            await temp_agent._init_session()
            
            try:
                # Use the existing search methods
                jobs = await temp_agent._search_source(source_name, role, location, max_jobs)
                return jobs
            finally:
                # Clean up the temporary agent's session
                await temp_agent._close_session()
                
        except Exception as e:
            self.log_action("ERROR", f"Failed to execute search for {source_name}: {str(e)}")
            return []
    
    def _remove_duplicates_and_rank(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and rank jobs by relevance."""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            identifier = f"{job.get('title', '').lower().strip()}|{job.get('company', '').lower().strip()}"
            
            if identifier not in seen and identifier != "|":
                seen.add(identifier)
                
                # Add relevance score based on source priority and other factors
                job['relevance_score'] = self._calculate_relevance_score(job)
                unique_jobs.append(job)
        
        # Sort by relevance score (higher is better)
        unique_jobs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return unique_jobs
    
    def _calculate_relevance_score(self, job: Dict[str, Any]) -> float:
        """Calculate relevance score for a job posting."""
        score = 0.0
        
        # Base score from source priority
        source = job.get('source', '')
        source_config = JobConfig.get_source_config(source)
        if source_config:
            priority = source_config.get('priority', 3)
            score += (4 - priority) * 10  # Higher priority = higher score
        
        # Bonus for salary information
        if job.get('salary'):
            score += 5
        
        # Bonus for detailed description
        if job.get('description') and len(job.get('description', '')) > 100:
            score += 3
        
        # Bonus for recent postings
        posted_date = job.get('posted_date')
        if posted_date:
            try:
                posted = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                days_old = (datetime.now(posted.tzinfo) - posted).days
                if days_old <= 7:
                    score += 10
                elif days_old <= 30:
                    score += 5
            except:
                pass
        
        return score
    
    async def _init_session(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.search_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': JobConfig.USER_AGENT
                }
            )
    
    async def _close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
