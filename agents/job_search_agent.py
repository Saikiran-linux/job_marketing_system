import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import re
from urllib.parse import urljoin, quote
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, AgentState
from agents.linkedin_agent import LinkedInAgent
from config import Config

class JobSearchAgent(BaseAgent):
    """Agent responsible for finding job postings from various sources."""
    
    def __init__(self):
        super().__init__("JobSearchAgent")
        self.session = None
        self.linkedin_agent = None
        self.job_sources = {
            "indeed": {
                "base_url": "https://www.indeed.com",
                "search_path": "/jobs",
                "enabled": True
            },
            "linkedin": {
                "base_url": "https://www.linkedin.com",
                "search_path": "/jobs/search",
                "enabled": True,
                "use_api": True  # Use LinkedIn API instead of web scraping
            },
            "glassdoor": {
                "base_url": "https://www.glassdoor.com",
                "search_path": "/Job/jobs.htm",
                "enabled": True
            }
        }
    
    async def execute(self, state: AgentState) -> AgentState:
        """Find jobs matching the specified criteria."""
        
        # Validate required inputs
        required_fields = ["role"]
        if not self.validate_input(state, required_fields):
            state.status = "error"
            state.error = "Missing required fields: role"
            return state
        
        role = state.role
        location = state.location
        max_jobs = state.max_jobs
        
        self.log_action("SEARCHING", f"Role: {role}, Location: {location}, Max: {max_jobs}")
        
        # Initialize session and LinkedIn agent
        await self._init_session()
        await self._init_linkedin_agent()
        
        all_jobs = []
        search_results = {}
        
        # Search each enabled source
        for source_name, source_config in self.job_sources.items():
            if not source_config["enabled"]:
                continue
                
            try:
                if source_name == "linkedin" and source_config.get("use_api", False):
                    # Use LinkedIn API for better results
                    jobs = await self._search_linkedin_api(role, location, max_jobs)
                else:
                    # Use web scraping for other sources
                    jobs = await self._search_source(source_name, role, location, max_jobs)
                
                all_jobs.extend(jobs)
                search_results[source_name] = {
                    "count": len(jobs),
                    "status": "success"
                }
                self.log_action("SOURCE_COMPLETE", f"{source_name}: {len(jobs)} jobs found")
                
            except Exception as e:
                self.log_action("SOURCE_ERROR", f"{source_name}: {str(e)}")
                search_results[source_name] = {
                    "count": 0,
                    "status": "error",
                    "error": str(e)
                }
        
        # Close session and LinkedIn agent
        await self._close_session()
        await self._close_linkedin_agent()
        
        # Remove duplicates
        unique_jobs = self._remove_duplicates(all_jobs)
        
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
                "timestamp": datetime.now().isoformat()
            }
        }
        
        state.steps_completed.append("job_search")
        state.current_step = "job_search_complete"
        
        return state
    
    async def _init_session(self):
        """Initialize HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
    
    async def _close_session(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _init_linkedin_agent(self):
        """Initialize LinkedIn agent for API-based job search."""
        if not self.linkedin_agent:
            self.linkedin_agent = LinkedInAgent()
    
    async def _close_linkedin_agent(self):
        """Close LinkedIn agent and clean up resources."""
        if self.linkedin_agent:
            await self.linkedin_agent.close()
            self.linkedin_agent = None
    
    async def _search_source(self, source_name: str, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search a specific job source."""
        
        if source_name == "indeed":
            return await self._search_indeed(role, location, max_jobs)
        elif source_name == "linkedin":
            return await self._search_linkedin(role, location, max_jobs)
        elif source_name == "glassdoor":
            return await self._search_glassdoor(role, location, max_jobs)
        else:
            self.log_action("ERROR", f"Unknown job source: {source_name}")
            return []
    
    async def _search_indeed(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search Indeed for jobs."""
        jobs = []
        
        try:
            # Build search URL
            base_url = "https://www.indeed.com/jobs"
            params = {
                'q': role,
                'l': location,
                'limit': min(max_jobs, 50)
            }
            
            # Build URL manually to handle encoding
            url = f"{base_url}?q={quote(role)}&l={quote(location)}&limit={params['limit']}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse job listings
                    job_cards = soup.find_all('div', {'class': 'job_seen_beacon'}) or \
                               soup.find_all('div', {'data-jk': True}) or \
                               soup.find_all('a', {'data-jk': True})
                    
                    for card in job_cards[:max_jobs]:
                        job = self._parse_indeed_job(card, soup)
                        if job:
                            jobs.append(job)
                
        except Exception as e:
            self.log_action("ERROR", f"Indeed search failed: {str(e)}")
        
        return jobs
    
    def _parse_indeed_job(self, card, soup) -> Dict[str, Any]:
        """Parse individual Indeed job posting."""
        try:
            # Extract job title
            title_elem = card.find('h2') or card.find('a', {'data-jk': True})
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract company
            company_elem = card.find('span', {'class': 'companyName'}) or \
                          card.find('a', {'data-testid': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = card.find('div', {'data-testid': 'job-location'}) or \
                           card.find('span', {'class': 'locationsContainer'})
            location = location_elem.get_text(strip=True) if location_elem else "Unknown Location"
            
            # Extract job URL
            link_elem = card.find('a', {'data-jk': True}) or title_elem
            job_id = link_elem.get('data-jk') if link_elem else None
            job_url = f"https://www.indeed.com/job/{job_id}" if job_id else ""
            
            # Extract salary if available
            salary_elem = card.find('span', {'class': 'salary-snippet'})
            salary = salary_elem.get_text(strip=True) if salary_elem else None
            
            # Extract job summary/description
            summary_elem = card.find('div', {'class': 'summary'}) or \
                          card.find('div', {'data-testid': 'job-snippet'})
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "salary": salary,
                "description": summary,
                "source": "indeed",
                "posted_date": datetime.now().isoformat(),
                "job_id": job_id
            }
            
        except Exception as e:
            self.log_action("PARSE_ERROR", f"Failed to parse Indeed job: {str(e)}")
            return None
    
    async def _search_linkedin(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search LinkedIn for jobs (simplified version)."""
        jobs = []
        
        try:
            # Note: LinkedIn requires authentication for full access
            # This is a simplified version that would need enhancement for production use
            
            self.log_action("INFO", "LinkedIn search would require authentication")
            
            # In a real implementation, you would:
            # 1. Use Selenium with login credentials
            # 2. Handle LinkedIn's anti-bot measures
            # 3. Parse job listings from the HTML
            
        except Exception as e:
            self.log_action("ERROR", f"LinkedIn search failed: {str(e)}")
        
        return jobs
    
    async def _search_linkedin_api(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search LinkedIn using the API for better results."""
        
        try:
            search_input = {
                "operation": "search",
                "keywords": role,
                "location": location,
                "max_results": max_jobs
            }
            
            result = await self.linkedin_agent.execute(search_input)
            
            if result.get("status") == "success":
                return result.get("jobs", [])
            else:
                self.log_action("LINKEDIN_API_ERROR", result.get("message", "Unknown error"))
                # Fallback to web scraping if API fails
                return await self._search_linkedin_web(role, location, max_jobs)
                
        except Exception as e:
            self.log_action("LINKEDIN_API_ERROR", f"LinkedIn API search failed: {str(e)}")
            # Fallback to web scraping
            return await self._search_linkedin_web(role, location, max_jobs)
    
    async def _search_linkedin_web(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Fallback LinkedIn search using web scraping."""
        jobs = []
        
        try:
            # Note: LinkedIn requires authentication for full access
            # This is a simplified version that would need enhancement for production use
            
            self.log_action("INFO", "LinkedIn web scraping fallback - limited results")
            
            # In a real implementation, you would:
            # 1. Use Selenium with login credentials
            # 2. Handle LinkedIn's anti-bot measures
            # 3. Parse job listings from the HTML
            
        except Exception as e:
            self.log_action("ERROR", f"LinkedIn web search failed: {str(e)}")
        
        return jobs
    
    async def _search_glassdoor(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search Glassdoor for jobs (simplified version)."""
        jobs = []
        
        try:
            # Similar to LinkedIn, Glassdoor often requires authentication
            # This is a placeholder for the actual implementation
            
            self.log_action("INFO", "Glassdoor search would require enhanced implementation")
            
        except Exception as e:
            self.log_action("ERROR", f"Glassdoor search failed: {str(e)}")
        
        return jobs
    
    def _remove_duplicates(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    async def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Fetch detailed job description from job URL."""
        
        if not self.session:
            await self._init_session()
        
        try:
            async with self.session.get(job_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract full job description
                    # This would need to be customized for each job source
                    description_elem = soup.find('div', {'class': 'jobsearch-jobDescriptionText'}) or \
                                     soup.find('div', {'id': 'jobDescriptionText'})
                    
                    description = description_elem.get_text(strip=True) if description_elem else ""
                    
                    return {
                        "status": "success",
                        "full_description": description,
                        "url": job_url
                    }
                    
        except Exception as e:
            self.log_action("ERROR", f"Failed to fetch job details: {str(e)}")
        
        return {
            "status": "error",
            "message": "Failed to fetch job details"
        }
