import asyncio
import os
import re
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches
from datetime import datetime
import openai
from openai import AsyncOpenAI
from agents.base_agent import BaseAgent, AgentState
from config import Config

class ResumeModificationAgent(BaseAgent):
    """Agent responsible for modifying resumes to match job requirements."""
    
    def __init__(self):
        super().__init__("ResumeModificationAgent")
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY) if Config.OPENAI_API_KEY else None
    
    async def execute(self, state: AgentState) -> AgentState:
        """Modify resume to match job requirements."""
        
        # For resume modification, we need to get the job-specific data from the context
        # This agent is typically called during job processing, not from the main workflow state
        # We'll create a temporary state or use the existing state if it has job information
        
        # Since this agent is called during job processing, we need to handle the case
        # where we don't have direct access to job description in the main state
        # For now, we'll return the state as-is and handle the actual modification in the calling context
        
        self.log_action("INFO", "Resume modification agent called - job-specific modification handled in calling context")
        
        # Update state to indicate resume modification step
        state.steps_completed.append("resume_modification")
        state.current_step = "resume_modification_complete"
        
        return state
    
    def _analyze_skill_gaps(self, current_resume: Dict[str, Any], 
                           required_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze gaps between current skills and required skills."""
        
        current_skills = current_resume.get("current_skills", [])
        current_skill_names = {skill["skill"].lower() for skill in current_skills}
        
        # Categorize required skills
        missing_skills = []
        matching_skills = []
        skill_enhancements = []
        
        for req_skill in required_skills:
            skill_name = req_skill.get("skill", "").lower()
            skill_confidence = req_skill.get("confidence", 0)
            
            if skill_name in current_skill_names:
                # Find current skill details
                current_skill = next(
                    (s for s in current_skills if s["skill"].lower() == skill_name), 
                    None
                )
                
                matching_skills.append({
                    "skill": skill_name,
                    "current_mentions": current_skill["mention_count"] if current_skill else 0,
                    "required_confidence": skill_confidence,
                    "enhancement_needed": skill_confidence > 0.8 and 
                                        (current_skill["mention_count"] if current_skill else 0) < 2
                })
                
                # Check if skill needs enhancement
                if current_skill and current_skill["mention_count"] < 2 and skill_confidence > 0.7:
                    skill_enhancements.append({
                        "skill": skill_name,
                        "current_mentions": current_skill["mention_count"],
                        "suggested_mentions": 3,
                        "contexts_to_add": req_skill.get("categories", [])
                    })
            else:
                missing_skills.append({
                    "skill": skill_name,
                    "confidence": skill_confidence,
                    "category": req_skill.get("categories", ["unknown"])[0] if req_skill.get("categories") else "unknown",
                    "priority": "high" if skill_confidence > 0.8 else "medium" if skill_confidence > 0.5 else "low"
                })
        
        return {
            "missing_skills": missing_skills,
            "matching_skills": matching_skills,
            "skill_enhancements": skill_enhancements,
            "coverage_percentage": len(matching_skills) / len(required_skills) * 100 if required_skills else 0,
            "total_required": len(required_skills),
            "total_matching": len(matching_skills),
            "total_missing": len(missing_skills)
        }
    
    async def _generate_optimized_content(self, current_resume: Dict[str, Any], 
                                        required_skills: List[Dict[str, Any]],
                                        job_description: str, 
                                        job_title: str) -> Dict[str, Any]:
        """Generate optimized resume content using AI."""
        
        if not self.client:
            return self._generate_basic_optimized_content(current_resume, required_skills)
        
        try:
            # Extract key information from current resume
            resume_content = current_resume.get("resume_content", "")
            current_skills = [skill["skill"] for skill in current_resume.get("current_skills", [])]
            experience_details = current_resume.get("experience_details", [])
            
            # Create required skills list
            required_skill_names = [skill.get("skill", "") for skill in required_skills]
            high_priority_skills = [
                skill.get("skill", "") for skill in required_skills 
                if skill.get("confidence", 0) > 0.7
            ]
            
            prompt = f"""
            Optimize this resume for a {job_title} position. The goal is to better align the resume with the job requirements while maintaining truthfulness and professionalism.
            
            Current Resume Content:
            {resume_content[:2000]}
            
            Job Description:
            {job_description[:1000]}
            
            Required Skills: {', '.join(required_skill_names)}
            High Priority Skills: {', '.join(high_priority_skills)}
            Current Skills: {', '.join(current_skills)}
            
            Please provide optimized content in JSON format:
            {{
                "optimized_summary": "Professional summary optimized for this role...",
                "enhanced_experience": [
                    {{
                        "title": "Job Title",
                        "company": "Company Name", 
                        "description": "Enhanced job description with relevant keywords...",
                        "achievements": ["Achievement 1", "Achievement 2"]
                    }}
                ],
                "skills_section": {{
                    "technical_skills": ["skill1", "skill2", ...],
                    "core_competencies": ["competency1", "competency2", ...]
                }},
                "keywords_added": ["keyword1", "keyword2", ...],
                "modifications_summary": ["modification1", "modification2", ...],
                "ats_optimization_tips": ["tip1", "tip2", ...]
            }}
            
            Guidelines:
            1. Keep all information truthful - only enhance presentation, don't fabricate
            2. Incorporate high-priority required skills naturally into existing experience
            3. Use action verbs and quantifiable achievements
            4. Optimize for ATS (Applicant Tracking Systems)
            5. Maintain professional tone and format
            6. Focus on relevant experience and skills
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert resume writer and career coach. Create compelling, truthful, and ATS-optimized resume content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content
            
            # Extract JSON from the response
            import json
            try:
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = ai_response[json_start:json_end]
                    optimized_data = json.loads(json_str)
                    
                    # Add metadata
                    optimized_data["source"] = "ai"
                    optimized_data["optimization_timestamp"] = datetime.now().isoformat()
                    
                    return optimized_data
                
            except json.JSONDecodeError as e:
                self.log_action("WARNING", f"Failed to parse AI response as JSON: {str(e)}")
                
            # Fallback to basic optimization
            return self._generate_basic_optimized_content(current_resume, required_skills)
            
        except Exception as e:
            self.log_action("ERROR", f"AI optimization failed: {str(e)}")
            return self._generate_basic_optimized_content(current_resume, required_skills)
    
    def _generate_basic_optimized_content(self, current_resume: Dict[str, Any], 
                                        required_skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate basic optimized content without AI."""
        
        resume_content = current_resume.get("resume_content", "")
        current_skills = current_resume.get("current_skills", [])
        
        # Extract high-priority missing skills
        current_skill_names = {skill["skill"].lower() for skill in current_skills}
        missing_skills = [
            skill["skill"] for skill in required_skills 
            if skill.get("skill", "").lower() not in current_skill_names 
            and skill.get("confidence", 0) > 0.6
        ]
        
        # Basic modifications
        modifications = []
        
        if missing_skills:
            modifications.append(f"Added {len(missing_skills)} required skills to technical skills section")
        
        # Enhanced skills section
        all_skills = [skill["skill"] for skill in current_skills]
        all_skills.extend(missing_skills[:5])  # Add top 5 missing skills
        
        return {
            "optimized_summary": "Professional summary highlighting relevant experience and technical expertise",
            "enhanced_experience": [],
            "skills_section": {
                "technical_skills": all_skills,
                "core_competencies": []
            },
            "keywords_added": missing_skills,
            "modifications_summary": modifications,
            "ats_optimization_tips": [
                "Added relevant keywords from job description",
                "Ensured skills match job requirements",
                "Optimized for ATS scanning"
            ],
            "source": "basic",
            "optimization_timestamp": datetime.now().isoformat()
        }
    
    async def _create_resume_file(self, optimized_content: Dict[str, Any], 
                                job_title: str, company_name: str) -> str:
        """Create a new resume file with optimized content."""
        
        # Create output directory
        os.makedirs(Config.OUTPUT_RESUME_DIR, exist_ok=True)
        
        # Generate filename
        safe_job_title = re.sub(r'[^\w\s-]', '', job_title).strip()
        safe_company = re.sub(r'[^\w\s-]', '', company_name).strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"resume_{safe_job_title}_{safe_company}_{timestamp}.docx"
        filepath = os.path.join(Config.OUTPUT_RESUME_DIR, filename)
        
        # Create new document
        doc = Document()
        
        # Add title
        title = doc.add_heading(f'Resume - {job_title}', 0)
        title.alignment = 1  # Center alignment
        
        # Add optimized summary
        if optimized_content.get("optimized_summary"):
            doc.add_heading('Professional Summary', level=1)
            doc.add_paragraph(optimized_content["optimized_summary"])
        
        # Add skills section
        skills_section = optimized_content.get("skills_section", {})
        if skills_section:
            doc.add_heading('Technical Skills', level=1)
            
            technical_skills = skills_section.get("technical_skills", [])
            if technical_skills:
                skills_text = " • ".join(technical_skills)
                doc.add_paragraph(skills_text)
            
            core_competencies = skills_section.get("core_competencies", [])
            if core_competencies:
                doc.add_heading('Core Competencies', level=2)
                comp_text = " • ".join(core_competencies)
                doc.add_paragraph(comp_text)
        
        # Add enhanced experience
        enhanced_experience = optimized_content.get("enhanced_experience", [])
        if enhanced_experience:
            doc.add_heading('Professional Experience', level=1)
            
            for exp in enhanced_experience:
                # Job title and company
                job_info = f"{exp.get('title', 'Position')} - {exp.get('company', 'Company')}"
                doc.add_heading(job_info, level=2)
                
                # Description
                if exp.get('description'):
                    doc.add_paragraph(exp['description'])
                
                # Achievements
                achievements = exp.get('achievements', [])
                if achievements:
                    for achievement in achievements:
                        p = doc.add_paragraph(achievement)
                        p.style = 'List Bullet'
        
        # Add metadata section (hidden)
        doc.add_page_break()
        doc.add_heading('Optimization Metadata', level=1)
        
        metadata_info = [
            f"Generated: {optimized_content.get('optimization_timestamp', 'Unknown')}",
            f"Target Position: {job_title}",
            f"Target Company: {company_name}",
            f"Keywords Added: {', '.join(optimized_content.get('keywords_added', []))}",
            f"Modifications: {len(optimized_content.get('modifications_summary', []))}"
        ]
        
        for info in metadata_info:
            doc.add_paragraph(info)
        
        # Save document
        doc.save(filepath)
        
        return filepath
    
    def _generate_improvement_report(self, current_resume: Dict[str, Any], 
                                   optimized_content: Dict[str, Any],
                                   skill_gap_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report of improvements made to the resume."""
        
        return {
            "summary": {
                "total_modifications": len(optimized_content.get("modifications_summary", [])),
                "skills_added": len(optimized_content.get("keywords_added", [])),
                "skill_coverage_improvement": f"{skill_gap_analysis.get('coverage_percentage', 0):.1f}%",
                "optimization_source": optimized_content.get("source", "unknown")
            },
            "skill_improvements": {
                "missing_skills_addressed": len(skill_gap_analysis.get("missing_skills", [])),
                "skills_enhanced": len(skill_gap_analysis.get("skill_enhancements", [])),
                "new_keywords": optimized_content.get("keywords_added", [])
            },
            "content_improvements": {
                "summary_optimized": bool(optimized_content.get("optimized_summary")),
                "experience_enhanced": len(optimized_content.get("enhanced_experience", [])),
                "skills_section_updated": bool(optimized_content.get("skills_section"))
            },
            "ats_optimization": optimized_content.get("ats_optimization_tips", []),
            "modifications_made": optimized_content.get("modifications_summary", []),
            "recommendations": self._generate_recommendations(skill_gap_analysis, optimized_content)
        }
    
    def _generate_recommendations(self, skill_gap_analysis: Dict[str, Any], 
                                optimized_content: Dict[str, Any]) -> List[str]:
        """Generate recommendations for further resume improvement."""
        
        recommendations = []
        
        # Skill-based recommendations
        missing_skills_count = len(skill_gap_analysis.get("missing_skills", []))
        if missing_skills_count > 5:
            recommendations.append(
                f"Consider learning {missing_skills_count} missing skills to better match job requirements"
            )
        
        coverage = skill_gap_analysis.get("coverage_percentage", 0)
        if coverage < 70:
            recommendations.append(
                "Skill coverage is below 70% - consider highlighting transferable skills"
            )
        
        # Content recommendations
        if not optimized_content.get("optimized_summary"):
            recommendations.append("Add a professional summary tailored to the target role")
        
        enhanced_exp_count = len(optimized_content.get("enhanced_experience", []))
        if enhanced_exp_count < 2:
            recommendations.append("Consider enhancing more work experience entries with relevant keywords")
        
        # ATS recommendations
        keywords_added = len(optimized_content.get("keywords_added", []))
        if keywords_added < 3:
            recommendations.append("Add more industry-specific keywords for better ATS compatibility")
        
        return recommendations
