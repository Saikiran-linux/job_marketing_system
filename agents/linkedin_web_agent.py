"""
LinkedIn Web Agent - Authenticates and scrapes jobs using email/password instead of API tokens.
"""

import asyncio
import time
import random
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
import os

class LinkedInWebAgent(BaseAgent):
    """Agent for searching and applying to jobs on LinkedIn using web automation."""
    
    def __init__(self):
        super().__init__("LinkedInWebAgent")
        self.base_url = "https://www.linkedin.com"
        self.driver = None
        self.logger = setup_logger("LinkedInWebAgent")
        self.is_authenticated = False
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute LinkedIn job search and application workflow using web automation."""
        
        try:
            self.log_action("STARTING", "Starting LinkedIn web-based job search")
            
            # Step 1: Authenticate with LinkedIn
            if not await self._authenticate(state):
                state.error = "Failed to authenticate with LinkedIn"
                return state
            
            # Step 2: Search for jobs
            job_search_results = await self._search_jobs_web(state)
            if job_search_results.get("status") == "success":
                state.linkedin_jobs = job_search_results.get("jobs", [])
                state.steps_completed.append("linkedin_search")
                self.log_action("SUCCESS", f"Found {len(state.linkedin_jobs)} jobs on LinkedIn")
            else:
                state.error = f"LinkedIn job search failed: {job_search_results.get('error', 'Unknown error')}"
                return state
            
            # Step 3: Filter and rank jobs
            filtered_jobs = await self._filter_jobs(state.linkedin_jobs, state)
            state.filtered_linkedin_jobs = filtered_jobs
            state.steps_completed.append("linkedin_filtering")
            
            # Step 4: Apply to selected jobs (if auto-apply is enabled)
            if state.auto_apply and filtered_jobs:
                application_results = await self._apply_to_jobs_web(filtered_jobs, state)
                state.linkedin_applications = application_results
                state.steps_completed.append("linkedin_applications")
            
            self.log_action("COMPLETE", "LinkedIn web workflow completed successfully")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"LinkedIn web workflow failed: {str(e)}")
            state.error = f"LinkedIn web error: {str(e)}"
            return state
        finally:
            await self._close_browser()
    
    async def _authenticate(self, state: AgentState) -> bool:
        """Authenticate with LinkedIn using email and password."""
        
        try:
            # Get credentials from state or config
            email = getattr(state, 'linkedin_email', None) or Config.LINKEDIN_EMAIL
            password = getattr(state, 'linkedin_password', None) or Config.LINKEDIN_PASSWORD
            
            if not email or not password:
                self.log_action("ERROR", "LinkedIn credentials not provided")
                return False
            
            # Initialize browser
            await self._init_browser()
            
            # Navigate to LinkedIn login page
            self.driver.get(f"{self.base_url}/login")
            await asyncio.sleep(2)
            
            # Find and fill email field
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_field.clear()
            email_field.send_keys(email)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for successful login
            await asyncio.sleep(5)
            
            # Check if login was successful
            if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                self.is_authenticated = True
                self.log_action("SUCCESS", "Successfully authenticated with LinkedIn")
                return True
            else:
                # Check for error messages
                try:
                    error_elem = self.driver.find_element(By.CLASS_NAME, "alert-error")
                    error_msg = error_elem.text
                    self.log_action("ERROR", f"Login failed: {error_msg}")
                except:
                    self.log_action("ERROR", "Login failed: Unknown error")
                return False
                
        except Exception as e:
            self.log_action("ERROR", f"Authentication failed: {str(e)}")
            return False
    
    async def _search_jobs_web(self, state: AgentState) -> Dict[str, Any]:
        """Search for jobs on LinkedIn using web scraping."""
        
        try:
            if not self.is_authenticated:
                return {"status": "error", "error": "Not authenticated"}
            
            # Extract search parameters from state
            role = getattr(state, 'role', 'Software Engineer')
            location = getattr(state, 'location', 'San Francisco, CA')
            max_jobs = getattr(state, 'max_jobs', 5)
            
            self.log_action("SEARCHING", f"Searching for {role} jobs in {location}")
            
            # Navigate to LinkedIn jobs page
            search_url = f"{self.base_url}/jobs"
            self.driver.get(search_url)
            await asyncio.sleep(3)
            
            # Fill in job search form
            try:
                # Job title/keyword field
                keyword_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label*='Search by title']"))
                )
                keyword_field.clear()
                keyword_field.send_keys(role)
                
                # Location field
                location_field = self.driver.find_element(By.CSS_SELECTOR, "input[aria-label*='City']")
                location_field.clear()
                location_field.send_keys(location)
                
                # Click search button
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Search']")
                search_button.click()
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.log_action("WARNING", f"Could not fill search form: {str(e)}")
                # Continue with current page if form filling fails
        
            # Extract job listings
            jobs = await self._extract_job_listings(max_jobs)
            
            return {
                "status": "success",
                "jobs": jobs,
                "total_found": len(jobs),
                "search_params": {
                    "role": role,
                    "location": location,
                    "max_jobs": max_jobs
                }
            }
            
        except Exception as e:
            self.log_action("SEARCH_ERROR", f"Web job search failed: {str(e)}")
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
            job_containers = self.driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
            
            if not job_containers:
                # Try alternative selectors
                job_containers = self.driver.find_elements(By.CSS_SELECTOR, "[data-job-id]")
            
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
    
    async def _extract_job_info(self, container) -> Optional[Dict[str, Any]]:
        """Extract job information from a job container element."""
        
        try:
            # Extract job title
            title_elem = container.find_element(By.CSS_SELECTOR, ".job-search-card__title")
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Extract company name
            company_elem = container.find_element(By.CSS_SELECTOR, ".job-search-card__subtitle")
            company = company_elem.text.strip() if company_elem else "Unknown Company"
            
            # Extract location
            location_elem = container.find_element(By.CSS_SELECTOR, ".job-search-card__location")
            location = location_elem.text.strip() if location_elem else "Unknown Location"
            
            # Extract job URL
            try:
                job_link = container.find_element(By.CSS_SELECTOR, "a")
                job_url = job_link.get_attribute("href") if job_link else ""
            except:
                job_url = ""
            
            # Extract salary (if available)
            try:
                salary_elem = container.find_element(By.CSS_SELECTOR, ".job-search-card__salary-info")
                salary = salary_elem.text.strip() if salary_elem else ""
            except:
                salary = ""
            
            # Extract posting date (if available)
            try:
                date_elem = container.find_element(By.CSS_SELECTOR, ".job-search-card__listdate")
                posted_date = date_elem.text.strip() if date_elem else ""
            except:
                posted_date = ""
            
            return {
                "id": f"li_web_{int(time.time())}_{random.randint(1000, 9999)}",
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "posted_date": posted_date,
                "url": job_url,
                "source": "linkedin_web",
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
        """Calculate job score based on various factors."""
        
        score = 50.0  # Base score
        
        # Keyword matching
        keywords = getattr(state, 'keywords', [])
        if keywords:
            job_text = f"{job.get('title', '')} {job.get('company', '')}".lower()
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in job_text)
            score += keyword_matches * 15
        
        # Salary filtering
        min_salary = getattr(state, 'min_salary', 0)
        if min_salary > 0 and job.get('salary'):
            # Simple salary parsing (would need enhancement for production)
            salary_text = job.get('salary', '').lower()
            if 'k' in salary_text or '000' in salary_text:
                score += 10
        
        # Recent posting bonus
        if job.get('posted_date'):
            if 'today' in job.get('posted_date', '').lower():
                score += 20
            elif 'yesterday' in job.get('posted_date', '').lower():
                score += 15
            elif 'week' in job.get('posted_date', '').lower():
                score += 10
        
        return score
    
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
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".jobs-apply-button"))
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
        """Initialize Selenium WebDriver with robust error handling and Windows compatibility."""
        
        if self.driver:
            return
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.log_action("INFO", f"Browser initialization attempt {attempt + 1}/{max_retries}")
                
                # Set up Chrome options with Windows-specific optimizations
                chrome_options = Options()
                
                # Windows-specific options
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--allow-running-insecure-content")
                chrome_options.add_argument("--disable-features=VizDisplayCompositor")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                # Disable images and CSS for faster loading
                prefs = {
                    "profile.managed_default_content_settings.images": 2,
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.default_content_setting_values.popups": 2
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
                
                # Set page load timeout
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                
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
