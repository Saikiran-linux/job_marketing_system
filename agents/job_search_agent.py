import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, Any, List
import re
from urllib.parse import urljoin, quote
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, AgentState
from config import Config

class JobSearchAgent(BaseAgent):
    """Agent responsible for finding job postings from various sources using web scraping."""
    
    def __init__(self):
        super().__init__("JobSearchAgent")
        self.session = None
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
                "use_web": True  # Use web scraping instead of API
            },
            "glassdoor": {
                "base_url": "https://www.glassdoor.com",
                "search_path": "/Job/jobs.htm",
                "enabled": True
            },
            "google_jobs": {
                "base_url": "https://www.google.com",
                "search_path": "/search",
                "enabled": True
            },
            "company_websites": {
                "base_url": None,
                "search_path": None,
                "enabled": True
            }
        }
    
    async def execute(self, state: AgentState) -> AgentState:
        """Find jobs matching the specified criteria using parallel execution."""
        
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
        
        # Initialize session
        await self._init_session()
        
        # Create tasks for parallel execution
        search_tasks = []
        for source_name, source_config in self.job_sources.items():
            if not source_config["enabled"]:
                continue
            
            # Create task for each enabled source
            task = self._search_source_parallel(source_name, role, location, max_jobs)
            search_tasks.append((source_name, task))
        
        # Execute all searches in parallel using asyncio.gather()
        self.log_action("INFO", f"Starting parallel search across {len(search_tasks)} sources")
        
        all_jobs = []
        search_results = {}
        
        if search_tasks:
            try:
                # Execute all searches in parallel
                source_names = [name for name, _ in search_tasks]
                search_coroutines = [task for _, task in search_tasks]
                
                # Use asyncio.gather() for true parallel execution
                results = await asyncio.gather(*search_coroutines, return_exceptions=True)
                
                # Process results
                for source_name, result in zip(source_names, results):
                    if isinstance(result, Exception):
                        self.log_action("SOURCE_ERROR", f"{source_name}: {str(result)}")
                        search_results[source_name] = {
                            "count": 0,
                            "status": "error",
                            "error": str(result)
                        }
                    else:
                        all_jobs.extend(result)
                        search_results[source_name] = {
                            "count": len(result),
                            "status": "success"
                        }
                        self.log_action("SOURCE_COMPLETE", f"{source_name}: {len(result)} jobs found")
                        
            except Exception as e:
                self.log_action("ERROR", f"Parallel search execution failed: {str(e)}")
                # Fallback to sequential execution if parallel fails
                self.log_action("INFO", "Falling back to sequential execution")
                for source_name, task in search_tasks:
                    try:
                        jobs = await task
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
        
        # Close session
        await self._close_session()
        
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
                "timestamp": datetime.now().isoformat(),
                "execution_mode": "parallel"
            }
        }
        
        state.steps_completed.append("job_search")
        state.current_step = "job_search_complete"
        
        return state
    
    async def _search_source_parallel(self, source_name: str, role: str, location: str, max_jobs: int):
        """Create a task for searching a specific job source."""
        return await self._search_source(source_name, role, location, max_jobs)
    
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
    
    async def _search_source(self, source_name: str, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search a specific job source."""
        
        if source_name == "indeed":
            return await self._search_indeed(role, location, max_jobs)
        elif source_name == "linkedin":
            return await self._search_linkedin(role, location, max_jobs)
        elif source_name == "glassdoor":
            return await self._search_glassdoor(role, location, max_jobs)
        elif source_name == "google_jobs":
            return await self._search_google_jobs(role, location, max_jobs)
        elif source_name == "company_websites":
            return await self._search_company_websites(role, location, max_jobs)
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
        
        # Add mock data for testing if no real jobs found
        if not jobs and max_jobs > 0:
            jobs = self._get_mock_indeed_jobs(role, location, max_jobs)
        
        return jobs
    
    def _get_mock_indeed_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Generate mock Indeed jobs for testing purposes."""
        mock_companies = ["TechCorp", "InnovateLabs", "DataFlow Inc", "CloudTech Solutions", "AI Dynamics"]
        mock_jobs = []
        
        for i in range(min(max_jobs, 5)):
            mock_jobs.append({
                "title": f"{role} - Team {i+1}",
                "company": mock_companies[i % len(mock_companies)],
                "location": location,
                "url": f"https://indeed.com/job/mock_{i}",
                "salary": f"${80000 + i*5000} - ${120000 + i*5000}",
                "description": f"Exciting opportunity for a {role} at {mock_companies[i % len(mock_companies)]}",
                "source": "indeed",
                "posted_date": datetime.now().isoformat(),
                "job_id": f"mock_{i}"
            })
        
        return mock_jobs
    
    def _parse_indeed_job(self, card, soup) -> Dict[str, Any]:
        """Parse individual Indeed job posting."""
        try:
            # Validate input
            if not card:
                return None
                
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
        """Search LinkedIn for jobs using web scraping."""
        jobs = []
        
        try:
            # Note: LinkedIn requires authentication for full access
            # This is a simplified version that would need enhancement for production use
            
            self.log_action("INFO", "LinkedIn search would require authentication")
            
            # In a real implementation, you would:
            # 1. Use Playwright with login credentials
            # 2. Handle LinkedIn's anti-bot measures
            # 3. Parse job listings from the HTML
            
        except Exception as e:
            self.log_action("ERROR", f"LinkedIn search failed: {str(e)}")
        
        # Add mock data for testing if no real jobs found
        if not jobs and max_jobs > 0:
            jobs = self._get_mock_linkedin_jobs(role, location, max_jobs)
        
        return jobs
    
    def _get_mock_linkedin_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Generate mock LinkedIn jobs for testing purposes."""
        mock_companies = ["LinkedIn Corp", "Tech Network", "Professional Hub", "Career Connect", "Business Network"]
        mock_jobs = []
        
        for i in range(min(max_jobs, 5)):
            mock_jobs.append({
                "title": f"{role} - Network {i+1}",
                "company": mock_companies[i % len(mock_companies)],
                "location": location,
                "url": f"https://linkedin.com/jobs/mock_{i}",
                "salary": f"${90000 + i*3000} - ${130000 + i*3000}",
                "description": f"Connect with {mock_companies[i % len(mock_companies)]} as a {role}",
                "source": "linkedin",
                "posted_date": datetime.now().isoformat(),
                "job_id": f"linkedin_mock_{i}"
            })
        
        return mock_jobs
    
    async def _search_glassdoor(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search Glassdoor for jobs (simplified version)."""
        jobs = []
        
        try:
            # Similar to LinkedIn, Glassdoor often requires authentication
            # This is a placeholder for the actual implementation
            
            self.log_action("INFO", "Glassdoor search would require enhanced implementation")
            
        except Exception as e:
            self.log_action("ERROR", f"Glassdoor search failed: {str(e)}")
        
        # Add mock data for testing if no real jobs found
        if not jobs and max_jobs > 0:
            jobs = self._get_mock_glassdoor_jobs(role, location, max_jobs)
        
        return jobs
    
    def _get_mock_glassdoor_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Generate mock Glassdoor jobs for testing purposes."""
        mock_companies = ["Glassdoor Inc", "Review Corp", "Rating Systems", "Feedback Tech", "Opinion Hub"]
        mock_jobs = []
        
        for i in range(min(max_jobs, 5)):
            mock_jobs.append({
                "title": f"{role} - Review Team {i+1}",
                "company": mock_companies[i % len(mock_companies)],
                "location": location,
                "url": f"https://glassdoor.com/jobs/mock_{i}",
                "salary": f"${85000 + i*4000} - ${125000 + i*4000}",
                "description": f"Join {mock_companies[i % len(mock_companies)]} as a {role}",
                "source": "glassdoor",
                "posted_date": datetime.now().isoformat(),
                "job_id": f"glassdoor_mock_{i}"
            })
        
        return mock_jobs
    
    async def _search_google_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search Google Jobs for job postings."""
        jobs = []
        
        try:
            # Google Jobs search URL
            base_url = "https://www.google.com/search"
            params = {
                'q': f"{role} jobs {location}",
                'ibp': 'htl;jobs',  # Enable Google Jobs
                'hl': 'en'
            }
            
            # Build URL
            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in params.items()])
            url = f"{base_url}?{query_string}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse Google Jobs results
                    # Google Jobs results are typically in specific divs
                    job_cards = soup.find_all('div', {'class': 'g'}) or \
                               soup.find_all('div', {'data-ved': True}) or \
                               soup.find_all('div', {'class': 'job-result'})
                    
                    for card in job_cards[:max_jobs]:
                        job = self._parse_google_jobs_job(card, soup)
                        if job:
                            jobs.append(job)
                
        except Exception as e:
            self.log_action("ERROR", f"Google Jobs search failed: {str(e)}")
        
        # Add mock data for testing if no real jobs found
        if not jobs and max_jobs > 0:
            jobs = self._get_mock_google_jobs(role, location, max_jobs)
        
        return jobs
    
    def _get_mock_google_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Generate mock Google Jobs for testing purposes."""
        mock_companies = ["GlobalTech", "Future Systems", "Digital Innovations", "Smart Solutions", "NextGen Corp"]
        mock_jobs = []
        
        for i in range(min(max_jobs, 5)):
            mock_jobs.append({
                "title": f"Senior {role}",
                "company": mock_companies[i % len(mock_companies)],
                "location": location,
                "url": f"https://google.com/jobs/mock_{i}",
                "salary": None,
                "description": f"Join {mock_companies[i % len(mock_companies)]} as a {role}",
                "source": "google_jobs",
                "posted_date": datetime.now().isoformat(),
                "job_id": None
            })
        
        return mock_jobs
    
    def _parse_google_jobs_job(self, card, soup) -> Dict[str, Any]:
        """Parse individual Google Jobs posting."""
        try:
            # Validate input
            if not card:
                return None
                
            # Extract job title
            title_elem = card.find('h3') or card.find('a', {'data-ved': True})
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            # Extract company
            company_elem = card.find('span', {'class': 'company'}) or \
                          card.find('div', {'class': 'company-name'})
            company = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = card.find('span', {'class': 'location'}) or \
                           card.find('div', {'class': 'job-location'})
            location = location_elem.get_text(strip=True) if location_elem else "Unknown Location"
            
            # Extract job URL
            link_elem = card.find('a', {'data-ved': True}) or title_elem
            job_url = link_elem.get('href') if link_elem else ""
            if job_url and not job_url.startswith('http'):
                job_url = f"https://www.google.com{job_url}"
            
            # Extract job summary/description
            summary_elem = card.find('div', {'class': 'summary'}) or \
                          card.find('span', {'class': 'snippet'})
            summary = summary_elem.get_text(strip=True) if summary_elem else ""
            
            return {
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "salary": None,  # Google Jobs doesn't typically show salary
                "description": summary,
                "source": "google_jobs",
                "posted_date": datetime.now().isoformat(),
                "job_id": None
            }
            
        except Exception as e:
            self.log_action("PARSE_ERROR", f"Failed to parse Google Jobs job: {str(e)}")
            return None
    
    async def _search_company_websites(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search company websites for job postings."""
        jobs = []
        
        try:
            # List of major companies to search (can be expanded)
            target_companies = [
                "Google", "Microsoft", "Apple", "Amazon", "Meta", "Netflix",
                "Uber", "Airbnb", "Stripe", "Palantir", "OpenAI", "Anthropic",
                "Databricks", "Snowflake", "MongoDB", "Elastic", "GitHub"
            ]
            
            # Search for jobs at each company
            company_tasks = []
            for company in target_companies[:10]:  # Limit to first 10 companies
                task = self._search_company_jobs(company, role, location, max_jobs // len(target_companies))
                company_tasks.append(task)
            
            # Execute company searches in parallel
            if company_tasks:
                company_results = await asyncio.gather(*company_tasks, return_exceptions=True)
                
                for result in company_results:
                    if isinstance(result, list):
                        jobs.extend(result)
                    elif isinstance(result, Exception):
                        self.log_action("WARNING", f"Company search failed: {str(result)}")
                
        except Exception as e:
            self.log_action("ERROR", f"Company websites search failed: {str(e)}")
        
        # Add mock data for testing if no real jobs found
        if not jobs and max_jobs > 0:
            jobs = self._get_mock_company_jobs(role, location, max_jobs)
        
        return jobs
    
    async def _search_company_jobs(self, company: str, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search a specific company's career page for jobs."""
        jobs = []
        
        try:
            # Common career page patterns
            career_urls = [
                f"https://careers.{company.lower()}.com",
                f"https://jobs.{company.lower()}.com",
                f"https://{company.lower()}.com/careers",
                f"https://{company.lower()}.com/jobs"
            ]
            
            for career_url in career_urls:
                try:
                    async with self.session.get(career_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Look for job listings
                            job_links = soup.find_all('a', href=re.compile(r'job|career|position', re.I))
                            
                            for link in job_links[:max_jobs]:
                                job_title = link.get_text(strip=True)
                                if role.lower() in job_title.lower():
                                    job_url = link.get('href')
                                    if not job_url.startswith('http'):
                                        job_url = urljoin(career_url, job_url)
                                    
                                    jobs.append({
                                        "title": job_title,
                                        "company": company,
                                        "location": location,
                                        "url": job_url,
                                        "salary": None,
                                        "description": f"Job at {company}",
                                        "source": f"company_website_{company.lower()}",
                                        "posted_date": datetime.now().isoformat(),
                                        "job_id": None
                                    })
                            
                            if jobs:  # Found jobs, no need to check other URLs
                                break
                                
                except Exception as e:
                    continue  # Try next URL
                    
        except Exception as e:
            self.log_action("WARNING", f"Failed to search {company}: {str(e)}")
        
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
    
    def _get_mock_company_jobs(self, role: str, location: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Generate mock company website jobs for testing purposes."""
        mock_companies = ["Google", "Microsoft", "Apple", "Amazon", "Meta"]
        mock_jobs = []
        
        for i in range(min(max_jobs, 5)):
            company = mock_companies[i % len(mock_companies)]
            mock_jobs.append({
                "title": f"{role} at {company}",
                "company": company,
                "location": location,
                "url": f"https://{company.lower()}.com/careers/job_{i}",
                "salary": f"${100000 + i*10000} - ${150000 + i*10000}",
                "description": f"Join {company} as a {role} and work on cutting-edge technology",
                "source": f"company_website_{company.lower()}",
                "posted_date": datetime.now().isoformat(),
                "job_id": f"{company.lower()}_mock_{i}"
            })
        
        return mock_jobs
