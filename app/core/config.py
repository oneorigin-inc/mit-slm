from pydantic_settings import BaseSettings  # Changed from pydantic import BaseSettings
from pydantic import Field
from typing import Dict, List
import os

class Settings(BaseSettings):
    # Ollama Configuration  
    OLLAMA_API_URL: str = "http://localhost:11434/api/generate"
    MODEL_NAME: str = "phi4-chat:latest"
    
    # Model Configuration
    MODEL_CONFIG: Dict = {
        "temperature": 0.15,
        "top_p": 0.8,
        "top_k": 30,
        "num_predict": 1024,
        "repeat_penalty": 1.05,
        "num_ctx": 4096,
        "stop": ["<|end|>", "}\n\n"]
    }
    
    # Asset paths
    ASSETS_PATH: str = "assets/"
    ICONS_PATH: str = "assets/icons/"
    LOGOS_PATH: str = "assets/logos/"
    FONTS_PATH: str = "assets/fonts/"
    
    # NLTK Configuration
    NLTK_AVAILABLE: bool = True
    
    # Style Descriptions
    STYLE_DESCRIPTIONS: Dict = {
    "Professional": "Style Instructions: Use formal, business-oriented language emphasizing industry standards and career advancement. Write in a professional corporate tone. Focus on business value, organizational impact, and career development. Use formal language suitable for executive presentations and HR documentation. Badge Naming: Create formal, professional titles that emphasize credibility and career value (e.g., 'Executive Leadership Certificate', 'Strategic Business Analyst Credential', 'Professional Project Management Badge'). Use titles that would appear on a resume or LinkedIn profile.",
    
    "Academic": "Style Instructions: Use scholarly language emphasizing learning outcomes and academic rigor. Adopt an academic writing style with emphasis on educational objectives and pedagogical frameworks. Reference learning theories and competency standards. Use precise educational terminology. Badge Naming: Create academic honors and scholarly titles that convey intellectual achievement (e.g., 'Research Excellence Award', 'Advanced Studies in Biology', 'Scholar of Data Science', 'Academic Achievement in Literature'). Use titles common in educational institutions and academic transcripts.",
    
    "Industry": "Style Instructions: Use sector-specific terminology focusing on job-readiness and practical applications. Write with industry-specific language emphasizing hands-on skills and workplace readiness. Focus on practical competencies, certifications, and real-world application. Use terminology that hiring managers recognize. Badge Naming: Create job-ready certification titles that signal employability (e.g., 'Certified Full-Stack Developer', 'Professional Welder Certification', 'Licensed Phlebotomy Technician', 'Qualified Network Administrator'). Use titles that employers and recruiters actively search for.",
    
    "Technical": "Style Instructions: Use precise technical language with emphasis on tools and measurable outcomes. Write with technical precision using specific metrics, tools, and technologies. Emphasize quantifiable achievements and technical proficiencies. Include technical stack details where relevant. Badge Naming: Create technical achievement titles that specify technologies and competencies (e.g., 'Python Mastery Badge', 'AWS Cloud Solutions Architect', 'React.js Developer Certification', 'Machine Learning Specialist'). Include specific tools, frameworks, or technologies in the title when relevant.",
    
    "Creative": "Style Instructions: Use engaging language highlighting innovation and problem-solving. Write in an inspiring tone that celebrates creativity, innovation, and breakthrough thinking. Emphasize unique approaches, original solutions, and forward-thinking mindset. Use energetic and motivational language. Badge Naming: Create inspiring, imaginative titles that energize and celebrate innovation (e.g., 'Innovation Pioneer', 'Creative Problem-Solver', 'Design Thinking Champion', 'Digital Storytelling Virtuoso'). Use dynamic, memorable titles that spark enthusiasm and highlight originality."
}
    
    TONE_DESCRIPTIONS: Dict = {
        "Authoritative": "Confident, definitive tone with institutional credibility.",
        "Encouraging": "Motivating, supportive tone inspiring continued learning.",
        "Detailed": "Comprehensive detail with examples and specific metrics.",
        "Concise": "Short, direct guidance focusing on essential information.",
        "Engaging": "Dynamic, compelling language to capture attention."
    }
    
    LEVEL_DESCRIPTIONS: Dict = {
        "Beginner": "Target learners with minimal prior knowledge; focus on foundations.",
        "Intermediate": "Target learners with basic familiarity; emphasize applied tasks.",
        "Advanced": "Target learners with solid foundations; emphasize complex problem solving."
    }
    
    CRITERION_TEMPLATES: Dict = {
        "Task-Oriented": "[Action verb], [action verb], [action verb]... (imperative commands directing learners to perform tasks)",
        "Evidence-Based": "Learner has/can/successfully [action verb], has/can/effectively [action verb], has/can/accurately [action verb]... (focusing on demonstrated abilities and accomplishments)",
        "Outcome-Focused": "Students will be able to [action verb], will be prepared to [action verb], will [action verb]... (future tense emphasizing expected outcomes and capabilities)"
    }
    
    model_config = {"env_file": ".env"}  # Updated for Pydantic v2

settings = Settings()
