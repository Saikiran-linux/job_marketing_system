import asyncio
import re
from typing import Dict, Any, List, Set
import openai
from openai import AsyncOpenAI
import nltk
from collections import Counter
from agents.base_agent import BaseAgent
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
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze job description and extract required skills."""
        
        # Validate required inputs
        required_fields = ["job_description"]
        if not self.validate_input(input_data, required_fields):
            return {"status": "error", "message": "Missing job description"}
        
        job_description = input_data.get("job_description", "")
        job_title = input_data.get("job_title", "")
        
        if not job_description.strip():
            return {"status": "error", "message": "Empty job description"}
        
        self.log_action("ANALYZING", f"Job: {job_title[:50]}...")
        
        try:
            # Extract skills using multiple methods
            regex_skills = self._extract_skills_regex(job_description)
            ai_skills = await self._extract_skills_ai(job_description, job_title)
            
            # Combine and rank skills
            combined_skills = self._combine_and_rank_skills(regex_skills, ai_skills, job_description)
            
            # Extract experience requirements
            experience_req = self._extract_experience_requirements(job_description)
            
            # Extract education requirements
            education_req = self._extract_education_requirements(job_description)
            
            # Extract certifications
            certifications = self._extract_certifications(job_description)
            
            # Categorize skills by importance
            skill_categories = self._categorize_skills(combined_skills, job_description)
            
            result = {
                "status": "success",
                "required_skills": combined_skills,
                "skill_categories": skill_categories,
                "experience_requirements": experience_req,
                "education_requirements": education_req,
                "certifications": certifications,
                "analysis_metadata": {
                    "description_length": len(job_description),
                    "regex_skills_found": len(regex_skills),
                    "ai_skills_found": len(ai_skills),
                    "total_unique_skills": len(combined_skills)
                }
            }
            
            self.log_action("SUCCESS", f"Extracted {len(combined_skills)} skills")
            return result
            
        except Exception as e:
            self.log_action("ERROR", f"Skills analysis failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Skills analysis failed: {str(e)}"
            }
    
    def _extract_skills_regex(self, job_description: str) -> Dict[str, List[str]]:
        """Extract skills using regex patterns."""
        extracted_skills = {}
        
        for category, pattern in self.skill_patterns.items():
            matches = pattern.findall(job_description)
            # Normalize matches (lowercase, remove duplicates)
            normalized_matches = list(set([match.lower() for match in matches]))
            extracted_skills[category] = normalized_matches
        
        return extracted_skills
    
    async def _extract_skills_ai(self, job_description: str, job_title: str) -> List[Dict[str, Any]]:
        """Extract skills using OpenAI API."""
        
        if not Config.OPENAI_API_KEY:
            self.log_action("WARNING", "OpenAI API key not configured, skipping AI analysis")
            return []
        
        try:
            prompt = f"""
            Analyze this job posting and extract the required skills, technologies, and qualifications.
            
            Job Title: {job_title}
            Job Description: {job_description}
            
            Please provide a JSON response with the following structure:
            {{
                "technical_skills": ["skill1", "skill2", ...],
                "soft_skills": ["skill1", "skill2", ...],
                "tools_and_technologies": ["tool1", "tool2", ...],
                "required_qualifications": ["qualification1", "qualification2", ...],
                "preferred_qualifications": ["qualification1", "qualification2", ...],
                "programming_languages": ["language1", "language2", ...],
                "frameworks_libraries": ["framework1", "framework2", ...],
                "databases": ["database1", "database2", ...],
                "cloud_platforms": ["platform1", "platform2", ...]
            }}
            
            Only include skills that are explicitly mentioned or clearly implied in the job posting.
            Use lowercase for all skills and technologies.
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing job descriptions and extracting relevant skills and requirements. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content
            
            # Extract JSON from the response
            import json
            try:
                # Try to find JSON in the response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = ai_response[json_start:json_end]
                    skills_data = json.loads(json_str)
                    
                    # Flatten the skills into a single list with metadata
                    ai_skills = []
                    for category, skills in skills_data.items():
                        for skill in skills:
                            ai_skills.append({
                                "skill": skill.lower(),
                                "category": category,
                                "source": "ai",
                                "confidence": 0.8
                            })
                    
                    return ai_skills
                
            except json.JSONDecodeError as e:
                self.log_action("ERROR", f"Failed to parse AI response as JSON: {str(e)}")
                
        except Exception as e:
            self.log_action("ERROR", f"OpenAI API call failed: {str(e)}")
        
        return []
    
    def _combine_and_rank_skills(self, regex_skills: Dict[str, List[str]], 
                                ai_skills: List[Dict[str, Any]], 
                                job_description: str) -> List[Dict[str, Any]]:
        """Combine skills from different sources and rank by importance."""
        
        all_skills = {}
        
        # Add regex skills
        for category, skills in regex_skills.items():
            for skill in skills:
                if skill not in all_skills:
                    all_skills[skill] = {
                        "skill": skill,
                        "sources": [],
                        "categories": [],
                        "mention_count": 0,
                        "confidence": 0.0
                    }
                
                all_skills[skill]["sources"].append("regex")
                all_skills[skill]["categories"].append(category)
                all_skills[skill]["confidence"] += 0.6
        
        # Add AI skills
        for skill_data in ai_skills:
            skill = skill_data["skill"]
            if skill not in all_skills:
                all_skills[skill] = {
                    "skill": skill,
                    "sources": [],
                    "categories": [],
                    "mention_count": 0,
                    "confidence": 0.0
                }
            
            all_skills[skill]["sources"].append("ai")
            all_skills[skill]["categories"].append(skill_data["category"])
            all_skills[skill]["confidence"] += skill_data["confidence"]
        
        # Count mentions in job description
        job_desc_lower = job_description.lower()
        for skill_name, skill_data in all_skills.items():
            skill_data["mention_count"] = job_desc_lower.count(skill_name)
            
            # Boost confidence based on mention count
            if skill_data["mention_count"] > 1:
                skill_data["confidence"] += 0.2 * skill_data["mention_count"]
        
        # Sort by confidence and return top skills
        ranked_skills = sorted(all_skills.values(), 
                             key=lambda x: x["confidence"], 
                             reverse=True)
        
        return ranked_skills
    
    def _extract_experience_requirements(self, job_description: str) -> Dict[str, Any]:
        """Extract experience requirements from job description."""
        
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:professional\s*)?(?:work\s*)?experience',
            r'minimum\s*(?:of\s*)?(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        years_mentioned = []
        for pattern in experience_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            years_mentioned.extend([int(match) for match in matches])
        
        # Extract level indicators
        level_patterns = {
            "entry": r'\b(?:entry[- ]?level|junior|graduate|new grad|recent graduate)\b',
            "mid": r'\b(?:mid[- ]?level|intermediate|experienced)\b',
            "senior": r'\b(?:senior|lead|principal|staff)\b',
            "expert": r'\b(?:expert|architect|distinguished|fellow)\b'
        }
        
        detected_levels = []
        for level, pattern in level_patterns.items():
            if re.search(pattern, job_description, re.IGNORECASE):
                detected_levels.append(level)
        
        return {
            "years_mentioned": years_mentioned,
            "min_years": min(years_mentioned) if years_mentioned else None,
            "max_years": max(years_mentioned) if years_mentioned else None,
            "detected_levels": detected_levels
        }
    
    def _extract_education_requirements(self, job_description: str) -> List[str]:
        """Extract education requirements."""
        
        education_patterns = [
            r'\b(?:bachelor\'?s?|ba|bs|b\.a\.|b\.s\.)\b',
            r'\b(?:master\'?s?|ma|ms|m\.a\.|m\.s\.|mba)\b',
            r'\b(?:phd|ph\.d\.|doctorate|doctoral)\b',
            r'\b(?:associate\'?s?|aa|as|a\.a\.|a\.s\.)\b',
            r'\b(?:high school|diploma|ged)\b'
        ]
        
        education_found = []
        for pattern in education_patterns:
            if re.search(pattern, job_description, re.IGNORECASE):
                education_found.append(pattern.replace('\\b', '').replace('?', ''))
        
        return education_found
    
    def _extract_certifications(self, job_description: str) -> List[str]:
        """Extract certification requirements."""
        
        cert_patterns = [
            r'\b(?:aws|amazon)\s*(?:certified|certification)\b',
            r'\bazure\s*(?:certified|certification)\b',
            r'\bgcp|google\s*cloud\s*(?:certified|certification)\b',
            r'\bcisco\s*(?:certified|ccna|ccnp|ccie)\b',
            r'\bpmp\s*(?:certified|certification)?\b',
            r'\bscrum\s*master\b',
            r'\bsix\s*sigma\b',
            r'\bitil\b',
            r'\bcism\b',
            r'\bcissp\b'
        ]
        
        certifications_found = []
        for pattern in cert_patterns:
            matches = re.findall(pattern, job_description, re.IGNORECASE)
            certifications_found.extend(matches)
        
        return list(set(certifications_found))
    
    def _categorize_skills(self, skills: List[Dict[str, Any]], job_description: str) -> Dict[str, List[str]]:
        """Categorize skills by importance (required vs preferred)."""
        
        required_indicators = [
            "required", "must have", "essential", "mandatory", 
            "need", "should have", "critical"
        ]
        
        preferred_indicators = [
            "preferred", "nice to have", "bonus", "plus", 
            "advantage", "desirable", "would be great"
        ]
        
        categorized = {
            "required": [],
            "preferred": [],
            "unknown": []
        }
        
        job_desc_lower = job_description.lower()
        
        for skill_data in skills:
            skill_name = skill_data["skill"]
            
            # Find mentions of the skill and surrounding context
            skill_mentions = []
            for match in re.finditer(re.escape(skill_name), job_desc_lower):
                start = max(0, match.start() - 100)
                end = min(len(job_desc_lower), match.end() + 100)
                context = job_desc_lower[start:end]
                skill_mentions.append(context)
            
            # Check context for requirement indicators
            is_required = False
            is_preferred = False
            
            for context in skill_mentions:
                for indicator in required_indicators:
                    if indicator in context:
                        is_required = True
                        break
                
                for indicator in preferred_indicators:
                    if indicator in context:
                        is_preferred = True
                        break
            
            # Categorize based on findings
            if is_required and not is_preferred:
                categorized["required"].append(skill_name)
            elif is_preferred and not is_required:
                categorized["preferred"].append(skill_name)
            elif skill_data["confidence"] > 0.8:
                categorized["required"].append(skill_name)
            else:
                categorized["unknown"].append(skill_name)
        
        return categorized
