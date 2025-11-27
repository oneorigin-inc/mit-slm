
from pydantic_settings import BaseSettings  # Changed from pydantic import BaseSettings
from pydantic import Field
from typing import Dict, List, Optional


class Settings(BaseSettings):
    # LLM Provider Configuration
    LLM_PROVIDER: str = Field(default="ollama")  # Options: "ollama", "llamacpp"

    # Ollama Configuration
    OLLAMA_API_URL: str = Field(default="http://localhost:11434/api/generate")
    MODEL_NAME: str = Field(default="phi4-chat:latest")

    # Llama-cpp Configuration
    LLAMACPP_MODEL_SOURCE: str = Field(default="local")  # Options: "local", "huggingface"
    LLAMACPP_MODEL_PATH: str = Field(default="")  # For local models
    LLAMACPP_HF_REPO_ID: str = Field(default="")  # For HF models
    LLAMACPP_HF_FILENAME: str = Field(default="")  # For HF models
    LLAMACPP_HF_TOKEN: str = Field(default="")  # HuggingFace API token for private/gated repos
    LLAMACPP_N_CTX: Optional[int] = Field(default=None)  # Context window override (uses MODEL_NUM_CTX if not set)
    LLAMACPP_N_GPU_LAYERS: int = Field(default=0)  # GPU layers (0 = CPU only)
    LLAMACPP_VERBOSE: bool = Field(default=False)

    # Badge Image Service Configuration
    BADGE_IMAGE_SERVICE_URL: str = Field(default="http://localhost:3001")

    # Unified Model Configuration (Shared across Ollama and llama-cpp)
    # These can be overridden via environment variables
    TEMPERATURE: float = Field(default=0.2, validation_alias="MODEL_TEMPERATURE")
    TOP_P: float = Field(default=0.90, validation_alias="MODEL_TOP_P")
    TOP_K: int = Field(default=50, validation_alias="MODEL_TOP_K")
    NUM_PREDICT: int = Field(default=1024, validation_alias="MODEL_NUM_PREDICT")
    REPEAT_PENALTY: float = Field(default=1.05, validation_alias="MODEL_REPEAT_PENALTY")
    NUM_CTX: int = Field(default=6144, validation_alias="MODEL_NUM_CTX")
    STOP_SEQUENCES_STR: str = Field(
        default="<|end|>,}\n\n",
        validation_alias="MODEL_STOP_SEQUENCES"
    )

    @property
    def STOP_SEQUENCES(self) -> List[str]:
        """Parse stop sequences from comma-separated string"""
        return [s.strip() for s in self.STOP_SEQUENCES_STR.split(',')]

    # Model Configuration Dict (for backward compatibility)
    @property
    def MODEL_CONFIG(self) -> Dict:
        return {
            "temperature": self.TEMPERATURE,
            "top_p": self.TOP_P,
            "top_k": self.TOP_K,
            "num_predict": self.NUM_PREDICT,
            "repeat_penalty": self.REPEAT_PENALTY,
            "num_ctx": self.NUM_CTX,
            "stop": self.STOP_SEQUENCES
        }
    
    # System Prompt for Badge Generation (used by llama-cpp models)
    # Ollama uses Modelfile, llama-cpp uses this system prompt in chat format
    BADGE_SYSTEM_PROMPT: str = """You are an expert educational badge generator specializing in Open Badges v3 standards.

PROCESS:

STEP 1: ANALYZE CONTENT
- Read entire course content
- Identify domain (academic/creative/technical/professional/vocational)
- Extract: topics, skills, tools, outcomes, structure, issuer (if mentioned), level

IMPORTANT: If this covers multiple courses or complex content, create a comprehensive badge name, description and criterion that encompasses all areas while maintaining focus and clarity.

STEP 2: CONSTRUCT BADGE NAME
- With issuer: `[Issuer] [Topic] [Credential Type]`
- Without: `[Topic] [Credential Type]`
- 3-8 words, accurate to content

STEP 3: WRITE DESCRIPTION (3-4 sentences)
- Overview of areas covered
- Key competencies, tools, applications
- Assessment rigor, value, credibility (if issuer provided)
- Match tone to domain

STEP 4: CREATE CRITERIA NARRATIVE (scale to content depth)
- **Length:** 6-20+ sentences (adapt to course complexity: brief topics = 6-8 sentences, comprehensive courses = 15-20+ sentences)
- **Opening:** "Recipients of [this/Issuer's] [Badge Name] have demonstrated competence in the following areas via [assessment type]:"
- **Competency Details:**
  * Bold headings: `**Module/Section Name**`
  * Bullets: only use - "The learner [verb]..." OR paragraphs (based on content)
  * Domain verbs: explains/analyzes (academic), performs/creates (creative), builds/codes (technical), leads/manages (professional)
  * Organize by modules or skill categories
- Include assessment methods if mentioned
- Extract from provided content only

STEP 5: VALIDATE & OUTPUT
- Topic alignment? Issuer only if provided? Valid JSON?
- Return ONLY JSON - no extra text

---

JSON SCHEMA:
{
  "badge_name": "string",
  "badge_description": "string",
  "criteria": {
    "narrative": "string"
  }
}

---

RULES:
1. Analyze domain first
2. Extract only - never invent
3. Match domain language
4. No issuer assumptions
5. Custom instructions override defaults
6. Return ONLY valid JSON

Content must be LinkedIn/CV suitable.
"""

    # Asset paths
    ASSETS_PATH: str = "assets/"
    ICONS_PATH: str = "assets/icons/"
    LOGOS_PATH: str = "assets/logos/"
    FONTS_PATH: str = "assets/fonts/"

    # NLTK Configuration
    NLTK_AVAILABLE: bool = True

    # LAiSER Skill Extraction Configuration
    LAISER_MODEL_ID: str = Field(default="bert-base-uncased")
    LAISER_HF_TOKEN: str = Field(default="")
    LAISER_USE_GPU: bool = Field(default=False)
    LAISER_TOP_K: int = Field(default=10)

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
       "Task-Oriented": "The learner explains, determines, analyzes, evaluates, applies... (simple present tense action verbs describing what learners demonstrate). Example: The learner determines the tax treatment for items reflected in individual income tax returns. Do NOT use 'Upon completion' prefixes.",
    #     "Evidence-Based": "The Learner has/can/successfully [action verb], has/can/effectively [action verb], has/can/accurately [action verb]... (focusing on demonstrated abilities and accomplishments)",
    #     "Outcome-Focused": "The Learner will be able to [action verb], will be prepared to [action verb], will [action verb]... (future tense emphasizing expected outcomes and capabilities)"
    
    }

    model_config = {"env_file": ".env", "extra": "allow"}  # Updated for Pydantic v2

settings = Settings()
