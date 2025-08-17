"""
Report generation utilities for job application analytics.
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
from utils.database import ApplicationDatabase
from config import Config

class ReportGenerator:
    """Generate various reports and analytics for job applications."""
    
    def __init__(self, db_path: str = None):
        self.db = ApplicationDatabase(db_path)
        self.report_dir = os.path.join(Config.APPLICATION_LOG_DIR, "reports")
        os.makedirs(self.report_dir, exist_ok=True)
    
    def generate_session_report(self, session_id: str) -> Dict[str, Any]:
        """Generate detailed report for a specific session."""
        
        applications = self.db.get_applications_by_session(session_id)
        
        if not applications:
            return {"error": "No applications found for session"}
        
        # Calculate metrics
        total_apps = len(applications)
        successful_apps = len([app for app in applications if app.get("application_status") == "success"])
        failed_apps = len([app for app in applications if app.get("application_status") == "error"])
        skipped_apps = total_apps - successful_apps - failed_apps
        
        success_rate = (successful_apps / total_apps * 100) if total_apps > 0 else 0
        
        # Extract companies and job titles
        companies = list(set([app.get("company_name", "") for app in applications if app.get("company_name")]))
        job_titles = list(set([app.get("job_title", "") for app in applications if app.get("job_title")]))
        
        # Skill analysis
        all_skills = []
        for app in applications:
            skill_analysis = app.get("skill_analysis", {})
            if isinstance(skill_analysis, dict):
                required_skills = skill_analysis.get("required_skills", [])
                for skill in required_skills:
                    if isinstance(skill, dict):
                        all_skills.append(skill.get("skill", ""))
                    else:
                        all_skills.append(str(skill))
        
        from collections import Counter
        skill_counts = Counter(all_skills)
        top_skills = skill_counts.most_common(10)
        
        # Timeline analysis
        app_timeline = []
        for app in applications:
            timestamp = app.get("application_timestamp", app.get("created_at", ""))
            status = app.get("application_status", "unknown")
            app_timeline.append({"timestamp": timestamp, "status": status})
        
        app_timeline.sort(key=lambda x: x["timestamp"])
        
        report = {
            "session_id": session_id,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_applications": total_apps,
                "successful_applications": successful_apps,
                "failed_applications": failed_apps,
                "skipped_applications": skipped_apps,
                "success_rate": round(success_rate, 2)
            },
            "targeting": {
                "companies_applied": len(companies),
                "unique_job_titles": len(job_titles),
                "company_list": companies[:10],  # Top 10 companies
                "job_title_list": job_titles[:10]  # Top 10 job titles
            },
            "skills_analysis": {
                "total_unique_skills": len(skill_counts),
                "top_required_skills": top_skills,
                "skill_diversity_score": len(skill_counts) / total_apps if total_apps > 0 else 0
            },
            "timeline": app_timeline,
            "recommendations": self._generate_session_recommendations(
                success_rate, total_apps, top_skills, companies
            )
        }
        
        # Save report
        report_file = os.path.join(self.report_dir, f"session_report_{session_id}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly performance report."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        stats = self.db.get_application_statistics(days=7)
        skill_trends = self.db.get_skill_trends(limit=15)
        
        # Calculate daily application counts
        daily_counts = self._get_daily_application_counts(start_date, end_date)
        
        report = {
            "report_type": "weekly",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "statistics": stats,
            "daily_breakdown": daily_counts,
            "skill_trends": skill_trends,
            "insights": self._generate_weekly_insights(stats, daily_counts, skill_trends)
        }
        
        # Save report
        report_file = os.path.join(self.report_dir, f"weekly_report_{end_date.strftime('%Y%m%d')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def generate_skill_gap_report(self, target_role: str = "") -> Dict[str, Any]:
        """Generate skill gap analysis report."""
        
        skill_trends = self.db.get_skill_trends(limit=50)
        
        # Categorize skills
        skill_categories = {
            "programming_languages": [],
            "frameworks": [],
            "databases": [],
            "cloud_platforms": [],
            "tools": [],
            "other": []
        }
        
        # Simple categorization (would be better with ML or predefined mappings)
        programming_langs = ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust"]
        frameworks = ["react", "angular", "vue", "django", "flask", "spring", "express"]
        databases = ["mysql", "postgresql", "mongodb", "redis", "elasticsearch"]
        cloud_platforms = ["aws", "azure", "gcp", "docker", "kubernetes"]
        tools = ["git", "jira", "jenkins", "gitlab"]
        
        for skill_data in skill_trends:
            skill_name = skill_data["skill_name"].lower()
            
            if any(lang in skill_name for lang in programming_langs):
                skill_categories["programming_languages"].append(skill_data)
            elif any(fw in skill_name for fw in frameworks):
                skill_categories["frameworks"].append(skill_data)
            elif any(db in skill_name for db in databases):
                skill_categories["databases"].append(skill_data)
            elif any(cloud in skill_name for cloud in cloud_platforms):
                skill_categories["cloud_platforms"].append(skill_data)
            elif any(tool in skill_name for tool in tools):
                skill_categories["tools"].append(skill_data)
            else:
                skill_categories["other"].append(skill_data)
        
        # Generate recommendations
        recommendations = []
        
        # Find top skills in each category
        for category, skills in skill_categories.items():
            if skills:
                top_skill = max(skills, key=lambda x: x["job_count"])
                recommendations.append({
                    "category": category,
                    "top_skill": top_skill["skill_name"],
                    "demand_count": top_skill["job_count"],
                    "recommendation": f"Consider learning {top_skill['skill_name']} - high demand in {category.replace('_', ' ')}"
                })
        
        report = {
            "report_type": "skill_gap_analysis",
            "target_role": target_role,
            "generated_at": datetime.now().isoformat(),
            "skill_categories": skill_categories,
            "recommendations": recommendations,
            "market_insights": self._generate_market_insights(skill_trends)
        }
        
        # Save report
        report_file = os.path.join(self.report_dir, f"skill_gap_report_{datetime.now().strftime('%Y%m%d')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _get_daily_application_counts(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get daily application counts for a date range."""
        
        # This is a simplified version - would need more complex SQL for accurate daily counts
        daily_counts = []
        current_date = start_date
        
        while current_date <= end_date:
            # Placeholder data - in real implementation, query database for each day
            daily_counts.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "applications": 0,  # Would be actual count from database
                "success_rate": 0.0
            })
            current_date += timedelta(days=1)
        
        return daily_counts
    
    def _generate_session_recommendations(self, success_rate: float, total_apps: int, 
                                        top_skills: List, companies: List) -> List[str]:
        """Generate recommendations for a specific session."""
        
        recommendations = []
        
        if success_rate < 30:
            recommendations.append("Low success rate - consider improving resume content and targeting")
        elif success_rate < 60:
            recommendations.append("Moderate success rate - focus on better job-skill matching")
        else:
            recommendations.append("Good success rate - maintain current strategy")
        
        if total_apps < 5:
            recommendations.append("Increase application volume for better results")
        elif total_apps > 50:
            recommendations.append("Consider focusing on quality over quantity")
        
        if len(companies) < 3:
            recommendations.append("Diversify applications across more companies")
        
        if top_skills:
            top_skill = top_skills[0][0]
            recommendations.append(f"Focus on roles requiring {top_skill} - it's highly demanded")
        
        return recommendations
    
    def _generate_weekly_insights(self, stats: Dict[str, Any], daily_counts: List, 
                                skill_trends: List) -> List[str]:
        """Generate insights for weekly report."""
        
        insights = []
        
        total_apps = stats.get("total_applications", 0)
        if total_apps > 0:
            insights.append(f"Applied to {total_apps} jobs this week")
        
        status_counts = stats.get("applications_by_status", {})
        success_count = status_counts.get("success", 0)
        if success_count > 0:
            insights.append(f"{success_count} successful applications submitted")
        
        top_companies = stats.get("top_companies", [])
        if top_companies:
            top_company = top_companies[0][0]
            insights.append(f"Most applications to: {top_company}")
        
        if skill_trends:
            trending_skill = skill_trends[0]["skill_name"]
            insights.append(f"Trending skill: {trending_skill}")
        
        return insights
    
    def _generate_market_insights(self, skill_trends: List) -> List[str]:
        """Generate market insights from skill trends."""
        
        insights = []
        
        if skill_trends:
            # Most demanded skill
            top_skill = skill_trends[0]
            insights.append(f"Most in-demand skill: {top_skill['skill_name']} ({top_skill['job_count']} jobs)")
            
            # Emerging skills (recently seen)
            recent_skills = [skill for skill in skill_trends if skill["job_count"] >= 3]
            if recent_skills:
                insights.append(f"Consistently demanded skills: {len(recent_skills)} skills appear in 3+ jobs")
            
            # Skill diversity
            total_skills = len(skill_trends)
            insights.append(f"Market skill diversity: {total_skills} unique skills tracked")
        
        return insights
    
    def create_visual_report(self, session_id: str) -> str:
        """Create visual charts for a session report."""
        
        try:
            applications = self.db.get_applications_by_session(session_id)
            
            if not applications:
                return "No data available for visualization"
            
            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Job Application Report - Session {session_id}', fontsize=16)
            
            # 1. Application Status Pie Chart
            status_counts = {}
            for app in applications:
                status = app.get("application_status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                ax1.pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%')
                ax1.set_title('Application Status Distribution')
            
            # 2. Companies Bar Chart
            company_counts = {}
            for app in applications:
                company = app.get("company_name", "Unknown")[:20]  # Truncate long names
                company_counts[company] = company_counts.get(company, 0) + 1
            
            if company_counts:
                companies = list(company_counts.keys())[:10]  # Top 10
                counts = [company_counts[c] for c in companies]
                ax2.bar(range(len(companies)), counts)
                ax2.set_xticks(range(len(companies)))
                ax2.set_xticklabels(companies, rotation=45, ha='right')
                ax2.set_title('Applications by Company')
                ax2.set_ylabel('Number of Applications')
            
            # 3. Timeline (simplified)
            timestamps = []
            for app in applications:
                timestamp = app.get("application_timestamp", app.get("created_at", ""))
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamps.append(dt)
                    except:
                        pass
            
            if timestamps:
                timestamps.sort()
                hours = [(ts - timestamps[0]).total_seconds() / 3600 for ts in timestamps]
                ax3.plot(hours, range(1, len(timestamps) + 1), marker='o')
                ax3.set_title('Application Timeline')
                ax3.set_xlabel('Hours from Start')
                ax3.set_ylabel('Cumulative Applications')
            
            # 4. Skills Word Cloud (simplified bar chart)
            all_skills = []
            for app in applications:
                skill_analysis = app.get("skill_analysis", {})
                if isinstance(skill_analysis, dict):
                    required_skills = skill_analysis.get("required_skills", [])
                    for skill in required_skills:
                        if isinstance(skill, dict):
                            all_skills.append(skill.get("skill", ""))
            
            if all_skills:
                from collections import Counter
                skill_counts = Counter(all_skills)
                top_skills = skill_counts.most_common(10)
                
                skills = [skill for skill, count in top_skills]
                counts = [count for skill, count in top_skills]
                
                ax4.barh(range(len(skills)), counts)
                ax4.set_yticks(range(len(skills)))
                ax4.set_yticklabels(skills)
                ax4.set_title('Top Required Skills')
                ax4.set_xlabel('Frequency')
            
            plt.tight_layout()
            
            # Save chart
            chart_file = os.path.join(self.report_dir, f"visual_report_{session_id}.png")
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_file
            
        except Exception as e:
            return f"Error creating visual report: {str(e)}"
