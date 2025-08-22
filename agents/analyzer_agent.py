"""
Analyzer Agent - Job description analysis and skills extraction.
"""

import asyncio
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentState
from utils.logger import setup_logger
import re
import json

class AnalyzerAgent(BaseAgent):
    """Analyzer agent that analyzes job descriptions and extracts required skills and requirements."""
    
    def __init__(self):
        super().__init__("AnalyzerAgent")
        self.logger = setup_logger("AnalyzerAgent")
        
        # Common skill categories and keywords
        self.skill_categories = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'php', 'ruby',
                'swift', 'kotlin', 'scala', 'r', 'matlab', 'sql', 'html', 'css', 'bash', 'powershell'
            ],
            'frameworks': [
                'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring', 'express', 'laravel',
                'asp.net', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'jquery'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb',
                'sqlite', 'oracle', 'sql server', 'firebase', 'supabase'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'heroku', 'digitalocean', 'linode', 'vultr', 'cloudflare'
            ],
            'tools': [
                'git', 'docker', 'kubernetes', 'jenkins', 'github actions', 'gitlab ci', 'jira',
                'confluence', 'slack', 'teams', 'zoom', 'figma', 'adobe creative suite'
            ],
            'methodologies': [
                'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd', 'lean'
            ]
        }
        
        # Experience level indicators
        self.experience_levels = {
            'entry_level': ['entry', 'junior', '0-2', '1-2', '2+', 'recent graduate', 'new grad'],
            'mid_level': ['mid', 'intermediate', '3-5', '4-6', '5+', 'experienced'],
            'senior_level': ['senior', 'lead', 'principal', '6+', '8+', '10+', 'expert'],
            'management': ['manager', 'director', 'head', 'vp', 'cto', 'leadership']
        }
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the analyzer agent workflow."""
        
        try:
            self.log_action("STARTING", "Starting job description analysis workflow")
            
            # Validate input
            if not self._validate_input(state):
                state.error = "Missing required input for analysis"
                return state
            
            # Analyze job descriptions
            analysis_results = await self._analyze_job_descriptions(state)
            
            # Extract skills and requirements
            skills_analysis = await self._extract_skills_and_requirements(state)
            
            # Generate analysis summary
            analysis_summary = self._generate_analysis_summary(analysis_results, skills_analysis)
            
            # Update state with analysis results
            state.jd_analysis = analysis_results
            state.skills_analysis = skills_analysis
            state.analysis_summary = analysis_summary
            
            self.log_action("SUCCESS", f"Analysis completed for {len(analysis_results)} job descriptions")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Analyzer agent failed: {str(e)}")
            state.error = f"Analyzer error: {str(e)}"
            return state
    
    def _validate_input(self, state: AgentState) -> bool:
        """Validate that required input fields are present."""
        
        required_fields = ['extracted_jds']
        return self.validate_input(state, required_fields)
    
    async def _analyze_job_descriptions(self, state: AgentState) -> List[Dict[str, Any]]:
        """Analyze individual job descriptions."""
        
        extracted_jds = getattr(state, 'extracted_jds', [])
        analysis_results = []
        
        for jd in extracted_jds:
            try:
                analysis = {
                    'job_id': jd.get('job_id'),
                    'title': jd.get('title'),
                    'company': jd.get('company'),
                    'analysis': {
                        'complexity_score': self._calculate_complexity_score(jd.get('description', '')),
                        'experience_level': self._identify_experience_level(jd.get('description', '')),
                        'required_skills': self._extract_required_skills(jd.get('description', '')),
                        'preferred_skills': self._extract_preferred_skills(jd.get('description', '')),
                        'responsibilities': self._extract_responsibilities(jd.get('description', '')),
                        'qualifications': self._extract_qualifications(jd.get('description', '')),
                        'benefits': self._extract_benefits(jd.get('description', '')),
                        'company_culture': self._analyze_company_culture(jd.get('description', ''))
                    }
                }
                
                analysis_results.append(analysis)
                
            except Exception as e:
                self.log_action("WARNING", f"Failed to analyze JD for job {jd.get('job_id', 'Unknown')}: {str(e)}")
                continue
        
        return analysis_results
    
    async def _extract_skills_and_requirements(self, state: AgentState) -> Dict[str, Any]:
        """Extract and categorize skills and requirements across all jobs."""
        
        extracted_jds = getattr(state, 'extracted_jds', [])
        
        all_required_skills = set()
        all_preferred_skills = set()
        skill_frequency = {}
        category_breakdown = {}
        
        for jd in extracted_jds:
            description = jd.get('description', '').lower()
            
            # Extract required skills
            required = self._extract_required_skills(description)
            all_required_skills.update(required)
            
            # Extract preferred skills
            preferred = self._extract_preferred_skills(description)
            all_preferred_skills.update(preferred)
            
            # Count skill frequency
            for skill in required + preferred:
                skill_frequency[skill] = skill_frequency.get(skill, 0) + 1
        
        # Categorize skills
        for skill in all_required_skills | all_preferred_skills:
            category = self._categorize_skill(skill)
            if category not in category_breakdown:
                category_breakdown[category] = []
            category_breakdown[category].append(skill)
        
        return {
            'required_skills': list(all_required_skills),
            'preferred_skills': list(all_preferred_skills),
            'skill_frequency': skill_frequency,
            'category_breakdown': category_breakdown,
            'total_unique_skills': len(all_required_skills | all_preferred_skills)
        }
    
    def _calculate_complexity_score(self, description: str) -> float:
        """Calculate a complexity score for the job description."""
        
        if not description:
            return 0.0
        
        # Factors that increase complexity
        complexity_indicators = [
            'senior', 'lead', 'principal', 'architect', 'expert', 'advanced',
            'complex', 'challenging', 'strategic', 'leadership', 'management',
            'mentor', 'coach', 'guide', 'oversee', 'coordinate'
        ]
        
        # Factors that decrease complexity
        simplicity_indicators = [
            'entry', 'junior', 'basic', 'simple', 'routine', 'assist',
            'support', 'learn', 'training', 'guidance', 'supervision'
        ]
        
        description_lower = description.lower()
        
        complexity_score = 0.0
        complexity_score += sum(description_lower.count(indicator) * 0.1 for indicator in complexity_indicators)
        complexity_score -= sum(description_lower.count(indicator) * 0.05 for indicator in simplicity_indicators)
        
        # Normalize to 0-10 scale
        complexity_score = max(0.0, min(10.0, complexity_score + 5.0))
        
        return round(complexity_score, 2)
    
    def _identify_experience_level(self, description: str) -> str:
        """Identify the experience level required for the job."""
        
        if not description:
            return 'unknown'
        
        description_lower = description.lower()
        
        for level, indicators in self.experience_levels.items():
            if any(indicator in description_lower for indicator in indicators):
                return level
        
        return 'unknown'
    
    def _extract_required_skills(self, description: str) -> List[str]:
        """Extract required skills from job description."""
        
        if not description:
            return []
        
        required_skills = []
        description_lower = description.lower()
        
        # Look for required skills patterns
        required_patterns = [
            r'required[:\s]+([^.\n]+)',
            r'must have[:\s]+([^.\n]+)',
            r'requirements[:\s]+([^.\n]+)',
            r'qualifications[:\s]+([^.\n]+)'
        ]
        
        for pattern in required_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                skills = self._extract_skills_from_text(match)
                required_skills.extend(skills)
        
        return list(set(required_skills))
    
    def _extract_preferred_skills(self, description: str) -> List[str]:
        """Extract preferred skills from job description."""
        
        if not description:
            return []
        
        preferred_skills = []
        description_lower = description.lower()
        
        # Look for preferred skills patterns
        preferred_patterns = [
            r'preferred[:\s]+([^.\n]+)',
            r'nice to have[:\s]+([^.\n]+)',
            r'bonus[:\s]+([^.\n]+)',
            r'plus[:\s]+([^.\n]+)'
        ]
        
        for pattern in preferred_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                skills = self._extract_skills_from_text(match)
                preferred_skills.extend(skills)
        
        return list(set(preferred_skills))
    
    def _extract_responsibilities(self, description: str) -> List[str]:
        """Extract job responsibilities from description."""
        
        if not description:
            return []
        
        responsibilities = []
        description_lower = description.lower()
        
        # Look for responsibilities section
        resp_patterns = [
            r'responsibilities[:\s]+([^.\n]+)',
            r'duties[:\s]+([^.\n]+)',
            r'what you\'ll do[:\s]+([^.\n]+)',
            r'key responsibilities[:\s]+([^.\n]+)'
        ]
        
        for pattern in resp_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                responsibilities.append(match.strip())
        
        return responsibilities
    
    def _extract_qualifications(self, description: str) -> List[str]:
        """Extract qualifications from job description."""
        
        if not description:
            return []
        
        qualifications = []
        description_lower = description.lower()
        
        # Look for qualifications section
        qual_patterns = [
            r'qualifications[:\s]+([^.\n]+)',
            r'requirements[:\s]+([^.\n]+)',
            r'education[:\s]+([^.\n]+)',
            r'experience[:\s]+([^.\n]+)'
        ]
        
        for pattern in qual_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                qualifications.append(match.strip())
        
        return qualifications
    
    def _extract_benefits(self, description: str) -> List[str]:
        """Extract benefits from job description."""
        
        if not description:
            return []
        
        benefits = []
        description_lower = description.lower()
        
        # Look for benefits section
        benefit_patterns = [
            r'benefits[:\s]+([^.\n]+)',
            r'perks[:\s]+([^.\n]+)',
            r'what we offer[:\s]+([^.\n]+)',
            r'compensation[:\s]+([^.\n]+)'
        ]
        
        for pattern in benefit_patterns:
            matches = re.findall(pattern, description_lower)
            for match in matches:
                benefits.append(match.strip())
        
        return benefits
    
    def _analyze_company_culture(self, description: str) -> Dict[str, Any]:
        """Analyze company culture indicators from job description."""
        
        if not description:
            return {}
        
        description_lower = description.lower()
        
        culture_indicators = {
            'remote_friendly': ['remote', 'work from home', 'wfh', 'hybrid', 'flexible location'],
            'collaborative': ['team', 'collaborate', 'collaboration', 'partnership', 'coordinate'],
            'innovative': ['innovate', 'innovation', 'creative', 'cutting-edge', 'latest technology'],
            'fast_paced': ['fast-paced', 'dynamic', 'agile', 'quick', 'rapid'],
            'learning_focused': ['learn', 'learning', 'growth', 'development', 'training'],
            'diverse': ['diversity', 'inclusive', 'inclusion', 'equal opportunity', 'diverse team']
        }
        
        culture_analysis = {}
        for aspect, indicators in culture_indicators.items():
            culture_analysis[aspect] = any(indicator in description_lower for indicator in indicators)
        
        return culture_analysis
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract individual skills from text."""
        
        skills = []
        text_lower = text.lower()
        
        # Check each skill category
        for category, skill_list in self.skill_categories.items():
            for skill in skill_list:
                if skill in text_lower:
                    skills.append(skill)
        
        # Also look for custom skills mentioned
        # This is a simplified approach - in practice, you might use NLP or ML
        custom_skills = re.findall(r'\b[a-zA-Z][a-zA-Z0-9\s&+.-]+\b', text)
        for skill in custom_skills:
            skill_clean = skill.strip().lower()
            if len(skill_clean) > 2 and skill_clean not in skills:
                skills.append(skill_clean)
        
        return skills
    
    def _categorize_skill(self, skill: str) -> str:
        """Categorize a skill into predefined categories."""
        
        skill_lower = skill.lower()
        
        for category, skills in self.skill_categories.items():
            if skill_lower in skills:
                return category
        
        return 'other'
    
    def _generate_analysis_summary(self, analysis_results: List[Dict], skills_analysis: Dict) -> Dict[str, Any]:
        """Generate a comprehensive analysis summary."""
        
        total_jobs = len(analysis_results)
        if total_jobs == 0:
            return {"error": "No jobs analyzed"}
        
        # Calculate averages
        avg_complexity = sum(
            job['analysis']['complexity_score'] 
            for job in analysis_results 
            if 'complexity_score' in job['analysis']
        ) / total_jobs
        
        # Most common experience level
        experience_counts = {}
        for job in analysis_results:
            level = job['analysis'].get('experience_level', 'unknown')
            experience_counts[level] = experience_counts.get(level, 0) + 1
        
        most_common_level = max(experience_counts.items(), key=lambda x: x[1])[0] if experience_counts else 'unknown'
        
        # Top skills
        top_skills = sorted(
            skills_analysis.get('skill_frequency', {}).items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_jobs_analyzed': total_jobs,
            'average_complexity_score': round(avg_complexity, 2),
            'most_common_experience_level': most_common_level,
            'total_unique_skills': skills_analysis.get('total_unique_skills', 0),
            'top_required_skills': top_skills,
            'skill_categories': skills_analysis.get('category_breakdown', {}),
            'analysis_timestamp': asyncio.get_event_loop().time()
        }
    
    async def close(self):
        """Clean up resources."""
        
        self.log_action("INFO", "Analyzer agent resources cleaned up")
