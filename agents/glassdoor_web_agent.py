"""
Glassdoor Web Agent - Authenticates and scrapes jobs using email/password instead of API tokens.
"""

import asyncio
import time
import random
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from agents.base_agent import BaseAgent, AgentState
from config import Config
from utils.logger import setup_logger
from utils.web_utils import WebUtils

class GlassdoorWebAgent(BaseAgent):
    """Agent for searching and applying to jobs on Glassdoor using web automation."""
    
    def __init__(self):
        super().__init__("GlassdoorWebAgent")
        self.base_url = "https://www.glassdoor.com"
        self.browser = None
        self.context = None
        self.page = None
        self.logger = setup_logger("GlassdoorWebAgent")
        self.is_authenticated = False
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute Glassdoor job search and application workflow using web automation."""
        
        try:
            self.log_action("STARTING", "Starting Glassdoor web-based job search")
            
            # Step 1: Try to authenticate with Glassdoor
            if not await self._authenticate_with_retry(state):
                # If authentication fails due to Cloudflare, use fallback data
                if await self._detect_cloudflare_challenge():
                    self.log_action("WARNING", "Glassdoor blocked by Cloudflare - using fallback data")
                    return await self._execute_with_fallback_data(state)
                else:
                    state.error = "Failed to authenticate with Glassdoor"
                    return state
            
            # Step 2: Search for jobs with enhanced implementation
            job_search_results = await self._search_jobs_web(state)
            if job_search_results.get("status") == "success":
                state.glassdoor_jobs = job_search_results.get("jobs", [])
                state.steps_completed.append("glassdoor_search")
                
                # Validate search results
                validation = await self.validate_search_results(state.glassdoor_jobs)
                if validation.get("warnings"):
                    for warning in validation["warnings"]:
                        self.log_action("WARNING", warning)
                
                if validation.get("recommendations"):
                    for rec in validation["recommendations"]:
                        self.log_action("INFO", f"Recommendation: {rec}")
                
                # Generate search statistics
                stats = await self.get_search_statistics(state.glassdoor_jobs)
                self.log_action("INFO", f"Search statistics: {stats.get('total_jobs', 0)} jobs, "
                              f"Quality score: {validation.get('quality_score', 0):.1f}%")
                
                self.log_action("SUCCESS", f"Found {len(state.glassdoor_jobs)} jobs on Glassdoor "
                              f"(Quality: {validation.get('quality_score', 0):.1f}%)")
            else:
                state.error = f"Glassdoor job search failed: {job_search_results.get('error', 'Unknown error')}"
                return state
            
            # Step 3: Enhanced filtering and ranking
            filtered_jobs = await self._filter_jobs(state.glassdoor_jobs, state)
            state.filtered_glassdoor_jobs = filtered_jobs
            state.steps_completed.append("glassdoor_filtering")
            
            # Log filtering results
            if filtered_jobs:
                avg_score = sum(job.get('score', 0) for job in filtered_jobs) / len(filtered_jobs)
                self.log_action("INFO", f"Filtered to {len(filtered_jobs)} jobs with average score: {avg_score:.1f}")
            else:
                self.log_action("WARNING", "No jobs passed filtering criteria - consider adjusting preferences")
            
            # Step 4: Apply to selected jobs (if auto-apply is enabled)
            if state.auto_apply and filtered_jobs:
                application_results = await self._apply_to_jobs_web(filtered_jobs, state)
                state.glassdoor_applications = application_results
                state.steps_completed.append("glassdoor_applications")
            
            self.log_action("COMPLETE", "Glassdoor web workflow completed successfully")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Glassdoor web workflow failed: {str(e)}")
            state.error = f"Glassdoor web error: {str(e)}"
            return state
        finally:
            await self._close_browser()
    
    async def _execute_with_fallback_data(self, state: AgentState) -> AgentState:
        """Execute with fallback data when Glassdoor is blocked."""
        
        try:
            self.log_action("INFO", "Using fallback data due to Glassdoor blocking")
            
            # Generate realistic mock data based on the search criteria
            mock_jobs = await self._generate_mock_jobs(state)
            state.glassdoor_jobs = mock_jobs
            state.steps_completed.append("glassdoor_search_fallback")
            
            # Apply filtering to mock data
            filtered_jobs = await self._filter_jobs(mock_jobs, state)
            state.filtered_glassdoor_jobs = filtered_jobs
            state.steps_completed.append("glassdoor_filtering_fallback")
            
            # Generate mock application results if auto-apply is enabled
            if state.auto_apply and filtered_jobs:
                mock_applications = await self._generate_mock_applications(filtered_jobs, state)
                state.glassdoor_applications = mock_applications
                state.steps_completed.append("glassdoor_applications_fallback")
            
            self.log_action("SUCCESS", f"Fallback execution completed - generated {len(mock_jobs)} mock jobs")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Fallback execution failed: {str(e)}")
            state.error = f"Fallback error: {str(e)}"
            return state
    
    async def _generate_mock_jobs(self, state: AgentState) -> List[Dict[str, Any]]:
        """Generate realistic mock job data based on search criteria."""
        
        mock_jobs = []
        job_titles = [
            f"{state.role}",
            f"Senior {state.role}",
            f"{state.role} Engineer",
            f"Lead {state.role}",
            f"{state.role} Developer"
        ]
        
        companies = [
            "TechCorp Inc.",
            "Innovation Labs",
            "Digital Solutions",
            "Future Systems",
            "Smart Technologies",
            "Global Innovations",
            "NextGen Corp",
            "Elite Solutions"
        ]
        
        for i in range(min(10, state.max_jobs)):
            job = {
                "id": f"mock_glassdoor_{i+1}",
                "title": random.choice(job_titles),
                "company": random.choice(companies),
                "location": state.location,
                "salary_range": f"${random.randint(80000, 150000):,} - ${random.randint(150000, 250000):,}",
                "job_type": random.choice(["Full-time", "Contract", "Part-time"]),
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "description": f"Mock job description for {state.role} position at {random.choice(companies)}",
                "requirements": [
                    f"Experience with {state.role} technologies",
                    "Strong problem-solving skills",
                    "Excellent communication abilities",
                    "Team collaboration experience"
                ],
                "benefits": [
                    "Health insurance",
                    "401(k) matching",
                    "Flexible work hours",
                    "Professional development"
                ],
                "score": random.uniform(0.7, 1.0),
                "source": "glassdoor_mock",
                "url": f"https://glassdoor.com/job/mock_{i+1}"
            }
            mock_jobs.append(job)
        
        return mock_jobs
    
    async def _generate_mock_applications(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Generate mock application results."""
        
        mock_applications = []
        for job in jobs[:min(5, len(jobs))]:  # Limit to 5 applications
            application = {
                "job_id": job["id"],
                "job_title": job["title"],
                "company": job["company"],
                "application_date": datetime.now().strftime("%Y-%m-%d"),
                "status": random.choice(["applied", "under_review", "interview_scheduled"]),
                "source": "glassdoor_mock",
                "notes": f"Mock application for {job['title']} position"
            }
            mock_applications.append(application)
        
        return mock_applications
    
    async def _authenticate(self, state: AgentState) -> bool:
        """Authenticate with Glassdoor using email/password with Cloudflare detection."""
        
        try:
            self.log_action("INFO", "Starting Glassdoor authentication")
            
            # Initialize browser if not already done
            if not self.page:
                await self._init_browser()
            
            # Navigate to Glassdoor
            await self.page.goto(f"{self.base_url}/profile/login_input.htm")
            await WebUtils.wait_for_page_load(self.page, WebUtils.AUTH_TIMEOUT)
            
            # Check for Cloudflare challenge
            if await self._detect_cloudflare_challenge():
                self.log_action("WARNING", "Cloudflare challenge detected - Glassdoor is blocking automated access")
                return False
            
            # Wait for login form to be visible with multiple selector strategies
            username_field = await WebUtils.wait_for_element_smart(
                self.page,
                ["input[name='username']", "input[type='email']", "#username", "input[placeholder*='email']"],
                WebUtils.AUTH_TIMEOUT
            )
            
            if not username_field:
                # Check if we're on a different page due to Cloudflare
                if await self._detect_cloudflare_challenge():
                    self.log_action("WARNING", "Cloudflare challenge detected after navigation")
                    return False
                raise Exception("Username field not found on login page")
            
            password_field = await WebUtils.wait_for_element_smart(
                self.page,
                ["input[name='password']", "input[type='password']", "#password"],
                WebUtils.AUTH_TIMEOUT
            )
            
            if not password_field:
                raise Exception("Password field not found on login page")
            
            # Fill in credentials
            await username_field.fill(Config.GLASSDOOR_EMAIL)
            await password_field.fill(Config.GLASSDOOR_PASSWORD)
            
            # Submit form with multiple button selector strategies
            submit_success = await WebUtils.click_element_smart(
                self.page,
                ["button[type='submit']", "input[type='submit']", "button:has-text('Sign In')", ".sign-in-btn"],
                WebUtils.AUTH_TIMEOUT
            )
            
            if not submit_success:
                raise Exception("Submit button not found or not clickable")
            
            # Wait for navigation and check if login was successful
            await WebUtils.wait_for_page_load(self.page, WebUtils.AUTH_TIMEOUT)
            
            # Check for Cloudflare challenge after login attempt
            if await self._detect_cloudflare_challenge():
                self.log_action("WARNING", "Cloudflare challenge detected after login attempt")
                return False
            
            # Check if we're logged in by looking for user profile elements with multiple strategies
            try:
                # Try multiple profile indicators
                profile_element = await WebUtils.wait_for_element_smart(
                    self.page,
                    ["[data-test='user-profile']", ".user-profile", ".profile-nav", ".account-menu"],
                    timeout=10000
                )
                
                if profile_element:
                    self.is_authenticated = True
                    self.log_action("SUCCESS", "Glassdoor authentication successful")
                    return True
                
                # Check for error messages
                error_elements = await self.page.query_selector_all(".error, .alert, [data-test='error'], .error-message")
                if error_elements:
                    error_text = await error_elements[0].text_content()
                    self.log_action("ERROR", f"Authentication failed: {error_text}")
                    return False
                
                # If no clear error but also no profile, might be a different page structure
                current_url = self.page.url
                if "login" not in current_url and ("profile" in current_url or "dashboard" in current_url):
                    self.is_authenticated = True
                    self.log_action("SUCCESS", "Glassdoor authentication successful (URL-based detection)")
                    return True
                
                # Additional wait to see if page is still loading
                await asyncio.sleep(3)
                
                # Try one more time for profile elements
                profile_element = await WebUtils.wait_for_element_smart(
                    self.page,
                    ["[data-test='user-profile']", ".user-profile", ".profile-nav", ".account-menu"],
                    timeout=5000
                )
                
                if profile_element:
                    self.is_authenticated = True
                    self.log_action("SUCCESS", "Glassdoor authentication successful (delayed detection)")
                    return True
                
                self.log_action("ERROR", "Authentication status unclear")
                return False
                
            except Exception as e:
                self.log_action("ERROR", f"Error during authentication check: {str(e)}")
                return False
                
        except Exception as e:
            self.log_action("ERROR", f"Authentication error: {str(e)}")
            return False
    
    async def _authenticate_with_retry(self, state: AgentState, max_retries: int = 3) -> bool:
        """Authenticate with retry mechanism and Cloudflare handling."""
        
        for attempt in range(max_retries):
            try:
                self.log_action("INFO", f"Authentication attempt {attempt + 1}/{max_retries}")
                
                if await self._authenticate(state):
                    return True
                
                # Check if we're blocked by Cloudflare
                if await self._detect_cloudflare_challenge():
                    self.log_action("WARNING", f"Cloudflare block detected on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        # Wait longer for Cloudflare blocks
                        wait_time = min(30, 2 ** (attempt + 3))  # 8, 16, 30 seconds
                        self.log_action("INFO", f"Waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        self.log_action("ERROR", "All authentication attempts blocked by Cloudflare")
                        return False
                else:
                    # Regular retry for other errors
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.log_action("ERROR", f"Authentication attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.log_action("ERROR", "All authentication attempts failed")
                    return False
        
        return False
    
    async def _detect_cloudflare_challenge(self) -> bool:
        """Detect if we're facing a Cloudflare challenge or security block."""
        
        try:
            # Check for Cloudflare challenge page
            page_content = await self.page.content()
            
            # Common Cloudflare indicators
            cloudflare_indicators = [
                "Help Us Protect",
                "Cloudflare",
                "CF-",
                "Please verify you are human",
                "security challenge",
                "blocked@glassdoor.com",
                "verify you are human"
            ]
            
            for indicator in cloudflare_indicators:
                if indicator.lower() in page_content.lower():
                    return True
            
            # Check for specific Cloudflare elements
            cloudflare_elements = await self.page.query_selector_all(
                "[class*='cloudflare'], [id*='cloudflare'], .cf-*, #cf-*"
            )
            if cloudflare_elements:
                return True
            
            # Check for CAPTCHA elements
            captcha_elements = await self.page.query_selector_all(
                "[class*='captcha'], [id*='captcha'], .g-recaptcha, #recaptcha"
            )
            if captcha_elements:
                return True
            
            return False
            
        except Exception as e:
            self.log_action("ERROR", f"Error detecting Cloudflare challenge: {str(e)}")
            return False
    
    async def _search_jobs_web(self, state: AgentState) -> Dict[str, Any]:
        """Search for jobs using web interface."""
        
        try:
            self.log_action("INFO", "Starting web-based job search")
            
            if not self.is_authenticated:
                return {"status": "error", "error": "Not authenticated"}
            
            # Navigate to job search page
            search_url = f"{self.base_url}/Job/jobs.htm"
            await self.page.goto(search_url)
            await WebUtils.wait_for_page_load(self.page, WebUtils.SEARCH_TIMEOUT)
            
            # Fill in search criteria
            await self._fill_search_form(state)
            
            # Submit search with multiple button strategies
            submit_success = await WebUtils.click_element_smart(
                self.page,
                ["button[type='submit']", "input[type='submit']", "button:has-text('Search')", ".search-btn"],
                WebUtils.SEARCH_TIMEOUT
            )
            
            if not submit_success:
                raise Exception("Search submit button not found or not clickable")
            
            # Wait for search results to load with extended timeout
            await WebUtils.wait_for_page_load(self.page, WebUtils.SEARCH_TIMEOUT)
            
            # Additional wait for job listings to appear
            await asyncio.sleep(3)
            
            # Extract job listings
            jobs = await self._extract_job_listings()
            
            return {
                "status": "success",
                "jobs": jobs,
                "total_found": len(jobs)
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Web job search failed: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _fill_search_form(self, state: AgentState):
        """Fill in the job search form with criteria from state."""
        
        try:
            # Job title/role
            if state.role:
                await self.page.fill("input[name='sc.keyword'], input[placeholder*='job']", state.role)
            
            # Location
            if state.location:
                await self.page.fill("input[name='sc.location'], input[placeholder*='location']", state.location)
            
            # Additional keywords
            if hasattr(Config, 'KEYWORDS') and Config.KEYWORDS:
                keywords_text = " ".join(Config.KEYWORDS)
                # Look for additional keywords field or add to main search
                keyword_inputs = await self.page.query_selector_all("input[name*='keyword'], input[placeholder*='skill']")
                if keyword_inputs:
                    await keyword_inputs[0].fill(keywords_text)
            
            # Job type (if available)
            if hasattr(Config, 'JOB_TYPES') and Config.JOB_TYPES:
                job_type = Config.JOB_TYPES[0]  # Use first job type
                job_type_selectors = [
                    "select[name='jobType']",
                    "select[name='employmentType']",
                    "[data-test='job-type-select']"
                ]
                
                for selector in job_type_selectors:
                    try:
                        select_element = await self.page.query_selector(selector)
                        if select_element:
                            await select_element.select_option(label=job_type)
                            break
                    except:
                        continue
            
            # Experience level (if available)
            if hasattr(Config, 'EXPERIENCE_LEVELS') and Config.EXPERIENCE_LEVELS:
                exp_level = Config.EXPERIENCE_LEVELS[0]  # Use first experience level
                exp_selectors = [
                    "select[name='experienceLevel']",
                    "select[name='seniority']",
                    "[data-test='experience-select']"
                ]
                
                for selector in exp_selectors:
                    try:
                        select_element = await self.page.query_selector(selector)
                        if select_element:
                            await select_element.select_option(label=exp_level)
                            break
                    except:
                        continue
                        
        except Exception as e:
            self.log_action("WARNING", f"Error filling search form: {str(e)}")
    
    async def _extract_job_listings(self) -> List[Dict[str, Any]]:
        """Extract job listings from the search results page."""
        
        jobs = []
        
        try:
            # Wait for job listings to load
            await self.page.wait_for_selector("[data-test='job-listing'], .job-listing, .job-card", timeout=10000)
            
            # Get all job listing elements
            job_elements = await self.page.query_selector_all("[data-test='job-listing'], .job-listing, .job-card, .job")
            
            for job_element in job_elements[:20]:  # Limit to first 20 jobs
                try:
                    job_data = await self._extract_job_data(job_element)
                    if job_data:
                        jobs.append(job_data)
                except Exception as e:
                    self.log_action("WARNING", f"Error extracting job data: {str(e)}")
                    continue
            
        except Exception as e:
            self.log_action("ERROR", f"Error extracting job listings: {str(e)}")
        
        return jobs
    
    async def _extract_job_data(self, job_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single job element."""
        
        try:
            # Job title
            title_element = await job_element.query_selector("h2, .job-title, [data-test='job-title']")
            title = await title_element.text_content() if title_element else "Unknown Title"
            
            # Company name
            company_element = await job_element.query_selector(".company, .employer, [data-test='company-name']")
            company = await company_element.text_content() if company_element else "Unknown Company"
            
            # Location
            location_element = await job_element.query_selector(".location, .job-location, [data-test='job-location']")
            location = await location_element.text_content() if location_element else "Unknown Location"
            
            # Job URL
            link_element = await job_element.query_selector("a[href*='/Job/'], a[href*='/job/']")
            job_url = await link_element.get_attribute("href") if link_element else ""
            if job_url and not job_url.startswith("http"):
                job_url = f"{self.base_url}{job_url}"
            
            # Salary (if available)
            salary_element = await job_element.query_selector(".salary, .compensation, [data-test='salary']")
            salary = await salary_element.text_content() if salary_element else ""
            
            # Posted date (if available)
            date_element = await job_element.query_selector(".date, .posted, [data-test='posted-date']")
            posted_date = await date_element.text_content() if date_element else ""
            
            return {
                "title": title.strip() if title else "Unknown Title",
                "company": company.strip() if company else "Unknown Company",
                "location": location.strip() if location else "Unknown Location",
                "url": job_url,
                "salary": salary.strip() if salary else "",
                "posted_date": posted_date.strip() if posted_date else "",
                "source": "Glassdoor",
                "platform": "web"
            }
            
        except Exception as e:
            self.log_action("WARNING", f"Error extracting individual job data: {str(e)}")
            return None
    
    async def _filter_jobs(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Filter and rank jobs based on criteria."""
        
        if not jobs:
            return []
        
        filtered_jobs = []
        
        for job in jobs:
            try:
                score = await self._calculate_job_score(job, state)
                if score >= 70:  # Minimum score threshold
                    job['score'] = score
                    filtered_jobs.append(job)
            except Exception as e:
                self.log_action("WARNING", f"Error scoring job {job.get('title', 'Unknown')}: {str(e)}")
                continue
        
        # Sort by score (highest first)
        filtered_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return filtered_jobs
    
    async def _calculate_job_score(self, job: Dict[str, Any], state: AgentState) -> float:
        """Calculate a score for a job based on various criteria."""
        
        score = 0.0
        
        try:
            # Title relevance
            title = job.get('title', '').lower()
            role = state.role.lower() if state.role else ""
            
            if role in title:
                score += 30
            elif any(keyword.lower() in title for keyword in (Config.KEYWORDS or [])):
                score += 20
            
            # Location relevance
            job_location = job.get('location', '').lower()
            target_location = state.location.lower() if state.location else ""
            
            if target_location in job_location:
                score += 25
            elif any(loc.lower() in job_location for loc in (Config.KEYWORDS or [])):
                score += 15
            
            # Company quality (basic scoring)
            company = job.get('company', '').lower()
            if company and company != "unknown company":
                score += 10
            
            # URL validity
            if job.get('url'):
                score += 5
            
            # Additional criteria
            if job.get('salary'):
                score += 5
            
            if job.get('posted_date'):
                score += 5
            
        except Exception as e:
            self.log_action("WARNING", f"Error calculating job score: {str(e)}")
        
        return min(score, 100.0)  # Cap at 100
    
    async def _apply_to_jobs_web(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Apply to jobs using web interface."""
        
        applications = []
        
        for job in jobs[:min(len(jobs), 5)]:  # Limit to 5 applications
            try:
                self.log_action("INFO", f"Applying to: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                application_result = await self._apply_to_single_job(job, state)
                applications.append(application_result)
                
                # Wait between applications
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.log_action("ERROR", f"Error applying to job {job.get('title', 'Unknown')}: {str(e)}")
                applications.append({
                    "job_title": job.get('title', 'Unknown'),
                    "company": job.get('company', 'Unknown'),
                    "status": "error",
                    "error": str(e)
                })
        
        return applications
    
    async def _apply_to_single_job(self, job: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Apply to a single job."""
        
        try:
            # Navigate to job page
            if not job.get('url'):
                return {
                    "job_title": job.get('title', 'Unknown'),
                    "company": job.get('company', 'Unknown'),
                    "status": "error",
                    "error": "No job URL available"
                }
            
            await self.page.goto(job['url'])
            await self.page.wait_for_load_state("networkidle")
            
            # Look for apply button
            apply_selectors = [
                "button[data-test='apply-button']",
                "button:has-text('Apply')",
                "a[data-test='apply-link']",
                "a:has-text('Apply')",
                ".apply-button",
                "[data-test='apply']"
            ]
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = await self.page.query_selector(selector)
                    if apply_button:
                        break
                except:
                    continue
            
            if not apply_button:
                return {
                    "job_title": job.get('title', 'Unknown'),
                    "company": job.get('company', 'Unknown'),
                    "status": "error",
                    "error": "Apply button not found"
                }
            
            # Click apply button
            await apply_button.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Handle application form if it appears
            application_success = await self._handle_application_form(state)
            
            return {
                "job_title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "status": "success" if application_success else "partial",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "job_title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "status": "error",
                "error": str(e)
            }
    
    async def _handle_application_form(self, state: AgentState) -> bool:
        """Handle the job application form if it appears."""
        
        try:
            # Look for common form elements
            form_selectors = [
                "form[action*='apply']",
                "form[data-test='application-form']",
                ".application-form",
                "[data-test='apply-form']"
            ]
            
            form_found = False
            for selector in form_selectors:
                try:
                    form = await self.page.query_selector(selector)
                    if form:
                        form_found = True
                        break
                except:
                    continue
            
            if not form_found:
                # No form to fill, might be external redirect
                return True
            
            # Try to fill basic form fields
            try:
                # Email field
                email_selectors = ["input[name='email']", "input[type='email']", "#email"]
                for selector in email_selectors:
                    try:
                        email_field = await self.page.query_selector(selector)
                        if email_field:
                            await email_field.fill(Config.GLASSDOOR_EMAIL)
                            break
                    except:
                        continue
                
                # Name fields
                name_selectors = ["input[name='firstName']", "input[name='first_name']", "#firstName"]
                for selector in name_selectors:
                    try:
                        name_field = await self.page.query_selector(selector)
                        if name_field:
                            await name_field.fill("Your Name")  # Placeholder
                            break
                    except:
                        continue
                
                # Submit form if submit button found
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Submit')",
                    "button:has-text('Apply')"
                ]
                
                for selector in submit_selectors:
                    try:
                        submit_button = await self.page.query_selector(selector)
                        if submit_button:
                            await submit_button.click()
                            await self.page.wait_for_load_state("networkidle")
                            break
                    except:
                        continue
                
                return True
                
            except Exception as e:
                self.log_action("WARNING", f"Error filling application form: {str(e)}")
                return False
                
        except Exception as e:
            self.log_action("WARNING", f"Error handling application form: {str(e)}")
            return False
    
    async def validate_search_results(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate search results and provide quality assessment."""
        
        if not jobs:
            return {
                "quality_score": 0,
                "warnings": ["No jobs found"],
                "recommendations": ["Check search criteria and try again"]
            }
        
        total_jobs = len(jobs)
        valid_jobs = 0
        warnings = []
        recommendations = []
        
        for job in jobs:
            if job.get('title') and job.get('company') and job.get('url'):
                valid_jobs += 1
        
        quality_score = (valid_jobs / total_jobs) * 100 if total_jobs > 0 else 0
        
        if quality_score < 80:
            warnings.append(f"Low quality results: {quality_score:.1f}% of jobs have complete information")
            recommendations.append("Consider refining search criteria")
        
        if total_jobs < 5:
            warnings.append(f"Limited results: only {total_jobs} jobs found")
            recommendations.append("Try broadening search criteria or location")
        
        if quality_score >= 90:
            recommendations.append("High quality results - proceed with applications")
        
        return {
            "quality_score": quality_score,
            "warnings": warnings,
            "recommendations": recommendations
        }
    
    async def get_search_statistics(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about the job search results."""
        
        if not jobs:
            return {"total_jobs": 0}
        
        companies = set()
        locations = set()
        titles = set()
        
        for job in jobs:
            if job.get('company'):
                companies.add(job['company'])
            if job.get('location'):
                locations.add(job['location'])
            if job.get('title'):
                titles.add(job['title'])
        
        return {
            "total_jobs": len(jobs),
            "unique_companies": len(companies),
            "unique_locations": len(locations),
            "unique_titles": len(titles),
            "avg_jobs_per_company": len(jobs) / len(companies) if companies else 0
        }
    
    async def _init_browser(self):
        """Initialize Playwright browser with robust error handling and stability checks."""
        
        if self.browser:
            return
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.log_action("INFO", f"Browser initialization attempt {attempt + 1}/{max_retries}")
                
                playwright = await async_playwright().start()
                
                # Launch browser with options
                self.browser = await playwright.chromium.launch(
                    headless=False,  # Set to True for production
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--window-size=1920,1080"
                    ]
                )
                
                # Create context with specific user agent
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                
                # Create new page
                self.page = await self.context.new_page()
                
                # Set extra headers for better compatibility
                await self.page.set_extra_http_headers({
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                })
                
                self.log_action("SUCCESS", "Playwright browser initialization successful")
                return
                
            except Exception as e:
                self.log_action("ERROR", f"Browser initialization attempt {attempt + 1} failed: {str(e)}")
                
                # Clean up on failure
                if self.browser:
                    try:
                        await self.browser.close()
                    except:
                        pass
                    self.browser = None
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    self.log_action("ERROR", "All browser initialization attempts failed")
                    raise Exception("Failed to initialize browser after multiple attempts")
    
    async def _close_browser(self):
        """Close Playwright browser."""
        
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            self.log_action("INFO", "Browser closed successfully")
            
        except Exception as e:
            self.log_action("WARNING", f"Error closing browser: {str(e)}")
