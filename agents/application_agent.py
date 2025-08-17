import asyncio
import os
import time
from typing import Dict, Any, List
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
from agents.base_agent import BaseAgent
from config import Config

class ApplicationAgent(BaseAgent):
    """Agent responsible for automatically applying to jobs."""
    
    def __init__(self):
        super().__init__("ApplicationAgent")
        self.driver = None
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
        self.application_count = 0
        self.daily_limit = Config.MAX_DAILY_APPLICATIONS
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job with the provided information."""
        
        # Validate required inputs
        required_fields = ["job_url", "resume_path"]
        if not self.validate_input(input_data, required_fields):
            return {"status": "error", "message": "Missing required fields"}
        
        job_url = input_data.get("job_url")
        resume_path = input_data.get("resume_path")
        cover_letter = input_data.get("cover_letter", "")
        job_title = input_data.get("job_title", "")
        company_name = input_data.get("company_name", "")
        
        # Check daily application limit
        if self.application_count >= self.daily_limit:
            return {
                "status": "skipped",
                "message": f"Daily application limit ({self.daily_limit}) reached"
            }
        
        self.log_action("APPLYING", f"{job_title} at {company_name}")
        
        try:
            # Initialize browser
            await self._init_browser()
            
            # Determine job site and apply accordingly
            application_result = await self._apply_to_job(
                job_url, resume_path, cover_letter, job_title, company_name
            )
            
            # Close browser
            await self._close_browser()
            
            if application_result.get("status") == "success":
                self.application_count += 1
                self.log_action("SUCCESS", f"Application submitted successfully")
            
            # Add application tracking info
            application_result.update({
                "job_url": job_url,
                "job_title": job_title,
                "company_name": company_name,
                "application_timestamp": datetime.now().isoformat(),
                "resume_used": resume_path,
                "daily_count": self.application_count
            })
            
            return application_result
            
        except Exception as e:
            self.log_action("ERROR", f"Application failed: {str(e)}")
            await self._close_browser()
            
            return {
                "status": "error",
                "message": f"Application failed: {str(e)}",
                "job_url": job_url,
                "job_title": job_title,
                "company_name": company_name
            }
    
    async def _init_browser(self):
        """Initialize Selenium WebDriver."""
        
        if self.driver:
            return
        
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            # Disable images and CSS for faster loading
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Initialize driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            self.log_action("BROWSER_INIT", "Chrome WebDriver initialized")
            
        except Exception as e:
            self.log_action("ERROR", f"Failed to initialize browser: {str(e)}")
            raise
    
    async def _close_browser(self):
        """Close Selenium WebDriver."""
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log_action("BROWSER_CLOSE", "WebDriver closed")
            except Exception as e:
                self.log_action("WARNING", f"Error closing browser: {str(e)}")
    
    async def _apply_to_job(self, job_url: str, resume_path: str, 
                          cover_letter: str, job_title: str, company_name: str) -> Dict[str, Any]:
        """Apply to a job based on the job site."""
        
        # Determine job site
        if "indeed.com" in job_url:
            return await self._apply_indeed(job_url, resume_path, cover_letter)
        elif "linkedin.com" in job_url:
            return await self._apply_linkedin(job_url, resume_path, cover_letter)
        elif "glassdoor.com" in job_url:
            return await self._apply_glassdoor(job_url, resume_path, cover_letter)
        else:
            return await self._apply_generic(job_url, resume_path, cover_letter)
    
    async def _apply_indeed(self, job_url: str, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Apply to a job on Indeed."""
        
        try:
            # Navigate to job page
            self.driver.get(job_url)
            await asyncio.sleep(2)
            
            # Look for apply button
            apply_selectors = [
                "//a[contains(@class, 'indeed-apply-button')]",
                "//button[contains(@class, 'indeed-apply-button')]",
                "//a[contains(text(), 'Apply Now')]",
                "//button[contains(text(), 'Apply Now')]",
                "//a[contains(@data-jk, 'apply')]",
                "//button[contains(@data-jk, 'apply')]"
            ]
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not apply_button:
                return {
                    "status": "failed",
                    "message": "Could not find apply button on Indeed"
                }
            
            # Click apply button
            apply_button.click()
            await asyncio.sleep(3)
            
            # Check if redirected to external site
            if "indeed.com" not in self.driver.current_url:
                return {
                    "status": "redirected",
                    "message": "Application redirected to external site",
                    "redirect_url": self.driver.current_url
                }
            
            # Fill out Indeed application form
            return await self._fill_indeed_application_form(resume_path, cover_letter)
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Indeed application failed: {str(e)}"
            }
    
    async def _fill_indeed_application_form(self, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Fill out Indeed's application form."""
        
        try:
            steps_completed = []
            
            # Step 1: Upload resume
            resume_upload = self._find_file_upload_input()
            if resume_upload and os.path.exists(resume_path):
                resume_upload.send_keys(os.path.abspath(resume_path))
                steps_completed.append("resume_uploaded")
                await asyncio.sleep(2)
            
            # Step 2: Fill cover letter if available
            if cover_letter:
                cover_letter_areas = self.driver.find_elements(By.XPATH, "//textarea")
                for textarea in cover_letter_areas:
                    if textarea.is_displayed() and textarea.is_enabled():
                        textarea.clear()
                        textarea.send_keys(cover_letter)
                        steps_completed.append("cover_letter_added")
                        break
            
            # Step 3: Fill any required fields with placeholder data
            await self._fill_common_application_fields()
            steps_completed.append("fields_filled")
            
            # Step 4: Submit application (optional - can be disabled for safety)
            submit_button = None
            submit_selectors = [
                "//button[contains(text(), 'Submit')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//a[contains(text(), 'Submit')]"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.XPATH, selector)
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        break
                except NoSuchElementException:
                    continue
            
            # For safety, we'll only simulate submission without actually clicking
            if submit_button:
                steps_completed.append("ready_to_submit")
                # submit_button.click()  # Uncomment to actually submit
                return {
                    "status": "simulated",  # Change to "success" when actually submitting
                    "message": "Application form filled (simulation mode)",
                    "steps_completed": steps_completed
                }
            else:
                return {
                    "status": "partial",
                    "message": "Form filled but could not find submit button",
                    "steps_completed": steps_completed
                }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Form filling failed: {str(e)}"
            }
    
    def _find_file_upload_input(self):
        """Find file upload input for resume."""
        
        upload_selectors = [
            "//input[@type='file']",
            "//input[contains(@name, 'resume')]",
            "//input[contains(@name, 'cv')]",
            "//input[contains(@id, 'resume')]",
            "//input[contains(@id, 'cv')]"
        ]
        
        for selector in upload_selectors:
            try:
                upload_input = self.driver.find_element(By.XPATH, selector)
                if upload_input.is_enabled():
                    return upload_input
            except NoSuchElementException:
                continue
        
        return None
    
    async def _fill_common_application_fields(self):
        """Fill common application fields with default data."""
        
        # Common field mappings
        field_data = {
            "firstName": "John",
            "first_name": "John",
            "fname": "John",
            "lastName": "Doe",
            "last_name": "Doe",
            "lname": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-0123",
            "phoneNumber": "555-0123",
            "phone_number": "555-0123"
        }
        
        # Fill text inputs
        for field_name, value in field_data.items():
            selectors = [
                f"//input[@name='{field_name}']",
                f"//input[@id='{field_name}']",
                f"//input[contains(@name, '{field_name.lower()}')]"
            ]
            
            for selector in selectors:
                try:
                    field = self.driver.find_element(By.XPATH, selector)
                    if field.is_displayed() and field.is_enabled():
                        field.clear()
                        field.send_keys(value)
                        break
                except NoSuchElementException:
                    continue
    
    async def _apply_linkedin(self, job_url: str, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Apply to a job on LinkedIn."""
        
        # LinkedIn requires authentication and has complex anti-bot measures
        # This is a simplified placeholder implementation
        
        try:
            self.driver.get(job_url)
            await asyncio.sleep(3)
            
            # Check if login is required
            if "login" in self.driver.current_url or "challenge" in self.driver.current_url:
                return {
                    "status": "authentication_required",
                    "message": "LinkedIn requires login authentication"
                }
            
            # Look for Easy Apply button
            easy_apply_button = None
            try:
                easy_apply_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'jobs-apply-button')]"))
                )
            except TimeoutException:
                return {
                    "status": "no_easy_apply",
                    "message": "Easy Apply not available for this job"
                }
            
            return {
                "status": "requires_manual_login",
                "message": "LinkedIn applications require manual login setup"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"LinkedIn application failed: {str(e)}"
            }
    
    async def _apply_glassdoor(self, job_url: str, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Apply to a job on Glassdoor."""
        
        try:
            self.driver.get(job_url)
            await asyncio.sleep(3)
            
            # Glassdoor often redirects to external sites or requires login
            return {
                "status": "requires_implementation",
                "message": "Glassdoor application automation requires additional implementation"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Glassdoor application failed: {str(e)}"
            }
    
    async def _apply_generic(self, job_url: str, resume_path: str, cover_letter: str) -> Dict[str, Any]:
        """Apply to a job on an unknown/generic job site."""
        
        try:
            self.driver.get(job_url)
            await asyncio.sleep(3)
            
            # Look for common apply button patterns
            apply_patterns = [
                "apply",
                "submit application",
                "apply now",
                "apply for this job",
                "apply online"
            ]
            
            apply_button = None
            for pattern in apply_patterns:
                try:
                    # Try different element types and attributes
                    selectors = [
                        f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]",
                        f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]",
                        f"//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{pattern}')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            apply_button = self.driver.find_element(By.XPATH, selector)
                            if apply_button.is_displayed() and apply_button.is_enabled():
                                break
                        except NoSuchElementException:
                            continue
                    
                    if apply_button:
                        break
                        
                except Exception:
                    continue
            
            if not apply_button:
                return {
                    "status": "no_apply_button",
                    "message": "Could not find apply button on this site"
                }
            
            # Click apply button and see what happens
            apply_button.click()
            await asyncio.sleep(3)
            
            return {
                "status": "clicked_apply",
                "message": "Clicked apply button - manual intervention may be required",
                "current_url": self.driver.current_url
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Generic application failed: {str(e)}"
            }
    
    async def generate_cover_letter(self, job_description: str, job_title: str, 
                                  company_name: str, resume_content: str) -> str:
        """Generate a personalized cover letter using AI."""
        
        if not self.client:
            return self._generate_basic_cover_letter(job_title, company_name)
        
        try:
            prompt = f"""
            Write a professional cover letter for the following job application:
            
            Job Title: {job_title}
            Company: {company_name}
            Job Description: {job_description[:1000]}
            
            Applicant Background: {resume_content[:800]}
            
            The cover letter should:
            1. Be professional and concise (2-3 paragraphs)
            2. Highlight relevant experience and skills
            3. Show enthusiasm for the role and company
            4. Be personalized to the specific job
            5. Include a strong opening and closing
            
            Write only the cover letter content, no additional commentary.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional career coach writing compelling cover letters."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.log_action("ERROR", f"AI cover letter generation failed: {str(e)}")
            return self._generate_basic_cover_letter(job_title, company_name)
    
    def _generate_basic_cover_letter(self, job_title: str, company_name: str) -> str:
        """Generate a basic cover letter template."""
        
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company_name}. With my technical background and passion for innovation, I am excited about the opportunity to contribute to your team.

My experience in software development and problem-solving aligns well with the requirements of this role. I am particularly drawn to {company_name}'s reputation for excellence and would welcome the chance to bring my skills to your organization.

Thank you for considering my application. I look forward to discussing how I can contribute to {company_name}'s continued success.

Best regards,
[Your Name]"""
    
    def get_application_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        
        return {
            "applications_today": self.application_count,
            "daily_limit": self.daily_limit,
            "remaining_applications": max(0, self.daily_limit - self.application_count),
            "limit_reached": self.application_count >= self.daily_limit
        }
