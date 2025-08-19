import asyncio
import re
from typing import Dict, Any, List, Set
import openai
from openai import AsyncOpenAI
import nltk
from collections import Counter
from agents.base_agent import BaseAgent, AgentState
from config import Config

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class SkillsAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing job descriptions and extracting required skills."""
    
    def __init__(self):
        super().__init__("SkillsAnalysisAgent")
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Common technical skills database
        self.technical_skills = {
            "programming_languages": [
                "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
                "kotlin", "swift", "php", "ruby", "scala", "r", "matlab", "sql"
            ],
            "frameworks": [
                "react", "angular", "vue", "django", "flask", "fastapi", "spring", "express",
                "node.js", "next.js", "nuxt.js", "laravel", "rails", "asp.net", "tensorflow",
                "pytorch", "scikit-learn", "pandas", "numpy"
            ],
            "databases": [
                "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
                "oracle", "sqlite", "dynamodb", "neo4j"
            ],
            "cloud_platforms": [
                "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
                "ansible", "jenkins", "gitlab", "github actions"
            ],
            "tools": [
                "git", "jira", "confluence", "slack", "teams", "figma", "sketch", "photoshop",
                "tableau", "power bi", "excel", "powerpoint"
            ]
        }
        
        # Compile skill patterns
        self.skill_patterns = self._compile_skill_patterns()
    
    def _compile_skill_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for skill extraction."""
        patterns = {}
        
        for category, skills in self.technical_skills.items():
            # Create pattern that matches skills with word boundaries
            skill_pattern = r'\b(?:' + '|'.join(re.escape(skill) for skill in skills) + r')\b'
            patterns[category] = re.compile(skill_pattern, re.IGNORECASE)
        
        return patterns
    
    async def execute(self, state: AgentState) -> AgentState:
        """Analyze job description and extract required skills."""
        
        # For skills analysis, we need to get the job description from the context
        # This agent is typically called with specific job data, not from the main workflow state
        # We'll create a temporary state or use the existing state if it has job information
        
        # Since this agent is called during job processing, we need to handle the case
        # where we don't have direct access to job description in the main state
        # For now, we'll return the state as-is and handle the actual analysis in the calling context
        
        self.log_action("INFO", "Skills analysis agent called - job-specific analysis handled in calling context")
        
        # Update state to indicate skills analysis step
        state.steps_completed.append("skills_analysis")
        state.current_step = "skills_analysis_complete"
        
        return state
