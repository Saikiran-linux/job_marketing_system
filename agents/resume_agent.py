"""
Resume Agent - Dynamic resume modification based on job requirements and skills.
"""

import asyncio
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent, AgentState
from utils.logger import setup_logger
from utils.resume_editor import ResumeEditor
import os
import json

class ResumeAgent(BaseAgent):
    """Resume agent that dynamically modifies resumes based on job requirements."""
    
    def __init__(self):
        super().__init__("ResumeAgent")
        self.logger = setup_logger("ResumeAgent")
        self.resume_editor = ResumeEditor()
        
        # Resume modification strategies
        self.modification_strategies = {
            'skills_enhancement': self._enhance_skills_section,
            'experience_optimization': self._optimize_experience_section,
            'summary_customization': self._customize_summary,
            'keyword_optimization': self._optimize_keywords,
            'format_adaptation': self._adapt_format
        }
    
    async def execute(self, state: AgentState) -> AgentState:
        """Execute the resume modification workflow."""
        
        try:
            self.log_action("STARTING", "Starting dynamic resume modification workflow")
            
            # Validate input
            if not self._validate_input(state):
                state.error = "Missing required input for resume modification"
                return state
            
            # Analyze current resume
            resume_analysis = await self._analyze_current_resume(state)
            
            # Generate modification plan
            modification_plan = await self._generate_modification_plan(state, resume_analysis)
            
            # Execute modifications
            modified_resume = await self._execute_modifications(state, modification_plan)
            
            # Validate modifications
            validation_result = await self._validate_modifications(state, modified_resume)
            
            # Update state with results
            state.resume_analysis = resume_analysis
            state.modification_plan = modification_plan
            state.modified_resume = modified_resume
            state.modification_validation = validation_result
            
            self.log_action("SUCCESS", "Resume modification completed successfully")
            return state
            
        except Exception as e:
            self.log_action("ERROR", f"Resume agent failed: {str(e)}")
            state.error = f"Resume agent error: {str(e)}"
            return state
    
    def _validate_input(self, state: AgentState) -> bool:
        """Validate that required input fields are present."""
        
        required_fields = ['resume_path', 'skills_analysis', 'jd_analysis']
        return self.validate_input(state, required_fields)
    
    async def _analyze_current_resume(self, state: AgentState) -> Dict[str, Any]:
        """Analyze the current resume to understand its structure and content."""
        
        try:
            resume_path = state.resume_path
            self.log_action("INFO", f"Analyzing current resume: {resume_path}")
            
            if not os.path.exists(resume_path):
                raise FileNotFoundError(f"Resume file not found: {resume_path}")
            
            # Use resume editor to analyze the resume
            analysis = await self.resume_editor.analyze_resume(resume_path)
            
            # Extract key information
            resume_analysis = {
                'file_path': resume_path,
                'file_size': os.path.getsize(resume_path),
                'file_type': os.path.splitext(resume_path)[1],
                'sections': analysis.get('sections', []),
                'current_skills': analysis.get('skills', []),
                'experience_summary': analysis.get('experience', []),
                'education': analysis.get('education', []),
                'contact_info': analysis.get('contact', {}),
                'overall_strength': analysis.get('strength_score', 0),
                'areas_for_improvement': analysis.get('improvement_areas', [])
            }
            
            self.log_action("SUCCESS", f"Resume analysis completed - {len(resume_analysis['sections'])} sections found")
            return resume_analysis
            
        except Exception as e:
            self.log_action("ERROR", f"Resume analysis failed: {str(e)}")
            raise
    
    async def _generate_modification_plan(self, state: AgentState, resume_analysis: Dict) -> Dict[str, Any]:
        """Generate a comprehensive modification plan based on job requirements."""
        
        try:
            self.log_action("INFO", "Generating resume modification plan")
            
            skills_analysis = state.skills_analysis
            jd_analysis = state.jd_analysis
            current_skills = resume_analysis.get('current_skills', [])
            
            # Identify missing skills
            required_skills = set(skills_analysis.get('required_skills', []))
            preferred_skills = set(skills_analysis.get('preferred_skills', []))
            current_skills_set = set(current_skills)
            
            missing_required = required_skills - current_skills_set
            missing_preferred = preferred_skills - current_skills_set
            
            # Generate modification strategies
            modifications = []
            
            # Skills enhancement
            if missing_required or missing_preferred:
                modifications.append({
                    'type': 'skills_enhancement',
                    'priority': 'high' if missing_required else 'medium',
                    'description': f"Add {len(missing_required)} required and {len(missing_preferred)} preferred skills",
                    'skills_to_add': list(missing_required | missing_preferred),
                    'target_section': 'skills'
                })
            
            # Experience optimization
            if jd_analysis:
                experience_mods = self._plan_experience_modifications(jd_analysis, resume_analysis)
                modifications.extend(experience_mods)
            
            # Summary customization
            if jd_analysis:
                modifications.append({
                    'type': 'summary_customization',
                    'priority': 'medium',
                    'description': 'Customize professional summary for target roles',
                    'target_section': 'summary'
                })
            
            # Keyword optimization
            if skills_analysis.get('skill_frequency'):
                modifications.append({
                    'type': 'keyword_optimization',
                    'priority': 'medium',
                    'description': 'Optimize resume with high-frequency keywords',
                    'keywords': list(skills_analysis['skill_frequency'].keys())[:20],
                    'target_section': 'all'
                })
            
            modification_plan = {
                'total_modifications': len(modifications),
                'high_priority': len([m for m in modifications if m['priority'] == 'high']),
                'medium_priority': len([m for m in modifications if m['priority'] == 'medium']),
                'low_priority': len([m for m in modifications if m['priority'] == 'low']),
                'modifications': modifications,
                'estimated_time': len(modifications) * 2,  # 2 minutes per modification
                'risk_level': 'low' if len(missing_required) == 0 else 'medium'
            }
            
            self.log_action("SUCCESS", f"Modification plan generated: {len(modifications)} modifications planned")
            return modification_plan
            
        except Exception as e:
            self.log_action("ERROR", f"Modification plan generation failed: {str(e)}")
            raise
    
    def _plan_experience_modifications(self, jd_analysis: List[Dict], resume_analysis: Dict) -> List[Dict]:
        """Plan experience section modifications based on job requirements."""
        
        modifications = []
        current_experience = resume_analysis.get('experience_summary', [])
        
        for job_analysis in jd_analysis:
            job_title = job_analysis.get('title', '').lower()
            required_skills = job_analysis['analysis'].get('required_skills', [])
            
            # Find relevant experience entries
            relevant_experience = []
            for exp in current_experience:
                exp_title = exp.get('title', '').lower()
                exp_skills = exp.get('skills', [])
                
                # Check if experience is relevant
                title_relevance = any(keyword in exp_title for keyword in job_title.split())
                skills_relevance = any(skill in exp_skills for skill in required_skills)
                
                if title_relevance or skills_relevance:
                    relevant_experience.append(exp)
            
            if relevant_experience:
                modifications.append({
                    'type': 'experience_optimization',
                    'priority': 'medium',
                    'description': f"Optimize experience for {job_title} role",
                    'target_experience': [exp.get('id') for exp in relevant_experience],
                    'target_section': 'experience',
                    'job_title': job_title
                })
        
        return modifications
    
    async def _execute_modifications(self, state: AgentState, modification_plan: Dict) -> Dict[str, Any]:
        """Execute the planned resume modifications."""
        
        try:
            self.log_action("INFO", "Executing resume modifications")
            
            modifications = modification_plan.get('modifications', [])
            modified_resume = {
                'original_path': state.resume_path,
                'modified_path': None,
                'modifications_applied': [],
                'modification_summary': {},
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Apply modifications in priority order
            high_priority = [m for m in modifications if m['priority'] == 'high']
            medium_priority = [m for m in modifications if m['priority'] == 'medium']
            low_priority = [m for m in modifications if m['priority'] == 'low']
            
            # Execute high priority first
            for mod in high_priority + medium_priority + low_priority:
                try:
                    result = await self._apply_modification(state, mod)
                    if result:
                        modified_resume['modifications_applied'].append({
                            'type': mod['type'],
                            'status': 'success',
                            'result': result
                        })
                    else:
                        modified_resume['modifications_applied'].append({
                            'type': mod['type'],
                            'status': 'failed',
                            'error': 'Modification returned no result'
                        })
                        
                except Exception as e:
                    self.log_action("WARNING", f"Modification {mod['type']} failed: {str(e)}")
                    modified_resume['modifications_applied'].append({
                        'type': mod['type'],
                        'status': 'error',
                        'error': str(e)
                    })
            
            # Generate modification summary
            modified_resume['modification_summary'] = {
                'total_applied': len([m for m in modified_resume['modifications_applied'] if m['status'] == 'success']),
                'total_failed': len([m for m in modified_resume['modifications_applied'] if m['status'] in ['failed', 'error']]),
                'success_rate': len([m for m in modified_resume['modifications_applied'] if m['status'] == 'success']) / len(modifications) if modifications else 0
            }
            
            self.log_action("SUCCESS", f"Modifications executed: {modified_resume['modification_summary']['total_applied']} successful")
            return modified_resume
            
        except Exception as e:
            self.log_action("ERROR", f"Modification execution failed: {str(e)}")
            raise
    
    async def _apply_modification(self, state: AgentState, modification: Dict) -> Optional[Dict]:
        """Apply a specific modification to the resume."""
        
        mod_type = modification.get('type')
        
        if mod_type in self.modification_strategies:
            return await self.modification_strategies[mod_type](state, modification)
        else:
            self.log_action("WARNING", f"Unknown modification type: {mod_type}")
            return None
    
    async def _enhance_skills_section(self, state: AgentState, modification: Dict) -> Dict[str, Any]:
        """Enhance the skills section with missing skills."""
        
        try:
            skills_to_add = modification.get('skills_to_add', [])
            
            if not skills_to_add:
                return {'message': 'No skills to add'}
            
            # Use resume editor to add skills
            result = await self.resume_editor.add_skills(state.resume_path, skills_to_add)
            
            return {
                'skills_added': skills_to_add,
                'skills_count': len(skills_to_add),
                'result': result
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Skills enhancement failed: {str(e)}")
            raise
    
    async def _optimize_experience_section(self, state: AgentState, modification: Dict) -> Dict[str, Any]:
        """Optimize the experience section for specific job requirements."""
        
        try:
            target_experience = modification.get('target_experience', [])
            job_title = modification.get('job_title', '')
            
            if not target_experience:
                return {'message': 'No target experience specified'}
            
            # Use resume editor to optimize experience
            result = await self.resume_editor.optimize_experience(
                state.resume_path, 
                target_experience, 
                job_title
            )
            
            return {
                'experience_optimized': target_experience,
                'job_title': job_title,
                'result': result
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Experience optimization failed: {str(e)}")
            raise
    
    async def _customize_summary(self, state: AgentState, modification: Dict) -> Dict[str, Any]:
        """Customize the professional summary for target roles."""
        
        try:
            # Extract key requirements from job analysis
            jd_analysis = state.jd_analysis
            if not jd_analysis:
                return {'message': 'No job analysis available for summary customization'}
            
            # Use resume editor to customize summary
            result = await self.resume_editor.customize_summary(state.resume_path, jd_analysis)
            
            return {
                'summary_customized': True,
                'target_jobs': len(jd_analysis),
                'result': result
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Summary customization failed: {str(e)}")
            raise
    
    async def _optimize_keywords(self, state: AgentState, modification: Dict) -> Dict[str, Any]:
        """Optimize the resume with high-frequency keywords."""
        
        try:
            keywords = modification.get('keywords', [])
            
            if not keywords:
                return {'message': 'No keywords provided for optimization'}
            
            # Use resume editor to optimize keywords
            result = await self.resume_editor.optimize_keywords(state.resume_path, keywords)
            
            return {
                'keywords_optimized': keywords,
                'keyword_count': len(keywords),
                'result': result
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Keyword optimization failed: {str(e)}")
            raise
    
    async def _adapt_format(self, state: AgentState, modification: Dict) -> Dict[str, Any]:
        """Adapt the resume format for better ATS compatibility."""
        
        try:
            # Use resume editor to adapt format
            result = await self.resume_editor.adapt_format(state.resume_path)
            
            return {
                'format_adapted': True,
                'ats_optimized': True,
                'result': result
            }
            
        except Exception as e:
            self.log_action("ERROR", f"Format adaptation failed: {str(e)}")
            raise
    
    async def _validate_modifications(self, state: AgentState, modified_resume: Dict) -> Dict[str, Any]:
        """Validate that the modifications were successful."""
        
        try:
            self.log_action("INFO", "Validating resume modifications")
            
            validation_result = {
                'validation_passed': True,
                'issues_found': [],
                'recommendations': [],
                'overall_score': 0
            }
            
            # Check if modifications were applied
            successful_mods = [m for m in modified_resume.get('modifications_applied', []) if m['status'] == 'success']
            
            if not successful_mods:
                validation_result['validation_passed'] = False
                validation_result['issues_found'].append('No modifications were successfully applied')
            
            # Check success rate
            success_rate = modified_resume.get('modification_summary', {}).get('success_rate', 0)
            if success_rate < 0.8:
                validation_result['issues_found'].append(f'Low success rate: {success_rate:.2%}')
            
            # Generate recommendations
            if success_rate < 0.8:
                validation_result['recommendations'].append('Review failed modifications and retry')
            
            if len(successful_mods) < 3:
                validation_result['recommendations'].append('Consider additional resume enhancements')
            
            # Calculate overall score
            validation_result['overall_score'] = min(100, int(success_rate * 100))
            
            self.log_action("SUCCESS", f"Validation completed - score: {validation_result['overall_score']}/100")
            return validation_result
            
        except Exception as e:
            self.log_action("ERROR", f"Validation failed: {str(e)}")
            return {
                'validation_passed': False,
                'issues_found': [f'Validation error: {str(e)}'],
                'recommendations': ['Review error logs and retry validation'],
                'overall_score': 0
            }
    
    async def close(self):
        """Clean up resources."""
        
        if hasattr(self.resume_editor, 'close'):
            await self.resume_editor.close()
        
        self.log_action("INFO", "Resume agent resources cleaned up")
