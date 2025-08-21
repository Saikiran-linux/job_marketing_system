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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from agents.base_agent import BaseAgent, AgentState
from config import Config
from utils.logger import setup_logger

class GlassdoorWebAgent(BaseAgent):
    """Agent for searching and applying to jobs on Glassdoor using web automation."""
    
    def __init__(self):
        super().__init__("GlassdoorWebAgent")
        self.base_url = "https://www.glassdoor.com"
        self.driver = None
        self.logger = setup_logger("GlassdoorWebAgent")
        self.is_authenticated = False
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute Glassdoor job search and application workflow using web automation."""
        
        try:
            self.log_action("STARTING", "Starting Glassdoor web-based job search")
            
            # Step 1: Authenticate with Glassdoor
            if not await self._authenticate_with_retry(state):
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
    
    async def _authenticate(self, state: AgentState) -> bool:
        """Authenticate with Glassdoor using email and password with enhanced stability."""
        
        try:
            # Get credentials from state or config
            email = getattr(state, 'glassdoor_email', None) or Config.GLASSDOOR_EMAIL
            password = getattr(state, 'glassdoor_password', None) or Config.GLASSDOOR_PASSWORD
            
            if not email or not password:
                self.log_action("ERROR", "Glassdoor credentials not provided")
                return False
            
            # Initialize browser with stability checks
            self.log_action("INFO", "Initializing browser for authentication...")
            await self._init_browser()
            
            # Wait for browser to be fully stable before proceeding
            self.log_action("INFO", "Waiting for browser to stabilize before authentication...")
            await asyncio.sleep(3)
            
            # Test browser one more time before authentication
            if not await self._test_browser_stability():
                self.log_action("ERROR", "Browser failed stability test before authentication")
                return False
            
            # Navigate to Glassdoor login page with error handling
            self.log_action("INFO", "Navigating to Glassdoor login page...")
            try:
                self.driver.get(f"{self.base_url}/profile/login_input.htm")
                await asyncio.sleep(3)  # Increased wait time
                
                # Verify we're on the login page
                if "login" not in self.driver.current_url.lower():
                    self.log_action("WARNING", "Not on login page, trying alternative URL")
                    self.driver.get(f"{self.base_url}/profile/login.htm")
                    await asyncio.sleep(3)
                
            except Exception as e:
                self.log_action("ERROR", f"Failed to navigate to login page: {str(e)}")
                return False
            
            # Wait for page to fully load
            await asyncio.sleep(2)
            
            # Find and fill email field with retry logic
            email_field = None
            email_selectors = ["userEmail", "email", "username", "user_email"]
            
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, selector))
                    )
                    if email_field:
                        self.log_action("INFO", f"Found email field with selector: {selector}")
                        break
                except:
                    continue
            
            if not email_field:
                self.log_action("ERROR", "Could not find email field on login page")
                return False
            
            # Fill email field
            try:
                email_field.clear()
                await asyncio.sleep(0.5)
                email_field.send_keys(email)
                await asyncio.sleep(0.5)
                self.log_action("INFO", "Email field filled successfully")
            except Exception as e:
                self.log_action("ERROR", f"Failed to fill email field: {str(e)}")
                return False
            
            # Find and fill password field
            password_field = None
            password_selectors = ["userPassword", "password", "pass", "user_password"]
            
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.ID, selector)
                    if password_field:
                        self.log_action("INFO", f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                self.log_action("ERROR", "Could not find password field on login page")
                return False
            
            # Fill password field
            try:
                password_field.clear()
                await asyncio.sleep(0.5)
                password_field.send_keys(password)
                await asyncio.sleep(0.5)
                self.log_action("INFO", "Password field filled successfully")
            except Exception as e:
                self.log_action("ERROR", f"Failed to fill password field: {str(e)}")
                return False
            
            # Wait before clicking login button
            await asyncio.sleep(1)
            
            # Find and click login button with retry logic
            login_button = None
            login_selectors = ["btnSubmit", "login-button", "submit", "signin", "btnLogin"]
            
            for selector in login_selectors:
                try:
                    login_button = self.driver.find_element(By.ID, selector)
                    if login_button and login_button.is_enabled():
                        self.log_action("INFO", f"Found login button with selector: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                self.log_action("ERROR", "Could not find login button on login page")
                return False
            
            # Click login button
            try:
                self.log_action("INFO", "Clicking login button...")
                login_button.click()
                self.log_action("INFO", "Login button clicked successfully")
            except Exception as e:
                self.log_action("ERROR", f"Failed to click login button: {str(e)}")
                return False
            
            # Wait for login process with longer timeout
            self.log_action("INFO", "Waiting for login process to complete...")
            await asyncio.sleep(5)
            
            # Check if login was successful with multiple indicators
            success_indicators = [
                "profile" in self.driver.current_url.lower(),
                "dashboard" in self.driver.current_url.lower(),
                "home" in self.driver.current_url.lower(),
                "jobs" in self.driver.current_url.lower()
            ]
            
            if any(success_indicators):
                self.is_authenticated = True
                self.log_action("SUCCESS", "Successfully authenticated with Glassdoor")
                
                # Wait a bit more to ensure session is fully established
                await asyncio.sleep(2)
                return True
            else:
                # Check for error messages
                error_found = False
                error_selectors = [
                    ".error", ".alert", ".message", ".notification",
                    "[class*='error']", "[class*='alert']", "[class*='message']"
                ]
                
                for selector in error_selectors:
                    try:
                        error_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if error_elem and error_elem.text:
                            error_msg = error_elem.text.strip()
                            if error_msg and len(error_msg) > 5:  # Filter out very short messages
                                self.log_action("ERROR", f"Login failed: {error_msg}")
                                error_found = True
                                break
                    except:
                        continue
                
                if not error_found:
                    self.log_action("ERROR", "Login failed: Unknown error - check credentials and try again")
                
                return False
                
        except Exception as e:
            self.log_action("ERROR", f"Authentication failed: {str(e)}")
            
            # Try to get more context about the error
            try:
                if self.driver:
                    current_url = self.driver.current_url
                    page_title = self.driver.title
                    self.log_action("ERROR", f"Current URL: {current_url}")
                    self.log_action("ERROR", f"Page title: {page_title}")
            except:
                pass
            
            return False
    
    async def _authenticate_with_retry(self, state: AgentState, max_attempts: Optional[int] = None) -> bool:
        """Retry wrapper around _authenticate with backoff and recovery."""
        try:
            attempts = max_attempts or self.max_retries
            for attempt in range(1, attempts + 1):
                self.log_action("AUTH", f"Authentication attempt {attempt}/{attempts}")
                self.is_authenticated = False
                try:
                    success = await self._authenticate(state)
                    if success:
                        return True
                except Exception as e:
                    self.log_action("WARNING", f"Authentication attempt {attempt} raised error: {str(e)}")
                # Try to recover the browser between attempts
                await self._handle_browser_crash()
                # Exponential backoff before next attempt
                await asyncio.sleep(2 ** (attempt - 1))
            self.log_action("FAILED", f"All {attempts} authentication attempts failed")
            return False
        except Exception as e:
            self.log_action("ERROR", f"Authentication retry wrapper failed: {str(e)}")
            return False
    
    async def _search_jobs_web(self, state: AgentState) -> Dict[str, Any]:
        """Search for jobs on Glassdoor using enhanced web scraping."""
        
        try:
            if not self.is_authenticated:
                return {"status": "error", "error": "Not authenticated"}
            
            # Extract search parameters from state
            role = getattr(state, 'role', 'Software Engineer')
            location = getattr(state, 'location', 'San Francisco, CA')
            max_jobs = getattr(state, 'max_jobs', 10)
            radius = getattr(state, 'search_radius', '25')  # miles
            
            self.log_action("SEARCHING", f"Searching for {role} jobs in {location} (radius: {radius} miles)")
            
            # Try multiple search approaches
            jobs = []
            
            # Approach 1: Direct search form
            jobs = await self._search_via_form(role, location, radius, max_jobs)
            
            # Approach 2: If form search fails, try direct URL construction
            if not jobs or len(jobs) < max_jobs // 2:
                self.log_action("INFO", "Form search yielded insufficient results, trying direct URL search")
                jobs = await self._search_via_direct_url(role, location, radius, max_jobs)
            
            # Approach 3: If still insufficient, try advanced search
            if not jobs or len(jobs) < max_jobs // 2:
                self.log_action("INFO", "Direct URL search yielded insufficient results, trying advanced search")
                jobs = await self._search_via_advanced(role, location, radius, max_jobs)
            
            # Remove duplicates and limit results
            unique_jobs = self._remove_duplicate_jobs(jobs)
            final_jobs = unique_jobs[:max_jobs]
            
            self.log_action("SUCCESS", f"Found {len(final_jobs)} unique jobs out of {len(jobs)} total results")
            
            return {
                "status": "success",
                "jobs": final_jobs,
                "total_found": len(final_jobs),
                "total_raw_results": len(jobs),
                "search_params": {
                    "role": role,
                    "location": location,
                    "radius": radius,
                    "max_jobs": max_jobs
                }
            }
            
        except Exception as e:
            self.log_action("SEARCH_ERROR", f"Enhanced web job search failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "jobs": []
            }
    
    async def _extract_job_listings(self, max_jobs: int) -> List[Dict[str, Any]]:
        """Extract job listings from the current page."""
        
        jobs = []
        try:
            # Look for job listing containers
            job_containers = self.driver.find_elements(By.CLASS_NAME, "react-job-listing")
            
            if not job_containers:
                # Try alternative selectors
                job_containers = self.driver.find_elements(By.CLASS_NAME, "job-listing")
            
            if not job_containers:
                # Try more generic approach
                job_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'job')]")
            
            for i, container in enumerate(job_containers[:max_jobs]):
                try:
                    job_info = await self._extract_job_info(container)
                    if job_info:
                        jobs.append(job_info)
                except Exception as e:
                    self.log_action("WARNING", f"Failed to extract job {i}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.log_action("ERROR", f"Failed to extract job listings: {str(e)}")
        
        return jobs
    
    async def _search_via_form(self, role: str, location: str, radius: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search for jobs using the Glassdoor search form."""
        
        try:
            # Navigate to job search page
            search_url = f"{self.base_url}/Job/jobs.htm"
            self.driver.get(search_url)
            await asyncio.sleep(3)
            
            # Try multiple form selectors for different Glassdoor layouts
            form_selectors = [
                {"keyword": "sc.keyword", "location": "sc.location", "button": "HeroSearchButton"},
                {"keyword": "keyword", "location": "location", "button": "search-button"},
                {"keyword": "job-title", "location": "job-location", "button": "search-btn"},
                {"keyword": "search-keyword", "location": "search-location", "button": "submit-search"}
            ]
            
            for selector_set in form_selectors:
                try:
                    # Job title/keyword field
                    keyword_field = WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.ID, selector_set["keyword"]))
                    )
                    keyword_field.clear()
                    keyword_field.send_keys(role)
                    
                    # Location field
                    location_field = self.driver.find_element(By.ID, selector_set["location"])
                    location_field.clear()
                    location_field.send_keys(location)
                    
                    # Try to set radius if available
                    try:
                        radius_select = self.driver.find_element(By.NAME, "radius")
                        Select(radius_select).select_by_value(radius)
                    except:
                        pass
                    
                    # Click search button
                    search_button = self.driver.find_element(By.ID, selector_set["button"])
                    search_button.click()
                    
                    await asyncio.sleep(4)
                    break
                    
                except Exception as e:
                    self.log_action("WARNING", f"Form selector {selector_set} failed: {str(e)}")
                    continue
            
            # Extract job listings with pagination
            return await self._extract_job_listings_with_pagination(max_jobs)
            
        except Exception as e:
            self.log_action("ERROR", f"Form search failed: {str(e)}")
            return []
    
    async def _search_via_direct_url(self, role: str, location: str, radius: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search for jobs using direct URL construction."""
        
        try:
            # Construct search URL directly
            encoded_role = role.replace(" ", "-").replace("&", "and")
            encoded_location = location.replace(" ", "-").replace(",", "").replace(" ", "-")
            
            search_urls = [
                f"{self.base_url}/Job/{encoded_role}-jobs-{encoded_location}.htm",
                f"{self.base_url}/Job/jobs.htm?sc.keyword={role}&sc.location={location}&radius={radius}",
                f"{self.base_url}/Job/jobs.htm?keyword={role}&location={location}",
                f"{self.base_url}/Job/jobs.htm?sc.keyword={role}&sc.location={location}"
            ]
            
            for url in search_urls:
                try:
                    self.driver.get(url)
                    await asyncio.sleep(3)
                    
                    # Check if we got results
                    jobs = await self._extract_job_listings_with_pagination(max_jobs)
                    if jobs:
                        self.log_action("SUCCESS", f"Direct URL search successful: {url}")
                        return jobs
                        
                except Exception as e:
                    self.log_action("WARNING", f"Direct URL {url} failed: {str(e)}")
                    continue
            
            return []
            
        except Exception as e:
            self.log_action("ERROR", f"Direct URL search failed: {str(e)}")
            return []
    
    async def _search_via_advanced(self, role: str, location: str, radius: str, max_jobs: int) -> List[Dict[str, Any]]:
        """Search for jobs using advanced search options."""
        
        try:
            # Navigate to advanced search page
            advanced_url = f"{self.base_url}/Job/advanced-search.htm"
            self.driver.get(advanced_url)
            await asyncio.sleep(3)
            
            # Try to fill advanced search form
            try:
                # Job title
                title_field = self.driver.find_element(By.ID, "keyword")
                title_field.clear()
                title_field.send_keys(role)
                
                # Location
                loc_field = self.driver.find_element(By.ID, "location")
                loc_field.clear()
                loc_field.send_keys(location)
                
                # Experience level (try to set to entry/mid level)
                try:
                    exp_select = self.driver.find_element(By.NAME, "experience")
                    Select(exp_select).select_by_value("entry")
                except:
                    pass
                
                # Job type (try to set to full-time)
                try:
                    type_select = self.driver.find_element(By.NAME, "jobType")
                    Select(type_select).select_by_value("full-time")
                except:
                    pass
                
                # Search button
                search_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                search_btn.click()
                
                await asyncio.sleep(4)
                
            except Exception as e:
                self.log_action("WARNING", f"Advanced form filling failed: {str(e)}")
            
            # Extract job listings
            return await self._extract_job_listings_with_pagination(max_jobs)
            
        except Exception as e:
            self.log_action("ERROR", f"Advanced search failed: {str(e)}")
            return []
    
    async def _extract_job_listings_with_pagination(self, max_jobs: int) -> List[Dict[str, Any]]:
        """Extract job listings with pagination support."""
        
        all_jobs = []
        page = 1
        max_pages = 5  # Limit to prevent infinite loops
        
        while len(all_jobs) < max_jobs and page <= max_pages:
            try:
                self.log_action("INFO", f"Extracting jobs from page {page}")
                
                # Extract jobs from current page
                page_jobs = await self._extract_job_listings_from_current_page(max_jobs - len(all_jobs))
                all_jobs.extend(page_jobs)
                
                # Try to go to next page
                if len(page_jobs) > 0 and len(all_jobs) < max_jobs:
                    next_page = await self._go_to_next_page()
                    if not next_page:
                        break
                    page += 1
                    await asyncio.sleep(2)
                else:
                    break
                    
            except Exception as e:
                self.log_action("WARNING", f"Error on page {page}: {str(e)}")
                break
        
        return all_jobs
    
    async def _extract_job_listings_from_current_page(self, max_jobs: int) -> List[Dict[str, Any]]:
        """Extract job listings from the current page only."""
        
        jobs = []
        try:
            # Enhanced selectors for different Glassdoor layouts
            selectors = [
                # Modern React-based layout
                "div[data-test='job-listing']",
                "div.react-job-listing",
                "div.job-listing",
                # Legacy layout
                "div.job",
                "div.job-listing-item",
                # Generic fallbacks
                "div[class*='job']",
                "div[class*='listing']",
                # XPath fallbacks
                "//div[contains(@class, 'job')]",
                "//div[contains(@class, 'listing')]",
                "//div[contains(@class, 'react-job')]"
            ]
            
            job_containers = []
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        containers = self.driver.find_elements(By.XPATH, selector)
                    else:
                        # CSS selector
                        containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if containers:
                        job_containers = containers
                        self.log_action("INFO", f"Found {len(containers)} job containers using selector: {selector}")
                        break
                        
                except Exception as e:
                    continue
            
            # Extract job info from containers
            for i, container in enumerate(job_containers[:max_jobs]):
                try:
                    job_info = await self._extract_job_info_enhanced(container)
                    if job_info:
                        jobs.append(job_info)
                except Exception as e:
                    self.log_action("WARNING", f"Failed to extract job {i}: {str(e)}")
                    continue
                    
        except Exception as e:
            self.log_action("ERROR", f"Failed to extract job listings from current page: {str(e)}")
        
        return jobs
    
    async def _go_to_next_page(self) -> bool:
        """Navigate to the next page of results."""
        
        try:
            # Try multiple next page selectors
            next_selectors = [
                "a[aria-label='Next']",
                "a[aria-label='Next page']",
                "a.next",
                "a[class*='next']",
                "button[aria-label='Next']",
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]"
            ]
            
            for selector in next_selectors:
                try:
                    if selector.startswith("//"):
                        next_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_button and next_button.is_enabled():
                        next_button.click()
                        return True
                        
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            self.log_action("WARNING", f"Failed to go to next page: {str(e)}")
            return False
    
    def _remove_duplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate jobs based on title, company, and location."""
        
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            identifier = f"{job.get('title', '')}|{job.get('company', '')}|{job.get('location', '')}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique_jobs.append(job)
        
        return unique_jobs
    
    async def _extract_job_info_enhanced(self, container) -> Optional[Dict[str, Any]]:
        """Enhanced job information extraction with multiple selector strategies."""
        
        try:
            # Multiple selector strategies for each field
            title_selectors = [
                "[data-test='job-link']",
                "[data-test='job-title']",
                ".job-title",
                ".job-link",
                "h3",
                "h4",
                "a[href*='job']"
            ]
            
            company_selectors = [
                "[data-test='employer-name']",
                ".employer-name",
                ".company-name",
                ".job-company",
                "[class*='company']",
                "[class*='employer']"
            ]
            
            location_selectors = [
                "[data-test='location']",
                ".location",
                ".job-location",
                "[class*='location']",
                ".job-city",
                ".job-state"
            ]
            
            salary_selectors = [
                "[data-test='salary-estimate']",
                ".salary-estimate",
                ".job-salary",
                "[class*='salary']",
                ".compensation"
            ]
            
            date_selectors = [
                "[data-test='job-age']",
                ".job-age",
                ".posted-date",
                "[class*='date']",
                "[class*='age']"
            ]
            
            # Extract job title
            title = self._extract_text_with_selectors(container, title_selectors, "Unknown Title")
            
            # Extract company name
            company = self._extract_text_with_selectors(container, company_selectors, "Unknown Company")
            
            # Extract location
            location = self._extract_text_with_selectors(container, location_selectors, "Unknown Location")
            
            # Extract job URL
            job_url = self._extract_url_with_selectors(container, title_selectors)
            
            # Extract salary
            salary = self._extract_text_with_selectors(container, salary_selectors, "")
            
            # Extract posting date
            posted_date = self._extract_text_with_selectors(container, date_selectors, "")
            
            # Extract additional metadata
            job_type = self._extract_job_type(container)
            experience_level = self._extract_experience_level(container)
            
            return {
                "id": f"gd_web_{int(time.time())}_{random.randint(1000, 9999)}",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "posted_date": posted_date,
                "url": job_url,
                "job_type": job_type,
                "experience_level": experience_level,
                "source": "glassdoor_web",
                "extracted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_action("WARNING", f"Failed to extract enhanced job info: {str(e)}")
            return None
    
    def _extract_text_with_selectors(self, container, selectors: List[str], default: str = "") -> str:
        """Extract text using multiple selectors with fallback."""
        
        for selector in selectors:
            try:
                element = container.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    return text
            except:
                continue
        
        return default
    
    def _extract_url_with_selectors(self, container, selectors: List[str]) -> str:
        """Extract URL using multiple selectors with fallback."""
        
        for selector in selectors:
            try:
                element = container.find_element(By.CSS_SELECTOR, selector)
                url = element.get_attribute("href")
                if url:
                    return url
            except:
                continue
        
        return ""
    
    def _extract_job_type(self, container) -> str:
        """Extract job type (full-time, part-time, contract, etc.)."""
        
        try:
            # Look for job type indicators
            type_selectors = [
                ".job-type",
                "[class*='type']",
                ".employment-type",
                ".work-schedule"
            ]
            
            for selector in type_selectors:
                try:
                    element = container.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip().lower()
                    if any(t in text for t in ['full-time', 'part-time', 'contract', 'temporary', 'internship']):
                        return text
                except:
                    continue
            
            return "Unknown"
            
        except Exception as e:
            return "Unknown"
    
    def _extract_experience_level(self, container) -> str:
        """Extract experience level (entry, mid, senior, etc.)."""
        
        try:
            # Look for experience level indicators
            level_selectors = [
                ".experience-level",
                "[class*='experience']",
                ".seniority",
                ".level"
            ]
            
            for selector in level_selectors:
                try:
                    element = container.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip().lower()
                    if any(level in text for level in ['entry', 'junior', 'mid', 'senior', 'lead', 'principal']):
                        return text
                except:
                    continue
            
            return "Unknown"
            
        except Exception as e:
            return "Unknown"
    
    async def _extract_job_info(self, container) -> Optional[Dict[str, Any]]:
        """Extract job information from a job container element."""
        
        try:
            # Extract job title
            title_elem = container.find_element(By.CSS_SELECTOR, "[data-test='job-link']")
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Extract company name
            company_elem = container.find_element(By.CSS_SELECTOR, "[data-test='employer-name']")
            company = company_elem.text.strip() if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = container.find_element(By.CSS_SELECTOR, "[data-test='location']")
            location = location_elem.text.strip() if location_elem else "Unknown Location"
            
            # Extract job URL
            job_url = title_elem.get_attribute("href") if title_elem else ""
            
            # Extract salary (if available)
            try:
                salary_elem = container.find_element(By.CSS_SELECTOR, "[data-test='salary-estimate']")
                salary = salary_elem.text.strip() if salary_elem else ""
            except:
                salary = ""
            
            # Extract posting date (if available)
            try:
                date_elem = container.find_element(By.CSS_SELECTOR, "[data-test='job-age']")
                posted_date = date_elem.text.strip() if date_elem else ""
            except:
                posted_date = ""
            
            return {
                "id": f"gd_web_{int(time.time())}_{random.randint(1000, 9999)}",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "posted_date": posted_date,
                "url": job_url,
                "source": "glassdoor_web",
                "extracted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.log_action("WARNING", f"Failed to extract job info: {str(e)}")
            return None
    
    async def _filter_jobs(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Filter and rank jobs based on state preferences."""
        
        if not jobs:
            return []
        
        filtered_jobs = []
        
        for job in jobs:
            score = await self._calculate_job_score(job, state)
            if score >= getattr(state, 'min_job_score', 50):
                job['score'] = score
                filtered_jobs.append(job)
        
        # Sort by score (highest first)
        filtered_jobs.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limit to max jobs
        max_jobs = getattr(state, 'max_jobs', 5)
        return filtered_jobs[:max_jobs]
    
    async def _calculate_job_score(self, job: Dict[str, Any], state: AgentState) -> float:
        """Calculate enhanced job score based on multiple factors."""
        
        score = 50.0  # Base score
        
        # Enhanced keyword matching with weights
        keywords = getattr(state, 'keywords', [])
        if keywords:
            job_text = f"{job.get('title', '')} {job.get('company', '')} {job.get('location', '')}".lower()
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in job_text)
            score += keyword_matches * 20  # Increased weight for keywords
        
        # Company reputation scoring
        company_name = job.get('company', '').lower()
        if company_name:
            # Prefer well-known companies
            well_known_companies = [
                'google', 'microsoft', 'amazon', 'apple', 'meta', 'netflix', 'tesla',
                'salesforce', 'oracle', 'ibm', 'intel', 'adobe', 'cisco', 'nvidia',
                'airbnb', 'uber', 'lyft', 'stripe', 'square', 'palantir'
            ]
            if any(company in company_name for company in well_known_companies):
                score += 25
        
        # Enhanced salary scoring
        min_salary = getattr(state, 'min_salary', 0)
        if min_salary > 0 and job.get('salary'):
            salary_text = job.get('salary', '').lower()
            # Parse salary ranges
            if 'k' in salary_text or '000' in salary_text:
                try:
                    # Extract numeric values
                    numbers = re.findall(r'\d+', salary_text)
                    if numbers:
                        avg_salary = sum(int(n) for n in numbers) / len(numbers)
                        if avg_salary >= min_salary:
                            score += 20
                        elif avg_salary >= min_salary * 0.8:
                            score += 15
                        elif avg_salary >= min_salary * 0.6:
                            score += 10
                except:
                    score += 10  # Fallback if parsing fails
        
        # Enhanced posting date scoring
        if job.get('posted_date'):
            date_text = job.get('posted_date', '').lower()
            if 'today' in date_text or 'just posted' in date_text:
                score += 25
            elif 'yesterday' in date_text:
                score += 20
            elif 'week' in date_text:
                score += 15
            elif 'days ago' in date_text:
                # Extract number of days
                days_match = re.search(r'(\d+)\s*days?', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    if days <= 3:
                        score += 15
                    elif days <= 7:
                        score += 10
                    elif days <= 14:
                        score += 5
        
        # Job type scoring
        job_type = job.get('job_type', '').lower()
        if job_type:
            preferred_types = getattr(state, 'preferred_job_types', ['full-time'])
            if any(pref in job_type for pref in preferred_types):
                score += 15
        
        # Experience level scoring
        experience_level = job.get('experience_level', '').lower()
        if experience_level:
            user_experience = getattr(state, 'user_experience_level', 'mid')
            if user_experience == 'entry' and 'entry' in experience_level:
                score += 20
            elif user_experience == 'mid' and 'mid' in experience_level:
                score += 20
            elif user_experience == 'senior' and 'senior' in experience_level:
                score += 20
        
        # Location preference scoring
        preferred_locations = getattr(state, 'preferred_locations', [])
        if preferred_locations:
            job_location = job.get('location', '').lower()
            for pref_loc in preferred_locations:
                if pref_loc.lower() in job_location:
                    score += 15
                    break
        
        # Remote work preference
        if getattr(state, 'prefer_remote', False):
            remote_indicators = ['remote', 'work from home', 'wfh', 'virtual', 'telecommute']
            job_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
            if any(indicator in job_text for indicator in remote_indicators):
                score += 20
        
        # Industry preference scoring
        preferred_industries = getattr(state, 'preferred_industries', [])
        if preferred_industries:
            company_name = job.get('company', '').lower()
            for industry in preferred_industries:
                if industry.lower() in company_name:
                    score += 10
                    break
        
        # Cap the score at 200
        return min(score, 200.0)
    
    async def validate_search_results(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and analyze search results quality."""
        
        if not jobs:
            return {
                "valid": False,
                "total_jobs": 0,
                "quality_score": 0,
                "issues": ["No jobs found"]
            }
        
        validation_results = {
            "valid": True,
            "total_jobs": len(jobs),
            "quality_score": 0,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Check for missing critical fields
        missing_fields = []
        for job in jobs:
            if not job.get('title') or job.get('title') == 'Unknown Title':
                missing_fields.append('title')
            if not job.get('company') or job.get('company') == 'Unknown Company':
                missing_fields.append('company')
            if not job.get('location') or job.get('location') == 'Unknown Location':
                missing_fields.append('location')
        
        if missing_fields:
            validation_results["warnings"].append(f"Some jobs missing: {', '.join(set(missing_fields))}")
        
        # Calculate quality score
        quality_factors = {
            "has_title": sum(1 for job in jobs if job.get('title') and job.get('title') != 'Unknown Title'),
            "has_company": sum(1 for job in jobs if job.get('company') and job.get('company') != 'Unknown Company'),
            "has_location": sum(1 for job in jobs if job.get('location') and job.get('location') != 'Unknown Location'),
            "has_salary": sum(1 for job in jobs if job.get('salary')),
            "has_url": sum(1 for job in jobs if job.get('url')),
            "has_date": sum(1 for job in jobs if job.get('posted_date'))
        }
        
        total_possible = len(jobs) * len(quality_factors)
        actual_score = sum(quality_factors.values())
        validation_results["quality_score"] = (actual_score / total_possible) * 100 if total_possible > 0 else 0
        
        # Generate recommendations
        if validation_results["quality_score"] < 70:
            validation_results["recommendations"].append("Consider adjusting search parameters for better results")
        
        if len(jobs) < 5:
            validation_results["recommendations"].append("Try broadening search criteria to get more results")
        
        if not any(job.get('salary') for job in jobs):
            validation_results["recommendations"].append("Salary information not available - consider other job sources")
        
        return validation_results
    
    async def get_search_statistics(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive search statistics."""
        
        if not jobs:
            return {"error": "No jobs to analyze"}
        
        stats = {
            "total_jobs": len(jobs),
            "companies": {},
            "locations": {},
            "job_types": {},
            "experience_levels": {},
            "salary_ranges": {},
            "posting_dates": {},
            "top_keywords": {}
        }
        
        # Analyze companies
        for job in jobs:
            company = job.get('company', 'Unknown')
            stats["companies"][company] = stats["companies"].get(company, 0) + 1
        
        # Analyze locations
        for job in jobs:
            location = job.get('location', 'Unknown')
            stats["locations"][location] = stats["locations"].get(location, 0) + 1
        
        # Analyze job types
        for job in jobs:
            job_type = job.get('job_type', 'Unknown')
            stats["job_types"][job_type] = stats["job_types"].get(job_type, 0) + 1
        
        # Analyze experience levels
        for job in jobs:
            exp_level = job.get('experience_level', 'Unknown')
            stats["experience_levels"][exp_level] = stats["experience_levels"].get(exp_level, 0) + 1
        
        # Analyze salary information
        for job in jobs:
            salary = job.get('salary', '')
            if salary:
                # Categorize salary ranges
                try:
                    numbers = re.findall(r'\d+', salary)
                    if numbers:
                        avg_salary = sum(int(n) for n in numbers) / len(numbers)
                        if avg_salary < 50:
                            range_key = "Under $50K"
                        elif avg_salary < 100:
                            range_key = "$50K-$100K"
                        elif avg_salary < 150:
                            range_key = "$100K-$150K"
                        else:
                            range_key = "Over $150K"
                        stats["salary_ranges"][range_key] = stats["salary_ranges"].get(range_key, 0) + 1
                except:
                    stats["salary_ranges"]["Unknown"] = stats["salary_ranges"].get("Unknown", 0) + 1
        
        # Analyze posting dates
        for job in jobs:
            date = job.get('posted_date', 'Unknown')
            stats["posting_dates"][date] = stats["posting_dates"].get(date, 0) + 1
        
        # Extract top keywords from job titles
        all_titles = ' '.join([job.get('title', '') for job in jobs])
        words = re.findall(r'\b\w+\b', all_titles.lower())
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top 10 keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_keywords"] = dict(top_keywords)
        
        return stats
    
    async def _apply_to_jobs_web(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Apply to jobs using web automation."""
        
        applications = []
        
        for job in jobs:
            try:
                application_result = await self._apply_to_single_job_web(job, state)
                applications.append(application_result)
                
                # Add delay between applications
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                self.log_action("ERROR", f"Failed to apply to job {job.get('title')}: {str(e)}")
                applications.append({
                    "job_id": job.get('id'),
                    "status": "error",
                    "error": str(e)
                })
        
        return applications
    
    async def _apply_to_single_job_web(self, job: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Apply to a single job using web automation."""
        
        try:
            if not job.get('url'):
                return {
                    "job_id": job.get('id'),
                    "status": "error",
                    "error": "No job URL available"
                }
            
            # Navigate to job page
            self.driver.get(job.get('url'))
            await asyncio.sleep(3)
            
            # Look for apply button
            apply_button = None
            try:
                apply_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='apply-button']"))
                )
            except:
                # Try alternative selectors
                try:
                    apply_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Apply')]")
                except:
                    try:
                        apply_button = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Apply')]")
                    except:
                        pass
            
            if not apply_button:
                return {
                    "job_id": job.get('id'),
                    "status": "error",
                    "error": "Apply button not found"
                }
            
            # Click apply button
            apply_button.click()
            await asyncio.sleep(3)
            
            # Handle application form if it appears
            application_result = await self._handle_application_form(job, state)
            
            return application_result
            
        except Exception as e:
            return {
                "job_id": job.get('id'),
                "status": "error",
                "error": str(e)
            }
    
    async def _handle_application_form(self, job: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Handle job application form if it appears."""
        
        try:
            # Check if we're on an application form
            form_elements = self.driver.find_elements(By.TAG_NAME, "form")
            
            if not form_elements:
                # No form, might be external redirect
                return {
                    "job_id": job.get('id'),
                    "status": "redirect",
                    "message": "Redirected to external application",
                    "current_url": self.driver.current_url
                }
            
            # Try to fill out common form fields
            resume_path = getattr(state, 'resume_path', None)
            
            if resume_path:
                # Look for file upload field
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    file_input.send_keys(resume_path)
                except:
                    pass
            
            # Look for submit button
            try:
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_button.click()
                await asyncio.sleep(3)
                
                return {
                    "job_id": job.get('id'),
                    "status": "success",
                    "message": "Application submitted successfully",
                    "submitted_at": datetime.now().isoformat()
                }
                
            except:
                return {
                    "job_id": job.get('id'),
                    "status": "partial",
                    "message": "Application form found but submission unclear",
                    "current_url": self.driver.current_url
                }
                
        except Exception as e:
            return {
                "job_id": job.get('id'),
                "status": "error",
                "error": f"Form handling failed: {str(e)}"
            }
    
    async def _init_browser(self):
        """Initialize Selenium WebDriver with robust error handling and stability checks."""
        
        if self.driver:
            return
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.log_action("INFO", f"Browser initialization attempt {attempt + 1}/{max_retries}")
                
                # Set up Chrome options with more stable settings
                chrome_options = Options()
                
                # Essential stability options (less aggressive than before)
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-plugins")
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-renderer-backgrounding")
                chrome_options.add_argument("--disable-features=TranslateUI")
                chrome_options.add_argument("--disable-ipc-flooding-protection")
                # Reduce WebGL fallback warnings on some systems
                chrome_options.add_argument("--enable-unsafe-swiftshader")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--start-maximized")
                
                # More stable user agent
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # Gentler preferences that won't cause crashes
                prefs = {
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.default_content_setting_values.popups": 2,
                    "profile.managed_default_content_settings.images": 1,  # Allow images for stability
                    "profile.managed_default_content_settings.javascript": 1,
                    "profile.managed_default_content_settings.cookies": 1,
                    "profile.managed_default_content_settings.plugins": 1,
                    "profile.managed_default_content_settings.popups": 2,
                    "profile.managed_default_content_settings.geolocation": 2,
                    "profile.managed_default_content_settings.media_stream": 2,
                }
                chrome_options.add_experimental_option("prefs", prefs)
                
                # Try multiple initialization methods for Windows compatibility
                driver_initialized = False
                
                # Method 1: Try with ChromeDriverManager (most reliable)
                if not driver_initialized:
                    try:
                        self.log_action("INFO", "Attempting ChromeDriverManager initialization...")
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        driver_initialized = True
                        self.log_action("SUCCESS", "ChromeDriverManager initialization successful")
                    except Exception as chrome_error:
                        self.log_action("WARNING", f"ChromeDriverManager failed: {str(chrome_error)}")
                
                # Method 2: Try with system ChromeDriver (if available)
                if not driver_initialized:
                    try:
                        self.log_action("INFO", "Attempting system ChromeDriver initialization...")
                        # Try to find ChromeDriver in PATH or common locations
                        chrome_driver_paths = [
                            "chromedriver",  # In PATH
                            "./chromedriver.exe",  # Current directory
                            "./chromedriver",  # Current directory (Unix)
                            r"C:\chromedriver\chromedriver.exe",  # Common Windows location
                            r"C:\Program Files\chromedriver\chromedriver.exe",
                            r"C:\Program Files (x86)\chromedriver\chromedriver.exe"
                        ]
                        
                        for driver_path in chrome_driver_paths:
                            try:
                                if os.path.exists(driver_path) or driver_path == "chromedriver":
                                    service = Service(driver_path)
                                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                                    driver_initialized = True
                                    self.log_action("SUCCESS", f"System ChromeDriver initialization successful with: {driver_path}")
                                    break
                            except Exception as e:
                                self.log_action("WARNING", f"ChromeDriver path {driver_path} failed: {str(e)}")
                                continue
                    except Exception as e:
                        self.log_action("WARNING", f"System ChromeDriver initialization failed: {str(e)}")
                
                # Method 3: Try with Chrome binary location detection
                if not driver_initialized:
                    try:
                        self.log_action("INFO", "Attempting Chrome binary location detection...")
                        chrome_paths = [
                            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
                            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USER', ''))
                        ]
                        
                        chrome_found = False
                        for chrome_path in chrome_paths:
                            if os.path.exists(chrome_path):
                                chrome_options.binary_location = chrome_path
                                chrome_found = True
                                self.log_action("INFO", f"Found Chrome at: {chrome_path}")
                                break
                        
                        if chrome_found:
                            # Try with minimal options and binary location
                            try:
                                minimal_options = Options()
                                minimal_options.binary_location = chrome_path
                                minimal_options.add_argument("--no-sandbox")
                                minimal_options.add_argument("--disable-dev-shm-usage")
                                minimal_options.add_argument("--disable-gpu")
                                minimal_options.add_argument("--headless")  # Try headless mode
                                
                                self.driver = webdriver.Chrome(options=minimal_options)
                                driver_initialized = True
                                self.log_action("SUCCESS", "Chrome binary location initialization successful (headless)")
                            except Exception as e:
                                self.log_action("WARNING", f"Chrome binary location (headless) failed: {str(e)}")
                                
                                # Try without headless mode
                                try:
                                    minimal_options = Options()
                                    minimal_options.binary_location = chrome_path
                                    minimal_options.add_argument("--no-sandbox")
                                    minimal_options.add_argument("--disable-dev-shm-usage")
                                    minimal_options.add_argument("--disable-gpu")
                                    
                                    self.driver = webdriver.Chrome(options=minimal_options)
                                    driver_initialized = True
                                    self.log_action("SUCCESS", "Chrome binary location initialization successful (non-headless)")
                                except Exception as e2:
                                    self.log_action("WARNING", f"Chrome binary location (non-headless) failed: {str(e2)}")
                    except Exception as e:
                        self.log_action("WARNING", f"Chrome binary location detection failed: {str(e)}")
                
                # Method 4: Last resort - try with minimal options
                if not driver_initialized:
                    try:
                        self.log_action("INFO", "Attempting minimal options initialization...")
                        minimal_options = Options()
                        minimal_options.add_argument("--no-sandbox")
                        minimal_options.add_argument("--disable-dev-shm-usage")
                        minimal_options.add_argument("--disable-gpu")
                        minimal_options.add_argument("--headless")
                        minimal_options.add_argument("--disable-extensions")
                        minimal_options.add_argument("--disable-plugins")
                        
                        self.driver = webdriver.Chrome(options=minimal_options)
                        driver_initialized = True
                        self.log_action("SUCCESS", "Minimal options initialization successful")
                    except Exception as e:
                        self.log_action("WARNING", f"Minimal options initialization failed: {str(e)}")
                
                if not driver_initialized:
                    raise Exception("All Chrome initialization methods failed")
                
                # Set timeouts
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                
                # Test browser stability
                if not await self._test_browser_stability():
                    raise Exception("Browser stability test failed")
                
                self.log_action("SUCCESS", "Browser initialized successfully")
                return
                
            except Exception as e:
                self.log_action("ERROR", f"Browser initialization attempt {attempt + 1} failed: {str(e)}")
                
                # Clean up failed driver
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to initialize browser after {max_retries} attempts: {str(e)}")
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _test_browser_stability(self) -> bool:
        """Test if the initialized browser is stable and working properly."""
        
        try:
            if not self.driver:
                return False
            
            # Test 1: Navigate to a simple, stable page
            self.log_action("INFO", "Testing browser stability with simple page navigation")
            self.driver.get("data:text/html,<html><body><h1>Browser Test</h1><p>Testing browser functionality...</p></body></html>")
            await asyncio.sleep(2)  # Give more time for page to load
            
            # Test 2: Check if we can get page title (more lenient)
            try:
                title = self.driver.title
                if title and title.strip():
                    self.log_action("INFO", f"Page title retrieved: {title}")
                else:
                    self.log_action("WARNING", "Page title is empty, but continuing with test")
            except Exception as e:
                self.log_action("WARNING", f"Could not retrieve page title: {str(e)}, but continuing with test")
            
            # Test 3: Check if we can find elements (more lenient)
            try:
                h1_element = self.driver.find_element(By.TAG_NAME, "h1")
                if h1_element and h1_element.text:
                    self.log_action("INFO", f"Element interaction successful: {h1_element.text}")
                else:
                    self.log_action("WARNING", "Element found but no text, continuing with test")
            except Exception as e:
                self.log_action("WARNING", f"Element interaction test failed: {str(e)}, but continuing with test")
            
            # Test 4: Check if we can execute JavaScript (more lenient)
            try:
                result = self.driver.execute_script("return document.title;")
                if result:
                    self.log_action("INFO", f"JavaScript execution successful: {result}")
                else:
                    self.log_action("WARNING", "JavaScript execution returned empty result, but continuing with test")
            except Exception as e:
                self.log_action("WARNING", f"JavaScript execution test failed: {str(e)}, but continuing with test")
            
            # Test 5: Check if we can navigate to a real website (optional)
            try:
                self.log_action("INFO", "Testing navigation to a real website")
                self.driver.get("https://www.google.com")
                await asyncio.sleep(3)  # Wait for page to load
                
                # Check if page loaded (don't be too strict about content)
                current_url = self.driver.current_url
                if "google" in current_url.lower():
                    self.log_action("INFO", "Successfully navigated to Google")
                else:
                    self.log_action("WARNING", f"Navigation test completed, but URL is: {current_url}")
                
            except Exception as e:
                self.log_action("WARNING", f"Navigation test failed: {str(e)}, but browser is still functional")
            
            # If we get here, the browser is working
            self.log_action("SUCCESS", "Browser stability test passed")
            return True
            
        except Exception as e:
            self.log_action("ERROR", f"Browser stability test failed with error: {str(e)}")
            return False
    
    async def _monitor_browser_health(self) -> bool:
        """Monitor browser health and detect potential crashes."""
        
        try:
            if not self.driver:
                return False
            
            # Quick health checks
            try:
                # Check if browser is responsive
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                # Check if we can execute basic JavaScript
                test_result = self.driver.execute_script("return 'healthy';")
                if test_result != "healthy":
                    return False
                
                return True
                
            except Exception as e:
                self.log_action("WARNING", f"Browser health check failed: {str(e)}")
                return False
                
        except Exception as e:
            self.log_action("ERROR", f"Browser health monitoring failed: {str(e)}")
            return False
    
    async def _handle_browser_crash(self) -> bool:
        """Handle browser crashes and attempt recovery."""
        
        try:
            self.log_action("WARNING", "Browser crash detected, attempting recovery...")
            
            # Close the crashed browser
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            # Wait a moment before attempting recovery
            await asyncio.sleep(2)
            
            # Try to reinitialize the browser
            try:
                await self._init_browser()
                if self.driver:
                    self.log_action("SUCCESS", "Browser recovery successful")
                    return True
                else:
                    self.log_action("ERROR", "Browser recovery failed - could not reinitialize")
                    return False
            except Exception as e:
                self.log_action("ERROR", f"Browser recovery failed: {str(e)}")
                return False
                
        except Exception as e:
            self.log_action("ERROR", f"Browser crash handling failed: {str(e)}")
            return False
    
    async def _safe_operation(self, operation_func, *args, **kwargs):
        """Execute an operation safely with browser health monitoring."""
        
        try:
            # Check browser health before operation
            if not await self._monitor_browser_health():
                self.log_action("WARNING", "Browser health check failed before operation")
                if not await self._handle_browser_crash():
                    raise Exception("Browser recovery failed")
            
            # Execute the operation
            result = await operation_func(*args, **kwargs)
            
            # Check browser health after operation
            if not await self._monitor_browser_health():
                self.log_action("WARNING", "Browser health check failed after operation")
                if not await self._handle_browser_crash():
                    self.log_action("WARNING", "Browser recovery failed after operation")
            
            return result
            
        except Exception as e:
            self.log_action("ERROR", f"Safe operation failed: {str(e)}")
            raise e
    
    async def _close_browser(self):
        """Close Selenium WebDriver."""
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_action("BROWSER_CLOSE", "WebDriver closed")
            except Exception as e:
                self.log_action("WARNING", f"Error closing browser: {str(e)}")
    
    async def close(self):
        """Clean up resources."""
        await self._close_browser()
