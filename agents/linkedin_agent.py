import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from agents.base_agent import BaseAgent, AgentState
from config import Config
import os

class LinkedInAgent(BaseAgent):
    """Agent responsible for LinkedIn job search and application using LinkedIn API."""
    
    def __init__(self):
        super().__init__("LinkedInAgent")
        self.session = None
        self.access_token = None
        self.token_expiry = None
        self.base_url = "https://api.linkedin.com/v2"
        self.jobs_api_url = "https://api.linkedin.com/v2/jobs"
        self.search_api_url = "https://api.linkedin.com/v2/jobs/search"
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute LinkedIn job search and application operations."""
        
        # For LinkedIn operations, we need to get the operation type from the context
        # This agent is typically called during job processing, not from the main workflow state
        # We'll create a temporary state or use the existing state if it has job information
        
        # Since this agent is called during job processing, we need to handle the case
        # where we don't have direct access to operation data in the main state
        # For now, we'll return the state as-is and handle the actual LinkedIn operations in the calling context
        
        self.log_action("INFO", "LinkedIn agent called - job-specific operations handled in calling context")
        
        # Update state to indicate LinkedIn operations step
        state.steps_completed.append("linkedin_operations")
        state.current_step = "linkedin_operations_complete"
        
        return state
    
    async def search_jobs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for jobs on LinkedIn using the API."""
        
        # Validate required inputs
        required_fields = ["keywords"]
        if not self.validate_input(input_data, required_fields):
            return {"status": "error", "message": "Missing required fields"}
        
        keywords = input_data.get("keywords")
        location = input_data.get("location", Config.DEFAULT_LOCATION)
        max_results = input_data.get("max_results", Config.MAX_JOBS_PER_SOURCE)
        experience_level = input_data.get("experience_level", "")
        job_type = input_data.get("job_type", "")
        
        self.log_action("SEARCHING", f"Keywords: {keywords}, Location: {location}")
        
        try:
            # Ensure we have a valid access token
            if not await self._ensure_valid_token():
                return {
                    "status": "error",
                    "message": "Failed to obtain LinkedIn API access token"
                }
            
            # Build search parameters
            search_params = {
                "keywords": keywords,
                "location": location,
                "count": min(max_results, 50),  # LinkedIn API limit
                "start": 0
            }
            
            if experience_level:
                search_params["experience"] = experience_level
            
            if job_type:
                search_params["jobType"] = job_type
            
            # Perform the search
            jobs = await self._perform_job_search(search_params)
            
            self.log_action("COMPLETE", f"Found {len(jobs)} jobs")
            
            return {
                "status": "success",
                "jobs": jobs,
                "total_found": len(jobs),
                "search_criteria": search_params,
                "source": "linkedin"
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Job search failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Job search failed: {str(e)}"
            }
    
    async def apply_to_job(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job on LinkedIn using the API."""
        
        # Validate required inputs
        required_fields = ["job_id", "resume_path"]
        if not self.validate_input(input_data, required_fields):
            return {"status": "error", "message": "Missing required fields"}
        
        job_id = input_data.get("job_id")
        resume_path = input_data.get("resume_path")
        cover_letter = input_data.get("cover_letter", "")
        
        self.log_action("APPLYING", f"Job ID: {job_id}")
        
        try:
            # Ensure we have a valid access token
            if not await self._ensure_valid_token():
                return {
                    "status": "error",
                    "message": "Failed to obtain LinkedIn API access token"
                }
            
            # Check if Easy Apply is available
            job_details = await self.get_job_details({"job_id": job_id})
            if job_details.get("status") != "success":
                return {
                    "status": "error",
                    "message": "Could not retrieve job details"
                }
            
            # Check if Easy Apply is available
            if not job_details.get("easy_apply", False):
                return {
                    "status": "not_supported",
                    "message": "This job does not support Easy Apply via API"
                }
            
            # Submit the application
            application_result = await self._submit_application(job_id, resume_path, cover_letter)
            
            return application_result
            
        except Exception as e:
            self.log_action("ERROR", f"Application failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Application failed: {str(e)}"
            }
    
    async def get_job_details(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific job."""
        
        job_id = input_data.get("job_id")
        if not job_id:
            return {"status": "error", "message": "Job ID is required"}
        
        try:
            # Ensure we have a valid access token
            if not await self._ensure_valid_token():
                return {
                    "status": "error",
                    "message": "Failed to obtain LinkedIn API access token"
                }
            
            # Get job details from LinkedIn API
            job_details = await self._fetch_job_details(job_id)
            
            return {
                "status": "success",
                "job": job_details
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Failed to get job details: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get job details: {str(e)}"
            }
    
    async def get_my_applications(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of jobs the user has applied to."""
        
        try:
            # Ensure we have a valid access token
            if not await self._ensure_valid_token():
                return {
                    "status": "error",
                    "message": "Failed to obtain LinkedIn API access token"
                }
            
            # Get applications from LinkedIn API
            applications = await self._fetch_my_applications()
            
            return {
                "status": "success",
                "applications": applications,
                "total": len(applications)
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Failed to get applications: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to get applications: {str(e)}"
            }
    
    async def _ensure_valid_token(self) -> bool:
        """Ensure we have a valid LinkedIn API access token."""
        
        # Check if we have a valid token
        if (self.access_token and self.token_expiry and 
            datetime.now() < self.token_expiry):
            return True
        
        # Try to get a new token
        return await self._get_access_token()
    
    async def _get_access_token(self) -> bool:
        """Get LinkedIn API access token using OAuth2 flow."""
        
        try:
            # Check if we have client credentials
            client_id = os.getenv("LINKEDIN_CLIENT_ID")
            client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
            refresh_token = os.getenv("LINKEDIN_REFRESH_TOKEN")
            
            if not all([client_id, client_secret, refresh_token]):
                self.log_action("ERROR", "LinkedIn API credentials not configured")
                return False
            
            # Initialize session if needed
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Exchange refresh token for access token
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            async with self.session.post(token_url, data=token_data) as response:
                if response.status == 200:
                    token_info = await response.json()
                    
                    self.access_token = token_info.get("access_token")
                    expires_in = token_info.get("expires_in", 3600)
                    
                    # Set token expiry (subtract 5 minutes for safety)
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
                    
                    self.log_action("TOKEN_OBTAINED", "LinkedIn API access token obtained")
                    return True
                else:
                    self.log_action("ERROR", f"Failed to get access token: {response.status}")
                    return False
                    
        except Exception as e:
            self.log_action("ERROR", f"Token acquisition failed: {str(e)}")
            return False
    
    async def _perform_job_search(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform the actual job search using LinkedIn API."""
        
        jobs = []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Build search query
            search_query = {
                "keywords": search_params["keywords"],
                "location": search_params["location"],
                "count": search_params["count"],
                "start": search_params["start"]
            }
            
            # Add optional parameters
            if "experience" in search_params:
                search_query["experience"] = search_params["experience"]
            
            if "jobType" in search_params:
                search_query["jobType"] = search_params["jobType"]
            
            # Make the API call
            async with self.session.post(
                self.search_api_url,
                headers=headers,
                json=search_query
            ) as response:
                
                if response.status == 200:
                    search_results = await response.json()
                    
                    # Parse the results
                    elements = search_results.get("elements", [])
                    for element in elements:
                        job = self._parse_job_element(element)
                        if job:
                            jobs.append(job)
                else:
                    self.log_action("ERROR", f"Search API returned {response.status}")
                    
        except Exception as e:
            self.log_action("ERROR", f"Job search API call failed: {str(e)}")
        
        return jobs
    
    async def _fetch_job_details(self, job_id: str) -> Dict[str, Any]:
        """Fetch detailed information about a specific job."""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            url = f"{self.jobs_api_url}/{job_id}"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    job_data = await response.json()
                    return self._parse_job_details(job_data)
                else:
                    self.log_action("ERROR", f"Job details API returned {response.status}")
                    return {}
                    
        except Exception as e:
            self.log_action("ERROR", f"Failed to fetch job details: {str(e)}")
            return {}
    
    async def _submit_application(self, job_id: str, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Submit a job application via LinkedIn API."""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Prepare application data
            application_data = {
                "jobId": job_id,
                "resumePath": resume_path
            }
            
            if cover_letter:
                application_data["coverLetter"] = cover_letter
            
            # Submit application
            apply_url = f"{self.jobs_api_url}/{job_id}/applications"
            
            async with self.session.post(
                apply_url,
                headers=headers,
                json=application_data
            ) as response:
                
                if response.status in [200, 201]:
                    self.log_action("SUCCESS", f"Application submitted for job {job_id}")
                    return {
                        "status": "success",
                        "message": "Application submitted successfully",
                        "job_id": job_id,
                        "application_id": response.headers.get("X-Application-Id")
                    }
                else:
                    self.log_action("ERROR", f"Application submission failed: {response.status}")
                    return {
                        "status": "failed",
                        "message": f"Application submission failed with status {response.status}",
                        "job_id": job_id
                    }
                    
        except Exception as e:
            self.log_action("ERROR", f"Application submission failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Application submission failed: {str(e)}",
                "job_id": job_id
            }
    
    async def _fetch_my_applications(self) -> List[Dict[str, Any]]:
        """Fetch list of user's job applications."""
        
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Get user's applications
            applications_url = f"{self.base_url}/jobApplications"
            
            async with self.session.get(applications_url, headers=headers) as response:
                if response.status == 200:
                    applications_data = await response.json()
                    
                    applications = []
                    elements = applications_data.get("elements", [])
                    
                    for element in elements:
                        application = self._parse_application_element(element)
                        if application:
                            applications.append(application)
                    
                    return applications
                else:
                    self.log_action("ERROR", f"Applications API returned {response.status}")
                    return []
                    
        except Exception as e:
            self.log_action("ERROR", f"Failed to fetch applications: {str(e)}")
            return []
    
    def _parse_job_element(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a job element from search results."""
        
        try:
            # Extract basic job information
            job_id = element.get("id")
            title = element.get("title", "Unknown Title")
            company = element.get("company", {}).get("name", "Unknown Company")
            location = element.get("location", {}).get("name", "Unknown Location")
            
            # Extract additional details
            description = element.get("description", "")
            experience_level = element.get("experienceLevel", "")
            job_type = element.get("employmentStatus", "")
            posted_date = element.get("listedAt")
            
            # Check if Easy Apply is available
            easy_apply = element.get("easyApply", False)
            
            return {
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "experience_level": experience_level,
                "job_type": job_type,
                "posted_date": posted_date,
                "easy_apply": easy_apply,
                "source": "linkedin",
                "url": f"https://www.linkedin.com/jobs/view/{job_id}"
            }
            
        except Exception as e:
            self.log_action("PARSE_ERROR", f"Failed to parse job element: {str(e)}")
            return None
    
    def _parse_job_details(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse detailed job information."""
        
        try:
            return {
                "id": job_data.get("id"),
                "title": job_data.get("title", "Unknown Title"),
                "company": job_data.get("company", {}).get("name", "Unknown Company"),
                "location": job_data.get("location", {}).get("name", "Unknown Location"),
                "description": job_data.get("description", ""),
                "requirements": job_data.get("requirements", ""),
                "experience_level": job_data.get("experienceLevel", ""),
                "job_type": job_data.get("employmentStatus", ""),
                "posted_date": job_data.get("listedAt"),
                "easy_apply": job_data.get("easyApply", False),
                "application_count": job_data.get("applicationCount", 0),
                "source": "linkedin"
            }
            
        except Exception as e:
            self.log_action("PARSE_ERROR", f"Failed to parse job details: {str(e)}")
            return {}
    
    def _parse_application_element(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse an application element from user's applications."""
        
        try:
            return {
                "application_id": element.get("id"),
                "job_id": element.get("jobId"),
                "job_title": element.get("jobTitle", "Unknown Title"),
                "company": element.get("companyName", "Unknown Company"),
                "application_date": element.get("appliedAt"),
                "status": element.get("status", "Unknown"),
                "source": "linkedin"
            }
            
        except Exception as e:
            self.log_action("PARSE_ERROR", f"Failed to parse application element: {str(e)}")
            return None
    
    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None
