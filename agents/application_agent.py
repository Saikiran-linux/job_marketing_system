import asyncio
import os
import time
import json
from typing import Dict, Any, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from datetime import datetime
import openai
from openai import AsyncOpenAI
from agents.base_agent import BaseAgent, AgentState
# LinkedIn agent import removed - using web-based approach only
from config import Config
import re

class ApplicationAgent(BaseAgent):
    """Agent responsible for automatically applying to jobs."""
    
    def __init__(self):
        super().__init__("ApplicationAgent")
        self.driver = None
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        # LinkedIn agent removed - using web-based approach only
        self.application_count = 0
        self.daily_limit = Config.MAX_DAILY_APPLICATIONS
        self.application_history = []
    
    async def execute(self, state: AgentState) -> AgentState:
        """Apply to a job with the provided information."""
        
        try:
            # Check if we have job information in the state
            if not state.job_search_results:
                state.error = "No job information available for application"
                return state
            
            # Get current job details
            current_job = state.job_search_results.get("current_job", {})
            if not current_job:
                state.error = "No current job information for application"
                return state
            
            # Check if auto-apply is enabled
            if not state.auto_apply:
                self.log_action("INFO", "Auto-apply disabled, skipping application")
                state.steps_completed.append("application_skipped")
                state.current_step = "application_skipped"
                return state
            
            # Check daily application limit
            if self.application_count >= self.daily_limit:
                self.log_action("WARNING", f"Daily application limit ({self.daily_limit}) reached")
                state.error = f"Daily application limit ({self.daily_limit}) reached"
                return state
            
            # Get resume path (use modified resume if available)
            resume_path = state.resume_path
            if state.resume_modification and state.resume_modification.get("modified_resume_path"):
                resume_path = state.resume_modification["modified_resume_path"]
                self.log_action("INFO", f"Using modified resume: {resume_path}")
            
            # Perform job application
            application_result = await self.apply_to_job(
                current_job,
                resume_path,
                state.resume_analysis
            )
            
            if application_result.get("status") == "success":
                # Update application count and history
                self.application_count += 1
                self.application_history.append({
                    "job_id": current_job.get("id", ""),
                    "job_title": current_job.get("title", ""),
                    "company": current_job.get("company", ""),
                    "application_date": datetime.now().isoformat(),
                    "status": "submitted",
                    "resume_used": resume_path
                })
                
                # Update state
                state.steps_completed.append("application_submitted")
                state.current_step = "application_complete"
                state.application_result = application_result
                
                self.log_action("SUCCESS", f"Successfully applied to {current_job.get('title', 'Unknown')} at {current_job.get('company', 'Unknown')}")
                
            else:
                state.error = f"Application failed: {application_result.get('error', 'Unknown error')}"
                self.log_action("ERROR", f"Application failed: {application_result.get('error', 'Unknown error')}")
            
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Application execution failed: {str(e)}")
            state.error = f"Application execution failed: {str(e)}"
            return state
    
    async def apply_to_job(self, job_info: Dict[str, Any], 
                          resume_path: str, 
                          resume_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a specific job."""
        
        try:
            job_title = job_info.get("title", "")
            company_name = job_info.get("company", "")
            job_url = job_info.get("url", "")
            job_source = job_info.get("source", "").lower()
            
            self.log_action("APPLYING", f"Applying to {job_title} at {company_name} via {job_source}")
            
            # Generate cover letter
            cover_letter = await self.generate_cover_letter(
                job_info, resume_analysis, company_name
            )
            
            # Apply based on job source
            if "linkedin" in job_source:
                application_result = await self._apply_via_linkedin(
                    job_info, resume_path, cover_letter
                )
            elif "indeed" in job_source:
                application_result = await self._apply_via_indeed(
                    job_info, resume_path, cover_letter
                )
            else:
                # Generic application method
                application_result = await self._apply_generic(
                    job_info, resume_path, cover_letter
                )
            
            # Add metadata
            application_result.update({
                "job_title": job_title,
                "company_name": company_name,
                "job_source": job_source,
                "application_timestamp": datetime.now().isoformat(),
                "resume_used": resume_path,
                "cover_letter_generated": bool(cover_letter)
            })
            
            return application_result
            
        except Exception as e:
            self.log_action("ERROR", f"Job application failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "application_timestamp": datetime.now().isoformat()
            }
    
    async def generate_cover_letter(self, job_info: Dict[str, Any], 
                                  resume_analysis: Dict[str, Any], 
                                  company_name: str) -> str:
        """Generate a personalized cover letter for the job."""
        
        if not self.client:
            return self._generate_basic_cover_letter(job_info, resume_analysis, company_name)
        
        try:
            job_title = job_info.get("title", "")
            job_description = job_info.get("description", "")
            current_skills = [skill["skill"] for skill in resume_analysis.get("current_skills", [])]
            
            prompt = f"""
            Generate a compelling cover letter for a {job_title} position at {company_name}.
            
            Job Description:
            {job_description[:1000]}
            
            Candidate Skills: {', '.join(current_skills[:10])}
            
            Requirements:
            1. Keep it professional and concise (200-300 words)
            2. Highlight relevant skills and experience
            3. Show enthusiasm for the company and role
            4. Include specific examples from the job description
            5. End with a call to action
            6. Maintain a confident but humble tone
            
            Format the response as a proper cover letter with:
            - Professional greeting
            - Opening paragraph (interest in the role)
            - Body paragraph (relevant experience and skills)
            - Closing paragraph (enthusiasm and call to action)
            - Professional closing
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert cover letter writer. Create compelling, personalized cover letters that help candidates stand out."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            cover_letter = response.choices[0].message.content.strip()
            self.log_action("SUCCESS", "Cover letter generated successfully")
            return cover_letter
            
        except Exception as e:
            self.log_action("WARNING", f"AI cover letter generation failed: {str(e)}")
            return self._generate_basic_cover_letter(job_info, resume_analysis, company_name)
    
    def _generate_basic_cover_letter(self, job_info: Dict[str, Any], 
                                   resume_analysis: Dict[str, Any], 
                                   company_name: str) -> str:
        """Generate a basic cover letter without AI."""
        
        job_title = job_info.get("title", "")
        current_skills = [skill["skill"] for skill in resume_analysis.get("current_skills", [])]
        
        cover_letter = f"""
Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company_name}. With my background in {', '.join(current_skills[:3])} and related technologies, I am confident in my ability to contribute effectively to your team.

My experience includes working with {', '.join(current_skills[:5])} and I am particularly excited about the opportunity to apply these skills in a dynamic environment like {company_name}. I am passionate about continuous learning and staying current with industry best practices.

I would welcome the opportunity to discuss how my skills and experience align with your needs. Thank you for considering my application.

Best regards,
[Your Name]
        """.strip()
        
        return cover_letter
    
    async def _apply_via_linkedin(self, job_info: Dict[str, Any], 
                                 resume_path: str, 
                                 cover_letter: str) -> Dict[str, Any]:
        """Apply to a job via LinkedIn."""
        
        try:
            self.log_action("INFO", "Applying via LinkedIn")
            
            # LinkedIn agent removed - using web-based approach only
            # For now, return a placeholder result
            application_result = {
                "status": "placeholder",
                "message": "LinkedIn agent integration removed - using web-based approach",
                "job_id": job_info.get("id", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            return application_result
            
        except Exception as e:
            self.log_action("ERROR", f"LinkedIn application failed: {str(e)}")
            return {
                "status": "error",
                "error": f"LinkedIn application failed: {str(e)}",
                "method": "linkedin"
            }
    
    async def _apply_via_indeed(self, job_info: Dict[str, Any], 
                               resume_path: str, 
                               cover_letter: str) -> Dict[str, Any]:
        """Apply to a job via Indeed."""
        
        try:
            self.log_action("INFO", "Applying via Indeed")
            
            # Initialize browser if needed
            await self._init_browser()
            
            # Navigate to job page
            job_url = job_info.get("url", "")
            if not job_url:
                return {
                    "status": "error",
                    "error": "No job URL provided",
                    "method": "indeed"
                }
            
            self.driver.get(job_url)
            await asyncio.sleep(3)  # Wait for page load
            
            # Look for apply button
            apply_button = None
            try:
                # Common Indeed apply button selectors
                selectors = [
                    "button[data-indeed-apply-button-enabled='true']",
                    "button[aria-label*='Apply']",
                    "button:contains('Apply')",
                    "a[href*='apply']",
                    ".indeed-apply-button"
                ]
                
                for selector in selectors:
                    try:
                        if "contains" in selector:
                            # Handle text-based selection
                            elements = self.driver.find_elements(By.TAG_NAME, "button")
                            for elem in elements:
                                if "apply" in elem.text.lower():
                                    apply_button = elem
                                    break
                        else:
                            apply_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            break
                    except:
                        continue
                
                if not apply_button:
                    return {
                        "status": "error",
                        "error": "Apply button not found",
                        "method": "indeed"
                    }
                
                # Click apply button
                apply_button.click()
                await asyncio.sleep(2)
                
                # Handle application form
                application_result = await self._handle_application_form(
                    job_info, resume_path, cover_letter, "indeed"
                )
                
                return application_result
                
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Indeed application failed: {str(e)}",
                    "method": "indeed"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Indeed application failed: {str(e)}",
                "method": "indeed"
            }
    
    async def _apply_generic(self, job_info: Dict[str, Any], 
                            resume_path: str, 
                            cover_letter: str) -> Dict[str, Any]:
        """Generic application method for unknown job sources."""
        
        try:
            self.log_action("INFO", "Using generic application method")
            
            # Initialize browser if needed
            await self._init_browser()
            
            # Navigate to job page
            job_url = job_info.get("url", "")
            if not job_url:
                return {
                    "status": "error",
                    "error": "No job URL provided",
                    "method": "generic"
                }
            
            self.driver.get(job_url)
            await asyncio.sleep(3)
            
            # Look for common apply patterns
            apply_patterns = [
                "//button[contains(text(), 'Apply')]",
                "//a[contains(text(), 'Apply')]",
                "//input[@value='Apply']",
                "//button[contains(@class, 'apply')]",
                "//a[contains(@href, 'apply')]"
            ]
            
            apply_button = None
            for pattern in apply_patterns:
                try:
                    apply_button = self.driver.find_element(By.XPATH, pattern)
                    break
                except:
                    continue
            
            if not apply_button:
                return {
                    "status": "error",
                    "error": "Apply button not found",
                    "method": "generic"
                }
            
            # Click apply button
            apply_button.click()
            await asyncio.sleep(2)
            
            # Handle application form
            application_result = await self._handle_application_form(
                job_info, resume_path, cover_letter, "generic"
            )
            
            return application_result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Generic application failed: {str(e)}",
                "method": "generic"
            }
    
    async def _handle_application_form(self, job_info: Dict[str, Any], 
                                     resume_path: str, 
                                     cover_letter: str, 
                                     method: str) -> Dict[str, Any]:
        """Handle the application form after clicking apply."""
        
        try:
            self.log_action("INFO", f"Handling application form via {method}")
            
            # Wait for form to load
            await asyncio.sleep(3)
            
            # Common form field patterns
            form_fields = {
                "name": ["input[name*='name']", "input[id*='name']", "input[placeholder*='name']"],
                "email": ["input[type='email']", "input[name*='email']", "input[id*='email']"],
                "phone": ["input[type='tel']", "input[name*='phone']", "input[id*='phone']"],
                "resume": ["input[type='file']", "input[accept*='pdf']", "input[accept*='doc']"]
            }
            
            # Fill basic information
            for field_type, selectors in form_fields.items():
                if field_type == "resume":
                    continue  # Handle resume upload separately
                
                field_value = self._get_field_value(field_type, job_info)
                if not field_value:
                    continue
                
                field_found = False
                for selector in selectors:
                    try:
                        field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        field.clear()
                        field.send_keys(field_value)
                        field_found = True
                        break
                    except:
                        continue
                
                if not field_found:
                    self.log_action("WARNING", f"Could not find {field_type} field")
            
            # Handle resume upload
            resume_uploaded = await self._upload_resume(resume_path)
            
            # Handle cover letter if there's a text area
            cover_letter_added = False
            if cover_letter:
                cover_letter_added = await self._add_cover_letter(cover_letter)
            
            # Look for submit button
            submit_button = None
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Submit')",
                "button:contains('Send')",
                "button[class*='submit']"
            ]
            
            for selector in submit_selectors:
                try:
                    if "contains" in selector:
                        elements = self.driver.find_elements(By.TAG_NAME, "button")
                        for elem in elements:
                            if any(word in elem.text.lower() for word in ["submit", "send", "apply"]):
                                submit_button = elem
                                break
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        break
                except:
                    continue
            
            if submit_button:
                # Take screenshot before submitting
                screenshot_path = await self._take_screenshot("before_submit")
                
                # Submit application
                submit_button.click()
                await asyncio.sleep(3)
                
                # Check for success indicators
                success_indicators = [
                    "//*[contains(text(), 'Thank you')]",
                    "//*[contains(text(), 'Application submitted')]",
                    "//*[contains(text(), 'Success')]",
                    "//*[contains(text(), 'Submitted')]"
                ]
                
                application_successful = False
                for indicator in success_indicators:
                    try:
                        self.driver.find_element(By.XPATH, indicator)
                        application_successful = True
                        break
                    except:
                        continue
                
                if application_successful:
                    return {
                        "status": "success",
                        "method": method,
                        "resume_uploaded": resume_uploaded,
                        "cover_letter_added": cover_letter_added,
                        "screenshot_before": screenshot_path,
                        "submission_timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "status": "pending",
                        "method": method,
                        "message": "Application submitted but success confirmation unclear",
                        "resume_uploaded": resume_uploaded,
                        "cover_letter_added": cover_letter_added,
                        "screenshot_before": screenshot_path
                    }
            else:
                return {
                    "status": "error",
                    "error": "Submit button not found",
                    "method": method
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Form handling failed: {str(e)}",
                "method": method
            }
    
    def _get_field_value(self, field_type: str, job_info: Dict[str, Any]) -> str:
        """Get appropriate value for form fields."""
        
        # This would typically come from user configuration or profile
        # For now, return placeholder values
        field_values = {
            "name": "John Doe",  # Should come from user profile
            "email": "john.doe@example.com",  # Should come from user profile
            "phone": "(555) 123-4567"  # Should come from user profile
        }
        
        return field_values.get(field_type, "")
    
    async def _upload_resume(self, resume_path: str) -> bool:
        """Upload resume file to the application form."""
        
        try:
            if not os.path.exists(resume_path):
                self.log_action("ERROR", f"Resume file not found: {resume_path}")
                return False
            
            # Look for file upload field
            file_selectors = [
                "input[type='file']",
                "input[accept*='pdf']",
                "input[accept*='doc']",
                "input[accept*='docx']"
            ]
            
            for selector in file_selectors:
                try:
                    file_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    file_input.send_keys(os.path.abspath(resume_path))
                    self.log_action("SUCCESS", f"Resume uploaded: {resume_path}")
                    return True
                except:
                    continue
            
            self.log_action("WARNING", "Could not find file upload field")
            return False
            
        except Exception as e:
            self.log_action("ERROR", f"Resume upload failed: {str(e)}")
            return False
    
    async def _add_cover_letter(self, cover_letter: str) -> bool:
        """Add cover letter to the application form."""
        
        try:
            # Look for text area or input field for cover letter
            cover_letter_selectors = [
                "textarea[name*='cover']",
                "textarea[id*='cover']",
                "textarea[placeholder*='cover']",
                "textarea[name*='letter']",
                "textarea[id*='letter']",
                "textarea[placeholder*='letter']",
                "textarea[name*='message']",
                "textarea[id*='message']",
                "textarea[placeholder*='message']"
            ]
            
            for selector in cover_letter_selectors:
                try:
                    text_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text_area.clear()
                    text_area.send_keys(cover_letter)
                    self.log_action("SUCCESS", "Cover letter added to form")
                    return True
                except:
                    continue
            
            self.log_action("WARNING", "Could not find cover letter field")
            return False
            
        except Exception as e:
            self.log_action("ERROR", f"Cover letter addition failed: {str(e)}")
            return False
    
    async def _take_screenshot(self, prefix: str) -> str:
        """Take a screenshot of the current page."""
        
        try:
            # Create screenshots directory
            screenshots_dir = "./screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}.png"
            filepath = os.path.join(screenshots_dir, filename)
            
            # Take screenshot
            self.driver.save_screenshot(filepath)
            self.log_action("INFO", f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            self.log_action("WARNING", f"Screenshot failed: {str(e)}")
            return ""
    
    async def _init_browser(self, max_retries: int = 3):
        """Initialize Selenium WebDriver with robust error handling and retry mechanism."""
        
        if self.driver:
            return
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.log_action("INFO", f"Retrying browser initialization (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(2)  # Wait before retry
                
                await self._try_init_browser()
                return  # Success, exit the retry loop
                
            except Exception as e:
                last_error = e
                self.log_action("WARNING", f"Browser initialization attempt {attempt + 1} failed: {str(e)}")
                
                # Clean up any partial initialization
                if self.driver:
                    try:
                        self.driver.quit()
                        self.driver = None
                    except:
                        pass
        
        # All retries failed
        error_msg = f"Browser initialization failed after {max_retries} attempts. Last error: {str(last_error)}"
        self.log_action("ERROR", error_msg)
        raise Exception(error_msg)
    
    async def _try_init_browser(self):
        """Single attempt at browser initialization."""
        
        try:
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
            
            # Try to initialize driver with better error handling
            try:
                # First try with ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception as chrome_error:
                self.log_action("WARNING", f"ChromeDriverManager failed: {str(chrome_error)}")
                
                # Fallback: try to find Chrome in common Windows locations
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ]
                
                chrome_found = False
                for chrome_path in chrome_paths:
                    if os.path.exists(chrome_path):
                        chrome_options.binary_location = chrome_path
                        chrome_found = True
                        break
                
                if chrome_found:
                    # Try without specifying service
                    try:
                        self.driver = webdriver.Chrome(options=chrome_options)
                    except Exception as e:
                        self.log_action("WARNING", f"Chrome with binary location failed: {str(e)}")
                        # Try with minimal options
                        minimal_options = Options()
                        minimal_options.binary_location = chrome_path
                        minimal_options.add_argument("--no-sandbox")
                        minimal_options.add_argument("--disable-dev-shm-usage")
                        self.driver = webdriver.Chrome(options=minimal_options)
                else:
                    # Last resort: try with minimal options
                    try:
                        minimal_options = Options()
                        minimal_options.add_argument("--no-sandbox")
                        minimal_options.add_argument("--disable-dev-shm-usage")
                        self.driver = webdriver.Chrome(options=minimal_options)
                    except Exception as e:
                        self.log_action("ERROR", f"All Chrome initialization methods failed: {str(e)}")
                        raise Exception(f"Unable to initialize Chrome WebDriver: {str(e)}")
            
            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Test if browser is working
            await self._test_browser_functionality()
            
            self.log_action("BROWSER_INIT", "Chrome WebDriver initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize browser: {str(e)}"
            self.log_action("ERROR", error_msg)
            
            # Provide helpful error information
            if "WinError 193" in str(e):
                self.log_action("ERROR", "This error typically indicates ChromeDriver compatibility issues. Please ensure Chrome browser is installed and up to date.")
            elif "chromedriver" in str(e).lower():
                self.log_action("ERROR", "ChromeDriver issue detected. Please check Chrome browser installation.")
            
            raise Exception(error_msg)
    
    async def _test_browser_functionality(self):
        """Test if the browser is working properly."""
        
        try:
            # Try to navigate to a simple page
            self.driver.get("data:text/html,<html><body><h1>Test</h1></body></html>")
            
            # Check if we can get page title
            title = self.driver.title
            if not title:
                raise Exception("Could not get page title")
            
            # Check if we can find elements
            elements = self.driver.find_elements(By.TAG_NAME, "h1")
            if not elements:
                raise Exception("Could not find page elements")
            
            self.log_action("INFO", "Browser functionality test passed")
            
        except Exception as e:
            self.log_action("WARNING", f"Browser functionality test failed: {str(e)}")
            # Don't raise here, just log the warning
    
    async def _close_browser(self):
        """Close Selenium WebDriver."""
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_action("BROWSER_CLOSE", "WebDriver closed")
            except Exception as e:
                self.log_action("WARNING", f"Error closing browser: {str(e)}")
    
    async def get_application_tools(self) -> List[Dict[str, Any]]:
        """Get available tools for job applications."""
        
        return [
            {
                "name": "apply_to_job",
                "description": "Apply to a specific job",
                "parameters": {
                    "job_info": "Job information dictionary",
                    "resume_path": "Path to resume file",
                    "resume_analysis": "Resume analysis data"
                }
            },
            {
                "name": "generate_cover_letter",
                "description": "Generate personalized cover letter",
                "parameters": {
                    "job_info": "Job information dictionary",
                    "resume_analysis": "Resume analysis data",
                    "company_name": "Company name"
                }
            },
            {
                "name": "apply_via_linkedin",
                "description": "Apply to job via LinkedIn",
                "parameters": {
                    "job_info": "Job information dictionary",
                    "resume_path": "Path to resume file",
                    "cover_letter": "Cover letter text"
                }
            },
            {
                "name": "apply_via_indeed",
                "description": "Apply to job via Indeed",
                "parameters": {
                    "job_info": "Job information dictionary",
                    "resume_path": "Path to resume file",
                    "cover_letter": "Cover letter text"
                }
            },
            {
                "name": "get_application_status",
                "description": "Get status of recent applications",
                "parameters": {}
            }
        ]
    
    async def get_application_status(self) -> Dict[str, Any]:
        """Get status of recent applications."""
        
        return {
            "total_applications": self.application_count,
            "daily_limit": self.daily_limit,
            "remaining_today": max(0, self.daily_limit - self.application_count),
            "application_history": self.application_history[-10:],  # Last 10 applications
            "last_application": self.application_history[-1] if self.application_history else None
        }
    
    async def reset_daily_count(self):
        """Reset daily application count (typically called at midnight)."""
        
        self.application_count = 0
        self.log_action("INFO", "Daily application count reset")
    
    async def cleanup(self):
        """Clean up resources."""
        
        await self._close_browser()
        self.log_action("INFO", "Application agent cleaned up")
    
    def check_chrome_installation(self) -> Dict[str, Any]:
        """Check Chrome browser installation and provide diagnostics."""
        
        diagnostics = {
            "chrome_installed": False,
            "chrome_version": None,
            "chrome_path": None,
            "chromedriver_available": False,
            "recommendations": []
        }
        
        try:
            # Check common Chrome installation paths
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            
            for chrome_path in chrome_paths:
                if os.path.exists(chrome_path):
                    diagnostics["chrome_installed"] = True
                    diagnostics["chrome_path"] = chrome_path
                    
                    # Try to get Chrome version
                    try:
                        import subprocess
                        result = subprocess.run([chrome_path, "--version"], 
                                             capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            diagnostics["chrome_version"] = result.stdout.strip()
                    except:
                        pass
                    break
            
            # Check if ChromeDriver is available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                if os.path.exists(driver_path):
                    diagnostics["chromedriver_available"] = True
            except Exception as e:
                diagnostics["recommendations"].append(f"ChromeDriver issue: {str(e)}")
            
            # Provide recommendations
            if not diagnostics["chrome_installed"]:
                diagnostics["recommendations"].append("Chrome browser not found. Please install Google Chrome.")
            elif not diagnostics["chromedriver_available"]:
                diagnostics["recommendations"].append("ChromeDriver not available. Try updating webdriver-manager.")
            
            if diagnostics["chrome_installed"] and diagnostics["chrome_version"]:
                version = diagnostics["chrome_version"]
                if "120" in version or "121" in version or "122" in version:
                    diagnostics["recommendations"].append("Chrome version looks good for automation.")
                else:
                    diagnostics["recommendations"].append("Consider updating Chrome to latest version for better compatibility.")
            
        except Exception as e:
            diagnostics["recommendations"].append(f"Error during diagnostics: {str(e)}")
        
        return diagnostics
