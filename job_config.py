"""
Job search configuration file.
This file contains all job search related configuration settings.
You can customize these values directly in this file.
"""

from typing import List, Optional

class JobConfig:
    """Job search configuration with hardcoded values."""
    
    # Job Search Preferences
    ROLE = "Applied AI Engineer"
    LOCATION = "Remote"
    MAX_JOBS = 10
    AUTO_APPLY = False
    
    # Keywords and Filters
    KEYWORDS = ["python", "machine learning", "AI", "data science"]
    EXCLUDE_KEYWORDS = ["senior", "lead", "manager", "director"]
    
    # Salary Range
    MIN_SALARY = 80000
    MAX_SALARY = 150000
    
    # Job Types and Experience
    JOB_TYPES = ["full-time", "remote"]
    EXPERIENCE_LEVELS = ["entry", "mid-level"]
    
    # Resume and Application Settings
    RESUME_PATH = "./resume.docx"
    APPLICATION_DELAY = 30
    MAX_DAILY_APPLICATIONS = 10
    
    # Job Search Settings
    MAX_JOBS_PER_SOURCE = 50
    DEFAULT_LOCATION = "remote"
    DEFAULT_JOB_TYPES = ["full-time", "contract", "remote"]
    
    # Parallel Execution Settings
    ENABLE_PARALLEL_SEARCH = True
    MAX_CONCURRENT_SEARCHES = 5
    SEARCH_TIMEOUT_PER_SOURCE = 30  # seconds
    
    # Job Sources Configuration
    JOB_SOURCES = {
        "indeed": {
            "enabled": True,
            "priority": 1,
            "max_jobs_per_source": 25
        },
        "linkedin": {
            "enabled": True,
            "priority": 1,
            "max_jobs_per_source": 25
        },
        "glassdoor": {
            "enabled": True,
            "priority": 2,
            "max_jobs_per_source": 20
        },
        "google_jobs": {
            "enabled": True,
            "priority": 2,
            "max_jobs_per_source": 20
        },
        "company_websites": {
            "enabled": True,
            "priority": 3,
            "max_jobs_per_source": 15
        }
    }
    
    # Company Websites to Search
    TARGET_COMPANIES = [
        "Google", "Microsoft", "Apple", "Amazon", "Meta", "Netflix",
        "Uber", "Airbnb", "Stripe", "Palantir", "OpenAI", "Anthropic",
        "Databricks", "Snowflake", "MongoDB", "Elastic", "GitHub",
        "NVIDIA", "Intel", "AMD", "Oracle", "Salesforce", "Adobe"
    ]
    
    # Application Behavior
    SKILL_MATCH_THRESHOLD = 0.7
    
    # Resume Settings
    MAX_RESUME_PAGES = 2
    MIN_SKILL_MENTIONS = 3
    
    # Safety Settings
    MAX_REQUESTS_PER_MINUTE = 10
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    @classmethod
    def get_job_filters(cls) -> dict:
        """Get all job search filters as a dictionary."""
        return {
            "role": cls.ROLE,
            "location": cls.LOCATION,
            "keywords": cls.KEYWORDS,
            "exclude_keywords": cls.EXCLUDE_KEYWORDS,
            "min_salary": cls.MIN_SALARY,
            "max_salary": cls.MAX_SALARY,
            "job_types": cls.JOB_TYPES,
            "experience_levels": cls.EXPERIENCE_LEVELS,
            "max_jobs": cls.MAX_JOBS,
            "auto_apply": cls.AUTO_APPLY,
            "enable_parallel_search": cls.ENABLE_PARALLEL_SEARCH,
            "max_concurrent_searches": cls.MAX_CONCURRENT_SEARCHES
        }
    
    @classmethod
    def get_enabled_sources(cls) -> List[str]:
        """Get list of enabled job sources."""
        return [source for source, config in cls.JOB_SOURCES.items() if config["enabled"]]
    
    @classmethod
    def get_source_config(cls, source_name: str) -> Optional[dict]:
        """Get configuration for a specific job source."""
        return cls.JOB_SOURCES.get(source_name)
    
    @classmethod
    def print_config(cls):
        """Print current job search configuration."""
        print("=== Job Search Configuration ===")
        print(f"Role: {cls.ROLE}")
        print(f"Location: {cls.LOCATION}")
        print(f"Max Jobs: {cls.MAX_JOBS}")
        print(f"Auto Apply: {cls.AUTO_APPLY}")
        print(f"Parallel Search: {cls.ENABLE_PARALLEL_SEARCH}")
        print(f"Max Concurrent Searches: {cls.MAX_CONCURRENT_SEARCHES}")
        print(f"Job Sources: {', '.join(cls.get_enabled_sources())}")
        print(f"Target Companies: {len(cls.TARGET_COMPANIES)} companies")
        print("================================")

# Predefined job configurations for common roles
JOB_PRESETS = {
    "software_engineer": {
        "role": "Software Engineer",
        "keywords": ["python", "javascript", "react", "node.js", "full-stack"],
        "exclude_keywords": ["senior", "lead", "manager", "director"],
        "experience_levels": ["entry", "mid-level"]
    },
    "data_scientist": {
        "role": "Data Scientist",
        "keywords": ["machine learning", "python", "SQL", "statistics", "AI"],
        "exclude_keywords": ["senior", "lead", "manager", "director"],
        "experience_levels": ["entry", "mid-level"]
    },
    "frontend_developer": {
        "role": "Frontend Developer",
        "keywords": ["react", "javascript", "typescript", "CSS", "HTML"],
        "exclude_keywords": ["senior", "lead", "manager", "director"],
        "experience_levels": ["entry", "mid-level"]
    },
    "machine_learning_engineer": {
        "role": "Machine Learning Engineer",
        "keywords": ["machine learning", "deep learning", "tensorflow", "pytorch", "python"],
        "exclude_keywords": ["senior", "lead", "manager", "director"],
        "experience_levels": ["entry", "mid-level"]
    }
}

def get_job_preset(preset_name: str) -> dict:
    """Get a predefined job configuration preset."""
    return JOB_PRESETS.get(preset_name.lower(), {})

def apply_job_preset(preset_name: str):
    """Apply a predefined job configuration preset."""
    preset = get_job_preset(preset_name)
    if preset:
        JobConfig.ROLE = preset.get("role", JobConfig.ROLE)
        JobConfig.KEYWORDS = preset.get("keywords", JobConfig.KEYWORDS)
        JobConfig.EXCLUDE_KEYWORDS = preset.get("exclude_keywords", JobConfig.EXCLUDE_KEYWORDS)
        JobConfig.EXPERIENCE_LEVELS = preset.get("experience_levels", JobConfig.EXPERIENCE_LEVELS)
        print(f"✅ Applied {preset_name} preset")
    else:
        print(f"❌ Preset '{preset_name}' not found. Available presets: {', '.join(JOB_PRESETS.keys())}")
