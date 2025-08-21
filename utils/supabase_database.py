"""
Supabase database adapter for the job application system.
"""

import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import create_client, Client
from config import Config

class SupabaseDatabase:
    """Supabase database for tracking job applications."""
    
    def __init__(self):
        if not Config.SUPABASE_URL or not Config.SUPABASE_ANON_KEY:
            raise ValueError("Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY.")
        
        self.supabase: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_ANON_KEY
        )
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables via Supabase migrations."""
        # Tables will be created via Supabase dashboard or migrations
        # This method ensures the client is working
        try:
            # Test connection by checking if tables exist
            self.supabase.table("applications").select("id").limit(1).execute()
        except Exception as e:
            print(f"Warning: Could not connect to applications table: {e}")
            print("Please ensure your Supabase database has the required tables created.")
    
    def save_application(self, application_data: Dict[str, Any]) -> int:
        """Save job application data."""
        
        data = {
            "session_id": application_data.get("session_id", ""),
            "job_id": application_data.get("job_id", ""),
            "job_title": application_data.get("job_title", ""),
            "company_name": application_data.get("company_name", ""),
            "job_url": application_data.get("job_url", ""),
            "application_status": application_data.get("application_status", ""),
            "application_timestamp": application_data.get("application_timestamp", datetime.now().isoformat()),
            "resume_path": application_data.get("resume_path", ""),
            "cover_letter_preview": application_data.get("cover_letter_preview", "")[:500],
            "job_data": application_data.get("job_data", {}),
            "skill_analysis": application_data.get("skill_analysis", {}),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            result = self.supabase.table("applications").insert(data).execute()
            # Handle Supabase client response format
            if result.data and len(result.data) > 0:
                return result.data[0]["id"]
            else:
                return None
        except Exception as e:
            print(f"Error saving application: {e}")
            return None
    
    def save_workflow_session(self, session_data: Dict[str, Any]) -> None:
        """Save workflow session data."""
        
        data = {
            "session_id": session_data.get("session_id", ""),
            "start_time": session_data.get("start_time", ""),
            "end_time": session_data.get("end_time", ""),
            "status": session_data.get("status", ""),
            "input_parameters": session_data.get("input_parameters", {}),
            "final_results": session_data.get("final_results", {}),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            self.supabase.table("workflow_sessions").upsert(data).execute()
        except Exception as e:
            print(f"Error saving workflow session: {e}")
    
    def track_skill(self, skill_name: str) -> None:
        """Track a skill mention."""
        
        try:
            # Check if skill exists
            result = self.supabase.table("skills_tracking").select("*").eq("skill_name", skill_name).execute()
            
            if result.data:
                # Update existing skill
                skill_id = result.data[0]["id"]
                current_count = result.data[0]["job_count"]
                self.supabase.table("skills_tracking").update({
                    "job_count": current_count + 1,
                    "last_seen": datetime.now().isoformat()
                }).eq("id", skill_id).execute()
            else:
                # Insert new skill
                self.supabase.table("skills_tracking").insert({
                    "skill_name": skill_name,
                    "job_count": 1,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat()
                }).execute()
        except Exception as e:
            print(f"Error tracking skill: {e}")
    
    def get_applications_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a session."""
        
        try:
            result = self.supabase.table("applications").select("*").eq("session_id", session_id).order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting applications: {e}")
            return []
    
    def get_application_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get application statistics for the last N days."""
        
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Total applications
            total_result = self.supabase.table("applications").select("id", count="exact").gte("created_at", cutoff_date.isoformat()).execute()
            total_applications = total_result.count if hasattr(total_result, 'count') and total_result.count else 0
            
            # Applications by status
            status_result = self.supabase.table("applications").select("application_status, id").gte("created_at", cutoff_date.isoformat()).execute()
            status_counts = {}
            for app in status_result.data:
                status = app["application_status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Top companies
            companies_result = self.supabase.table("applications").select("company_name, id").gte("created_at", cutoff_date.isoformat()).execute()
            company_counts = {}
            for app in companies_result.data:
                company = app["company_name"]
                company_counts[company] = company_counts.get(company, 0) + 1
            
            top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Top skills
            skills_result = self.supabase.table("skills_tracking").select("skill_name, job_count").order("job_count", desc=True).limit(10).execute()
            top_skills = [(skill["skill_name"], skill["job_count"]) for skill in skills_result.data] if skills_result.data else []
            
            return {
                "total_applications": total_applications,
                "applications_by_status": status_counts,
                "top_companies": top_companies,
                "top_skills": top_skills,
                "period_days": days
            }
        except Exception as e:
            print(f"Error getting application statistics: {e}")
            return {
                "total_applications": 0,
                "applications_by_status": {},
                "top_companies": [],
                "top_skills": [],
                "period_days": days
            }
    
    def get_skill_trends(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get trending skills based on job demand."""
        
        try:
            result = self.supabase.table("skills_tracking").select("*").order("job_count", desc=True).order("last_seen", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting skill trends: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        try:
            # Sign out from Supabase auth if needed
            self.supabase.auth.sign_out()
        except:
            pass
