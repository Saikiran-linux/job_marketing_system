import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Configuration settings for the job application system."""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Job Board Credentials
    LINKEDIN_EMAIL: str = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD", "")
    INDEED_EMAIL: str = os.getenv("INDEED_EMAIL", "")
    INDEED_PASSWORD: str = os.getenv("INDEED_PASSWORD", "")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///job_applications.db")
    
    # Application Settings
    MAX_JOBS_PER_SOURCE: int = int(os.getenv("MAX_JOBS_PER_SOURCE", "50"))
    APPLICATION_DELAY: int = int(os.getenv("APPLICATION_DELAY", "5"))
    MAX_DAILY_APPLICATIONS: int = int(os.getenv("MAX_DAILY_APPLICATIONS", "20"))
    SKILL_MATCH_THRESHOLD: float = float(os.getenv("SKILL_MATCH_THRESHOLD", "0.7"))
    
    # File Paths
    RESUME_TEMPLATE_PATH: str = os.getenv("RESUME_TEMPLATE_PATH", "./data/resume_template.docx")
    OUTPUT_RESUME_DIR: str = os.getenv("OUTPUT_RESUME_DIR", "./output/resumes/")
    APPLICATION_LOG_DIR: str = os.getenv("APPLICATION_LOG_DIR", "./logs/")
    
    # Job Search Settings
    DEFAULT_LOCATION: str = "remote"
    DEFAULT_JOB_TYPES: list = ["full-time", "contract", "remote"]
    
    # Resume Settings
    MAX_RESUME_PAGES: int = 2
    MIN_SKILL_MENTIONS: int = 3
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that required configuration is present."""
        required_fields = [
            "OPENAI_API_KEY"
        ]
        
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
