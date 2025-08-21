"""
Database utilities for tracking job applications and results.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from config import Config

# Import Supabase database
from .supabase_database import SupabaseDatabase

class ApplicationDatabase:
    """Supabase database for tracking job applications."""
    
    def __init__(self, db_path: Optional[str] = None):
        # Initialize Supabase database
        self.db = SupabaseDatabase()
    
    def save_application(self, application_data: Dict[str, Any]) -> int:
        """Save job application data."""
        return self.db.save_application(application_data)
    
    def save_workflow_session(self, session_data: Dict[str, Any]) -> None:
        """Save workflow session data."""
        self.db.save_workflow_session(session_data)
    
    def track_skill(self, skill_name: str) -> None:
        """Track a skill mention."""
        self.db.track_skill(skill_name)
    
    def get_applications_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a session."""
        return self.db.get_applications_by_session(session_id)
    
    def get_application_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get application statistics for the last N days."""
        return self.db.get_application_statistics(days)
    
    def get_skill_trends(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending skills based on job demand."""
        return self.db.get_skill_trends(limit)
    
    def close(self):
        """Close database connection."""
        self.db.close()
