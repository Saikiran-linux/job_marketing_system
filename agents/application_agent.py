"""
Application Agent - Handles job application automation using web automation.
"""

import asyncio
import time
import random
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from agents.base_agent import BaseAgent, AgentState
from config import Config
from utils.logger import setup_logger

class ApplicationAgent(BaseAgent):
    """Agent for automating job applications using web automation."""
    
    def __init__(self):
        super().__init__("ApplicationAgent")
        self.browser = None
        self.context = None
        self.page = None
        self.logger = setup_logger("ApplicationAgent")
        
    async def execute(self, state: AgentState) -> AgentState:
        """Execute job application workflow using web automation."""
        
        try:
            self.log_action("STARTING", "Starting job application workflow")
            
            # Initialize browser
            await self._init_browser()
            
            # Process jobs for application
            if hasattr(state, 'filtered_jobs') and state.filtered_jobs:
                applications = await self._apply_to_jobs(state.filtered_jobs, state)
                state.applications = applications
                state.steps_completed.append("job_applications")
                
                # Calculate success rate
                successful_apps = len([app for app in applications if app.get("status") == "success"])
                success_rate = (successful_apps / len(applications)) * 100 if applications else 0
                
                self.log_action("SUCCESS", f"Applied to {len(applications)} jobs with {success_rate:.1f}% success rate")
            else:
                self.log_action("WARNING", "No filtered jobs available for application")
                state.applications = []
            
            self.log_action("COMPLETE", "Job application workflow completed")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Job application workflow failed: {str(e)}")
            state.error = f"Application error: {str(e)}"
            return state
        finally:
            await self._close_browser()
    
    async def _apply_to_jobs(self, jobs: List[Dict[str, Any]], state: AgentState) -> List[Dict[str, Any]]:
        """Apply to multiple jobs."""
        
        applications = []
        
        for job in jobs[:min(len(jobs), 10)]:  # Limit to 10 applications
            try:
                self.log_action("INFO", f"Applying to: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
                
                application_result = await self._apply_to_single_job(job, state)
                applications.append(application_result)
                
                # Wait between applications to avoid being flagged as bot
                await asyncio.sleep(random.uniform(3, 8))
                
            except Exception as e:
                self.log_action("ERROR", f"Error applying to job {job.get('title', 'Unknown')}: {str(e)}")
                applications.append({
                    "job_title": job.get('title', 'Unknown'),
                    "company": job.get('company', 'Unknown'),
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
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
                    "error": "No job URL available",
                    "timestamp": datetime.now().isoformat()
                }
            
            await self.page.goto(job['url'])
            await self.page.wait_for_load_state("networkidle")
            
            # Look for apply button
            apply_selectors = [
                "button[data-test='apply-button']",
                "button:has-text('Apply')",
                "button:has-text('Apply Now')",
                "a[data-test='apply-link']",
                "a:has-text('Apply')",
                ".apply-button",
                "[data-test='apply']",
                "input[value*='Apply']",
                "input[value*='Submit']"
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
                    "error": "Apply button not found",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Click apply button
            await apply_button.click()
            await self.page.wait_for_load_state("networkidle")
            
            # Handle application form if it appears
            application_success = await self._handle_application_form(job, state)
            
            return {
                "job_title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "status": "success" if application_success else "partial",
                "timestamp": datetime.now().isoformat(),
                "url": job.get('url', '')
            }
            
        except Exception as e:
            return {
                "job_title": job.get('title', 'Unknown'),
                "company": job.get('company', 'Unknown'),
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _handle_application_form(self, job: Dict[str, Any], state: AgentState) -> bool:
        """Handle the job application form if it appears."""
        
        try:
            # Look for common form elements
            form_selectors = [
                "form[action*='apply']",
                "form[data-test='application-form']",
                ".application-form",
                "[data-test='apply-form']",
                "form[method='post']",
                "form"
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
                email_selectors = [
                    "input[name='email']", 
                    "input[type='email']", 
                    "#email",
                    "input[name='e-mail']",
                    "input[name='user_email']"
                ]
                
                for selector in email_selectors:
                    try:
                        email_field = await self.page.query_selector(selector)
                        if email_field:
                            await email_field.fill(Config.LINKEDIN_EMAIL or Config.GLASSDOOR_EMAIL or "user@example.com")
                            break
                    except:
                        continue
                
                # First name field
                first_name_selectors = [
                    "input[name='firstName']", 
                    "input[name='first_name']", 
                    "#firstName",
                    "input[name='fname']",
                    "input[name='given_name']"
                ]
                
                for selector in first_name_selectors:
                    try:
                        name_field = await self.page.query_selector(selector)
                        if name_field:
                            await name_field.fill("Your")  # Placeholder
                            break
                    except:
                        continue
                
                # Last name field
                last_name_selectors = [
                    "input[name='lastName']", 
                    "input[name='last_name']", 
                    "#lastName",
                    "input[name='lname']",
                    "input[name='family_name']"
                ]
                
                for selector in last_name_selectors:
                    try:
                        name_field = await self.page.query_selector(selector)
                        if name_field:
                            await name_field.fill("Name")  # Placeholder
                            break
                    except:
                        continue
                
                # Phone field
                phone_selectors = [
                    "input[name='phone']", 
                    "input[type='tel']", 
                    "#phone",
                    "input[name='telephone']",
                    "input[name='mobile']"
                ]
                
                for selector in phone_selectors:
                    try:
                        phone_field = await self.page.query_selector(selector)
                        if phone_field:
                            await phone_field.fill("555-123-4567")  # Placeholder
                            break
                    except:
                        continue
                
                # Resume upload (if available)
                resume_path = getattr(state, 'resume_path', None)
                if resume_path and os.path.exists(resume_path):
                    file_input_selectors = [
                        "input[type='file']",
                        "input[accept*='.pdf']",
                        "input[accept*='.doc']",
                        "input[accept*='.docx']"
                    ]
                    
                    for selector in file_input_selectors:
                        try:
                            file_input = await self.page.query_selector(selector)
                            if file_input:
                                await file_input.set_input_files(resume_path)
                                break
                        except:
                            continue
                
                # Submit form if submit button found
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Submit')",
                    "button:has-text('Apply')",
                    "button:has-text('Send')",
                    "input[value*='Submit']",
                    "input[value*='Apply']",
                    "input[value*='Send']"
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
    
    async def _init_browser(self):
        """Initialize Playwright browser with robust error handling and retry mechanism."""
        
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
                        "--window-size=1920,1080",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                
                # Create context with specific user agent and stealth settings
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    timezone_id="America/New_York"
                )
                
                # Create new page
                self.page = await self.context.new_page()
                
                # Set extra headers for better compatibility
                await self.page.set_extra_http_headers({
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none"
                })
                
                # Add stealth scripts to avoid detection
                await self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                
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
