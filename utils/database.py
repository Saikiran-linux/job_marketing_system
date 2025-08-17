"""
Database utilities for tracking job applications and results.
"""

import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from config import Config

class ApplicationDatabase:
    """Simple SQLite database for tracking job applications."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()
        self._init_database()
    
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        db_dir = os.path.dirname(Config.APPLICATION_LOG_DIR)
        return os.path.join(db_dir, "job_applications.db")
    
    def _init_database(self):
        """Initialize database tables."""
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    job_title TEXT,
                    company_name TEXT,
                    job_url TEXT,
                    application_status TEXT,
                    application_timestamp DATETIME,
                    resume_path TEXT,
                    cover_letter_preview TEXT,
                    job_data JSON,
                    skill_analysis JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Skills tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    job_count INTEGER DEFAULT 1,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(skill_name)
                )
            """)
            
            # Workflow sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    status TEXT,
                    input_parameters JSON,
                    final_results JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_application(self, application_data: Dict[str, Any]) -> int:
        """Save job application data."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO applications (
                    session_id, job_id, job_title, company_name, job_url,
                    application_status, application_timestamp, resume_path,
                    cover_letter_preview, job_data, skill_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                application_data.get("session_id", ""),
                application_data.get("job_id", ""),
                application_data.get("job_title", ""),
                application_data.get("company_name", ""),
                application_data.get("job_url", ""),
                application_data.get("application_status", ""),
                application_data.get("application_timestamp", datetime.now().isoformat()),
                application_data.get("resume_path", ""),
                application_data.get("cover_letter_preview", "")[:500],  # Truncate
                json.dumps(application_data.get("job_data", {})),
                json.dumps(application_data.get("skill_analysis", {}))
            ))
            
            application_id = cursor.lastrowid
            conn.commit()
            
            return application_id
    
    def save_workflow_session(self, session_data: Dict[str, Any]) -> None:
        """Save workflow session data."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO workflow_sessions (
                    session_id, start_time, end_time, status,
                    input_parameters, final_results
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_data.get("session_id", ""),
                session_data.get("start_time", ""),
                session_data.get("end_time", ""),
                session_data.get("status", ""),
                json.dumps(session_data.get("input_parameters", {})),
                json.dumps(session_data.get("final_results", {}))
            ))
            
            conn.commit()
    
    def track_skill(self, skill_name: str) -> None:
        """Track a skill mention."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO skills_tracking (skill_name, job_count, last_seen)
                VALUES (?, 1, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    job_count = job_count + 1,
                    last_seen = ?
            """, (skill_name, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
    
    def get_applications_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a session."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM applications WHERE session_id = ?
                ORDER BY created_at DESC
            """, (session_id,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            applications = []
            for row in rows:
                app_data = dict(zip(columns, row))
                
                # Parse JSON fields
                if app_data.get("job_data"):
                    try:
                        app_data["job_data"] = json.loads(app_data["job_data"])
                    except json.JSONDecodeError:
                        app_data["job_data"] = {}
                
                if app_data.get("skill_analysis"):
                    try:
                        app_data["skill_analysis"] = json.loads(app_data["skill_analysis"])
                    except json.JSONDecodeError:
                        app_data["skill_analysis"] = {}
                
                applications.append(app_data)
            
            return applications
    
    def get_application_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get application statistics for the last N days."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Total applications
            cursor.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE created_at >= ?
            """, (cutoff_date.isoformat(),))
            total_applications = cursor.fetchone()[0]
            
            # Applications by status
            cursor.execute("""
                SELECT application_status, COUNT(*) FROM applications 
                WHERE created_at >= ?
                GROUP BY application_status
            """, (cutoff_date.isoformat(),))
            status_counts = dict(cursor.fetchall())
            
            # Applications by company
            cursor.execute("""
                SELECT company_name, COUNT(*) FROM applications 
                WHERE created_at >= ?
                GROUP BY company_name
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (cutoff_date.isoformat(),))
            top_companies = cursor.fetchall()
            
            # Top skills
            cursor.execute("""
                SELECT skill_name, job_count FROM skills_tracking
                ORDER BY job_count DESC
                LIMIT 10
            """)
            top_skills = cursor.fetchall()
            
            return {
                "total_applications": total_applications,
                "applications_by_status": status_counts,
                "top_companies": top_companies,
                "top_skills": top_skills,
                "period_days": days
            }
    
    def get_skill_trends(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending skills based on job demand."""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT skill_name, job_count, first_seen, last_seen
                FROM skills_tracking
                ORDER BY job_count DESC, last_seen DESC
                LIMIT ?
            """, (limit,))
            
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def close(self):
        """Close database connection (not needed for SQLite with context manager)."""
        pass
