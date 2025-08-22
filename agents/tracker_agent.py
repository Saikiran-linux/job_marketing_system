"""
Tracker Agent - Application status monitoring and tracking.
"""

import asyncio
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentState
from utils.logger import setup_logger
from utils.database import ApplicationDatabase
from datetime import datetime, timedelta
import json

class TrackerAgent(BaseAgent):
    """Tracker agent that monitors application status and tracks job application progress."""
    
    def __init__(self):
        super().__init__("TrackerAgent")
        self.logger = setup_logger("TrackerAgent")
        self.db_manager = ApplicationDatabase()
        
        # Application status definitions
        self.application_statuses = {
            'applied': 'Application submitted',
            'under_review': 'Under review by employer',
            'interview_scheduled': 'Interview scheduled',
            'interview_completed': 'Interview completed',
            'offer_received': 'Job offer received',
            'offer_accepted': 'Offer accepted',
            'offer_declined': 'Offer declined',
            'rejected': 'Application rejected',
            'withdrawn': 'Application withdrawn',
            'expired': 'Application expired'
        }
        
        # Tracking intervals
        self.tracking_intervals = {
            'applied': 7,  # Check every 7 days
            'under_review': 3,  # Check every 3 days
            'interview_scheduled': 1,  # Check daily
            'interview_completed': 5,  # Check every 5 days
            'offer_received': 1,  # Check daily
            'offer_accepted': 7,  # Check weekly
            'offer_declined': 7,  # Check weekly
            'rejected': 30,  # Check monthly
            'withdrawn': 30,  # Check monthly
            'expired': 30  # Check monthly
        }
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the tracker agent workflow."""
        
        try:
            self.log_action("STARTING", "Starting application status monitoring workflow")
            
            # Initialize tracking system
            await self._initialize_tracking_system()
            
            # Track existing applications
            tracking_results = await self._track_applications(state)
            
            # Monitor new applications
            monitoring_results = await self._monitor_new_applications(state)
            
            # Generate tracking report
            tracking_report = await self._generate_tracking_report(tracking_results, monitoring_results)
            
            # Update application statuses
            updated_statuses = await self._update_application_statuses(state, tracking_results)
            
            # Set up automated monitoring
            monitoring_schedule = await self._setup_automated_monitoring(state)
            
            # Update state with results
            state.tracking_results = tracking_results
            state.monitoring_results = monitoring_results
            state.tracking_report = tracking_report
            state.updated_statuses = updated_statuses
            state.monitoring_schedule = monitoring_schedule
            
            self.log_action("SUCCESS", "Application status monitoring completed successfully")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Tracker agent failed: {str(e)}")
            state.error = f"Tracker error: {str(e)}"
            return state
    
    async def _initialize_tracking_system(self):
        """Initialize the application tracking system."""
        
        try:
            self.log_action("INFO", "Initializing application tracking system")
            
            # Initialize database tables if they don't exist
            await self.db_manager.initialize_tables()
            
            # Set up tracking configurations
            tracking_config = {
                'auto_monitoring_enabled': True,
                'notification_enabled': True,
                'status_update_frequency': 'daily',
                'report_generation_frequency': 'weekly',
                'data_retention_days': 365
            }
            
            await self.db_manager.save_config('tracking', tracking_config)
            
            self.log_action("SUCCESS", "Tracking system initialized successfully")
            
        except Exception as e:
            self.log_action("ERROR", f"Failed to initialize tracking system: {str(e)}")
            raise
    
    async def _track_applications(self, state: AgentState) -> Dict[str, Any]:
        """Track the status of existing job applications."""
        
        try:
            self.log_action("INFO", "Tracking existing applications")
            
            # Get applications from state or database
            applications = getattr(state, 'all_applications', [])
            if not applications:
                # Try to get from database
                applications = await self.db_manager.get_applications()
            
            tracking_results = {
                'total_applications': len(applications),
                'status_breakdown': {},
                'recent_updates': [],
                'follow_up_required': [],
                'success_metrics': {}
            }
            
            # Analyze each application
            for app in applications:
                app_id = app.get('id') or app.get('job_id')
                current_status = app.get('status', 'unknown')
                
                # Update status breakdown
                if current_status not in tracking_results['status_breakdown']:
                    tracking_results['status_breakdown'][current_status] = 0
                tracking_results['status_breakdown'][current_status] += 1
                
                # Check if follow-up is required
                if self._requires_follow_up(app):
                    tracking_results['follow_up_required'].append({
                        'app_id': app_id,
                        'job_title': app.get('job_title', 'Unknown'),
                        'company': app.get('company', 'Unknown'),
                        'status': current_status,
                        'last_updated': app.get('last_updated'),
                        'follow_up_reason': self._get_follow_up_reason(app)
                    })
                
                # Check for recent updates
                if self._has_recent_update(app):
                    tracking_results['recent_updates'].append({
                        'app_id': app_id,
                        'job_title': app.get('job_title', 'Unknown'),
                        'company': app.get('company', 'Unknown'),
                        'status': current_status,
                        'update_type': self._get_update_type(app),
                        'timestamp': app.get('last_updated')
                    })
            
            # Calculate success metrics
            tracking_results['success_metrics'] = self._calculate_success_metrics(applications)
            
            self.log_action("SUCCESS", f"Tracked {len(applications)} applications")
            return tracking_results
            
        except Exception as e:
            self.log_action("ERROR", f"Application tracking failed: {str(e)}")
            raise
    
    async def _monitor_new_applications(self, state: AgentState) -> Dict[str, Any]:
        """Monitor newly submitted applications."""
        
        try:
            self.log_action("INFO", "Monitoring new applications")
            
            # Get new applications from state
            new_applications = getattr(state, 'new_applications', [])
            if not new_applications:
                # Check database for recent applications
                new_applications = await self.db_manager.get_recent_applications(hours=24)
            
            monitoring_results = {
                'new_applications_count': len(new_applications),
                'applications_added': [],
                'initial_status_set': [],
                'monitoring_scheduled': []
            }
            
            for app in new_applications:
                app_id = app.get('id') or app.get('job_id')
                
                # Add to tracking system
                tracking_entry = {
                    'app_id': app_id,
                    'job_title': app.get('job_title', 'Unknown'),
                    'company': app.get('company', 'Unknown'),
                    'status': 'applied',
                    'applied_date': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'source': app.get('source', 'unknown'),
                    'url': app.get('url', ''),
                    'resume_used': app.get('resume_path', ''),
                    'auto_apply': app.get('auto_apply', False)
                }
                
                # Save to database
                await self.db_manager.save_application(tracking_entry)
                
                monitoring_results['applications_added'].append(tracking_entry)
                monitoring_results['initial_status_set'].append({
                    'app_id': app_id,
                    'status': 'applied',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Schedule monitoring
                monitoring_schedule = self._create_monitoring_schedule(app_id, 'applied')
                await self.db_manager.save_monitoring_schedule(monitoring_schedule)
                
                monitoring_results['monitoring_scheduled'].append(monitoring_schedule)
            
            self.log_action("SUCCESS", f"Monitoring set up for {len(new_applications)} new applications")
            return monitoring_results
            
        except Exception as e:
            self.log_action("ERROR", f"New application monitoring failed: {str(e)}")
            raise
    
    async def _generate_tracking_report(self, tracking_results: Dict, monitoring_results: Dict) -> Dict[str, Any]:
        """Generate a comprehensive tracking report."""
        
        try:
            self.log_action("INFO", "Generating tracking report")
            
            report = {
                'report_generated': datetime.now().isoformat(),
                'summary': {
                    'total_applications': tracking_results.get('total_applications', 0),
                    'new_applications': monitoring_results.get('new_applications_count', 0),
                    'active_applications': self._count_active_applications(tracking_results),
                    'success_rate': tracking_results.get('success_metrics', {}).get('success_rate', 0)
                },
                'status_overview': tracking_results.get('status_breakdown', {}),
                'recent_activity': {
                    'recent_updates': tracking_results.get('recent_updates', []),
                    'follow_up_required': tracking_results.get('follow_up_required', [])
                },
                'performance_metrics': tracking_results.get('success_metrics', {}),
                'recommendations': self._generate_tracking_recommendations(tracking_results, monitoring_results)
            }
            
            # Save report to database
            await self.db_manager.save_report('tracking', report)
            
            self.log_action("SUCCESS", "Tracking report generated successfully")
            return report
            
        except Exception as e:
            self.log_action("ERROR", f"Report generation failed: {str(e)}")
            raise
    
    async def _update_application_statuses(self, state: AgentState, tracking_results: Dict) -> List[Dict]:
        """Update application statuses based on tracking results."""
        
        try:
            self.log_action("INFO", "Updating application statuses")
            
            follow_up_apps = tracking_results.get('follow_up_required', [])
            updated_statuses = []
            
            for app in follow_up_apps:
                app_id = app['app_id']
                current_status = app['status']
                
                # Determine new status based on follow-up
                new_status = self._determine_new_status(app)
                
                if new_status != current_status:
                    # Update status in database
                    await self.db_manager.update_application_status(app_id, new_status)
                    
                    updated_statuses.append({
                        'app_id': app_id,
                        'old_status': current_status,
                        'new_status': new_status,
                        'update_reason': self._get_status_update_reason(app, new_status),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Update monitoring schedule
                    new_schedule = self._create_monitoring_schedule(app_id, new_status)
                    await self.db_manager.update_monitoring_schedule(app_id, new_schedule)
            
            self.log_action("SUCCESS", f"Updated {len(updated_statuses)} application statuses")
            return updated_statuses
            
        except Exception as e:
            self.log_action("ERROR", f"Status update failed: {str(e)}")
            raise
    
    async def _setup_automated_monitoring(self, state: AgentState) -> Dict[str, Any]:
        """Set up automated monitoring for all applications."""
        
        try:
            self.log_action("INFO", "Setting up automated monitoring")
            
            # Get all applications
            applications = await self.db_manager.get_applications()
            
            monitoring_schedule = {
                'total_scheduled': 0,
                'monitoring_configs': [],
                'next_check_time': None,
                'automation_enabled': True
            }
            
            for app in applications:
                app_id = app.get('id') or app.get('job_id')
                current_status = app.get('status', 'applied')
                
                # Create monitoring configuration
                config = self._create_monitoring_schedule(app_id, current_status)
                await self.db_manager.save_monitoring_schedule(config)
                
                monitoring_schedule['monitoring_configs'].append(config)
                monitoring_schedule['total_scheduled'] += 1
            
            # Set next check time
            monitoring_schedule['next_check_time'] = self._calculate_next_check_time()
            
            # Save monitoring configuration
            await self.db_manager.save_config('monitoring', monitoring_schedule)
            
            self.log_action("SUCCESS", f"Automated monitoring set up for {len(applications)} applications")
            return monitoring_schedule
            
        except Exception as e:
            self.log_action("ERROR", f"Automated monitoring setup failed: {str(e)}")
            raise
    
    def _requires_follow_up(self, app: Dict) -> bool:
        """Check if an application requires follow-up."""
        
        current_status = app.get('status', 'unknown')
        last_updated = app.get('last_updated')
        
        if not last_updated:
            return True
        
        # Parse last updated time
        try:
            if isinstance(last_updated, str):
                last_update = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                last_update = last_updated
            
            # Check if follow-up is needed based on status and time
            days_since_update = (datetime.now() - last_update).days
            max_days = self.tracking_intervals.get(current_status, 7)
            
            return days_since_update >= max_days
            
        except Exception:
            return True
    
    def _get_follow_up_reason(self, app: Dict) -> str:
        """Get the reason why follow-up is required."""
        
        current_status = app.get('status', 'unknown')
        last_updated = app.get('last_updated')
        
        if not last_updated:
            return "No last update timestamp"
        
        try:
            if isinstance(last_updated, str):
                last_update = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                last_update = last_updated
            
            days_since_update = (datetime.now() - last_update).days
            max_days = self.tracking_intervals.get(current_status, 7)
            
            if days_since_update >= max_days:
                return f"Status check overdue by {days_since_update - max_days} days"
            else:
                return "Follow-up not required"
                
        except Exception:
            return "Unable to determine follow-up reason"
    
    def _has_recent_update(self, app: Dict) -> bool:
        """Check if an application has been recently updated."""
        
        last_updated = app.get('last_updated')
        if not last_updated:
            return False
        
        try:
            if isinstance(last_updated, str):
                last_update = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            else:
                last_update = last_updated
            
            # Consider updates within last 7 days as recent
            return (datetime.now() - last_update).days <= 7
            
        except Exception:
            return False
    
    def _get_update_type(self, app: Dict) -> str:
        """Get the type of recent update."""
        
        # This would typically analyze the update history
        # For now, return a generic type
        return "status_update"
    
    def _calculate_success_metrics(self, applications: List[Dict]) -> Dict[str, Any]:
        """Calculate success metrics for applications."""
        
        if not applications:
            return {
                'success_rate': 0.0,
                'interview_rate': 0.0,
                'offer_rate': 0.0,
                'average_response_time': 0
            }
        
        total_apps = len(applications)
        successful_apps = len([app for app in applications if app.get('status') in ['offer_received', 'offer_accepted']])
        interview_apps = len([app for app in applications if 'interview' in app.get('status', '')])
        offer_apps = len([app for app in applications if 'offer' in app.get('status', '')])
        
        # Calculate response times (simplified)
        response_times = []
        for app in applications:
            if app.get('applied_date') and app.get('first_response_date'):
                try:
                    applied = datetime.fromisoformat(app['applied_date'].replace('Z', '+00:00'))
                    first_response = datetime.fromisoformat(app['first_response_date'].replace('Z', '+00:00'))
                    response_time = (first_response - applied).days
                    response_times.append(response_time)
                except Exception:
                    continue
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'success_rate': (successful_apps / total_apps) * 100 if total_apps > 0 else 0,
            'interview_rate': (interview_apps / total_apps) * 100 if total_apps > 0 else 0,
            'offer_rate': (offer_apps / total_apps) * 100 if total_apps > 0 else 0,
            'average_response_time': round(avg_response_time, 1)
        }
    
    def _count_active_applications(self, tracking_results: Dict) -> int:
        """Count applications that are still active."""
        
        active_statuses = ['applied', 'under_review', 'interview_scheduled', 'interview_completed', 'offer_received']
        
        status_breakdown = tracking_results.get('status_breakdown', {})
        active_count = sum(status_breakdown.get(status, 0) for status in active_statuses)
        
        return active_count
    
    def _generate_tracking_recommendations(self, tracking_results: Dict, monitoring_results: Dict) -> List[str]:
        """Generate recommendations based on tracking results."""
        
        recommendations = []
        
        # Check follow-up requirements
        follow_up_count = len(tracking_results.get('follow_up_required', []))
        if follow_up_count > 0:
            recommendations.append(f"Follow up on {follow_up_count} applications that require attention")
        
        # Check success rate
        success_rate = tracking_results.get('success_metrics', {}).get('success_rate', 0)
        if success_rate < 10:
            recommendations.append("Consider improving application strategy - success rate is low")
        elif success_rate < 25:
            recommendations.append("Application success rate could be improved with targeted applications")
        
        # Check response time
        avg_response_time = tracking_results.get('success_metrics', {}).get('average_response_time', 0)
        if avg_response_time > 14:
            recommendations.append("Consider following up earlier - average response time is high")
        
        # Check application volume
        total_apps = tracking_results.get('total_applications', 0)
        if total_apps < 10:
            recommendations.append("Increase application volume for better success chances")
        elif total_apps > 100:
            recommendations.append("Focus on quality over quantity - consider more targeted applications")
        
        if not recommendations:
            recommendations.append("Application tracking is healthy - continue current strategy")
        
        return recommendations
    
    def _determine_new_status(self, app: Dict) -> str:
        """Determine the new status for an application based on follow-up."""
        
        current_status = app['status']
        follow_up_reason = app.get('follow_up_reason', '')
        
        # This is a simplified logic - in practice, you might use ML or more complex rules
        if 'overdue' in follow_up_reason.lower():
            if current_status == 'applied':
                return 'under_review'
            elif current_status == 'under_review':
                return 'rejected'  # Assume rejection if no response for too long
            elif current_status == 'interview_scheduled':
                return 'interview_completed'
        
        return current_status
    
    def _get_status_update_reason(self, app: Dict, new_status: str) -> str:
        """Get the reason for a status update."""
        
        old_status = app['status']
        
        if new_status == old_status:
            return "No status change"
        
        if new_status == 'rejected' and old_status in ['applied', 'under_review']:
            return "No response received within expected timeframe"
        elif new_status == 'under_review' and old_status == 'applied':
            return "Follow-up indicated application is being reviewed"
        elif new_status == 'interview_completed' and old_status == 'interview_scheduled':
            return "Interview follow-up completed"
        
        return f"Status updated from {old_status} to {new_status}"
    
    def _create_monitoring_schedule(self, app_id: str, status: str) -> Dict[str, Any]:
        """Create a monitoring schedule for an application."""
        
        interval_days = self.tracking_intervals.get(status, 7)
        next_check = datetime.now() + timedelta(days=interval_days)
        
        return {
            'app_id': app_id,
            'status': status,
            'check_interval_days': interval_days,
            'next_check_time': next_check.isoformat(),
            'last_checked': datetime.now().isoformat(),
            'monitoring_enabled': True
        }
    
    def _calculate_next_check_time(self) -> str:
        """Calculate the next overall check time."""
        
        # Check every day at 9 AM
        next_check = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if next_check <= datetime.now():
            next_check += timedelta(days=1)
        
        return next_check.isoformat()
    
    async def close(self):
        """Clean up resources."""
        
        if hasattr(self.db_manager, 'close'):
            await self.db_manager.close()
        
        self.log_action("INFO", "Tracker agent resources cleaned up")
