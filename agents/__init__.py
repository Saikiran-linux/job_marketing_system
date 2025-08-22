"""
Simplified Multi-Agent Architecture for Job Application System
"""

from .orchestrator_agent import OrchestratorAgent
from .scraper_agent import ScraperAgent
from .analyzer_agent import AnalyzerAgent
from .resume_agent import ResumeAgent
from .application_agent import ApplicationAgent
from .tracker_agent import TrackerAgent
from .base_agent import BaseAgent, AgentState

__all__ = [
    'OrchestratorAgent',
    'ScraperAgent', 
    'AnalyzerAgent',
    'ResumeAgent',
    'ApplicationAgent',
    'TrackerAgent',
    'BaseAgent',
    'AgentState'
]
