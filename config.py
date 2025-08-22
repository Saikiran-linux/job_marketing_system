import os
from dotenv import load_dotenv
from typing import Optional
from job_config import JobConfig

load_dotenv()

class Config:
    """Configuration settings for the job application system."""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Job Board Credentials (for web automation)
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    GLASSDOOR_EMAIL: str = os.getenv("GLASSDOOR_EMAIL", "")
    GLASSDOOR_PASSWORD: str = os.getenv("GLASSDOOR_PASSWORD", "")
    INDEED_EMAIL: str = os.getenv("INDEED_EMAIL", "")
    INDEED_PASSWORD: str = os.getenv("INDEED_PASSWORD", "")
    
    # Database Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Database Selection
    USE_SUPABASE: bool = bool(SUPABASE_URL and SUPABASE_ANON_KEY)
    
    # Legacy SQLite fallback (kept for backward compatibility)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///job_applications.db")
    
    # Web Automation Settings
    WEB_AUTOMATION_TIMEOUT: int = int(os.getenv("WEB_AUTOMATION_TIMEOUT", "60"))  # Default 60 seconds
    WEB_AUTOMATION_MAX_RETRIES: int = int(os.getenv("WEB_AUTOMATION_MAX_RETRIES", "3"))
    WEB_AUTOMATION_DELAY: float = float(os.getenv("WEB_AUTOMATION_DELAY", "2.0"))
    
    # Enhanced Timeout Settings (in seconds)
    AUTH_TIMEOUT: int = int(os.getenv("AUTH_TIMEOUT", "45"))  # Authentication timeout
    SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "90"))  # Job search timeout
    ELEMENT_TIMEOUT: int = int(os.getenv("ELEMENT_TIMEOUT", "30"))  # Element waiting timeout
    PAGE_LOAD_TIMEOUT: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "60"))  # Page loading timeout
    
    # Network and Retry Settings
    NETWORK_RETRY_DELAY: float = float(os.getenv("NETWORK_RETRY_DELAY", "3.0"))  # Delay between retries
    SLOW_NETWORK_MULTIPLIER: float = float(os.getenv("SLOW_NETWORK_MULTIPLIER", "2.5"))  # Multiplier for slow networks
    
    # File Paths
    RESUME_TEMPLATE_PATH: str = os.getenv("RESUME_TEMPLATE_PATH", "./data/resume_template.docx")
    OUTPUT_RESUME_DIR: str = os.getenv("OUTPUT_RESUME_DIR", "./output/resumes/")
    APPLICATION_LOG_DIR: str = os.getenv("APPLICATION_LOG_DIR", "./logs/")
    
    # Job Search Settings - Imported from job_config.py
    MAX_JOBS_PER_SOURCE: int = JobConfig.MAX_JOBS_PER_SOURCE
    APPLICATION_DELAY: int = JobConfig.APPLICATION_DELAY
    MAX_DAILY_APPLICATIONS: int = JobConfig.MAX_DAILY_APPLICATIONS
    SKILL_MATCH_THRESHOLD: float = JobConfig.SKILL_MATCH_THRESHOLD
    
    # Job Search Configuration - Imported from job_config.py
    DEFAULT_JOB_ROLE: str = JobConfig.ROLE
    DEFAULT_JOB_LOCATION: str = JobConfig.LOCATION
    DEFAULT_MAX_JOBS: int = JobConfig.MAX_JOBS
    DEFAULT_AUTO_APPLY: bool = JobConfig.AUTO_APPLY
    
    # Job Search Filters - Imported from job_config.py
    JOB_SEARCH_KEYWORDS: list = JobConfig.KEYWORDS
    JOB_SEARCH_EXCLUDE_KEYWORDS: list = JobConfig.EXCLUDE_KEYWORDS
    MIN_SALARY: Optional[int] = JobConfig.MIN_SALARY
    MAX_SALARY: Optional[int] = JobConfig.MAX_SALARY
    JOB_TYPE: list = JobConfig.JOB_TYPES
    EXPERIENCE_LEVEL: list = JobConfig.EXPERIENCE_LEVELS
    
    # Resume Configuration - Imported from job_config.py
    DEFAULT_RESUME_PATH: str = JobConfig.RESUME_PATH
    
    # Resume Settings - Imported from job_config.py
    MAX_RESUME_PAGES: int = JobConfig.MAX_RESUME_PAGES
    MIN_SKILL_MENTIONS: int = JobConfig.MIN_SKILL_MENTIONS
    
    # Default Location and Job Types - Imported from job_config.py
    DEFAULT_LOCATION: str = JobConfig.DEFAULT_LOCATION
    DEFAULT_JOB_TYPES: list = JobConfig.DEFAULT_JOB_TYPES
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present."""
        required_fields = [
            "OPENAI_API_KEY"
        ]
        
        # Check web credentials configuration
        web_credentials = [
            "LINKEDIN_EMAIL",
            "LINKEDIN_PASSWORD", 
            "GLASSDOOR_EMAIL",
            "GLASSDOOR_PASSWORD"
        ]
        
        web_configured = any([
            getattr(cls, field) for field in web_credentials
        ])
        
        if not web_configured:
            print("Warning: No job board credentials configured")
            print("LinkedIn and Glassdoor integration will be disabled")
            print("Please set up your .env file with email/password credentials")
        
        for field in required_fields:
            if not getattr(cls, field):
                print(f"Warning: {field} is not set in configuration")
                return False
        return True
    
    @classmethod
    def create_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            cls.OUTPUT_RESUME_DIR,
            cls.APPLICATION_LOG_DIR,
            "./data/",
            "./output/",
            "./logs/"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
