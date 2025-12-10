"""
Guidance-based badge generator for guaranteed structured JSON output.

This service uses the guidance library to ensure that the LLM generates
valid JSON conforming to the BadgeSchema, eliminating the need for
regex-based JSON extraction and reducing parsing errors.
"""

import guidance
from guidance import gen, json as guidance_json, models
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)


class BadgeSchema(BaseModel):
    """Pydantic schema for badge generation with validation constraints"""
    badge_name: str = Field(max_length=100, description="Concise badge title")
    badge_description: str = Field(max_length=500, description="Comprehensive badge description")
    criteria: Dict[str, str] = Field(
        default_factory=lambda: {"narrative": ""},
        description="Achievement criteria with narrative field"
    )


class GuidanceBadgeGenerator:
    """Badge generator using guidance for structured output"""

    def __init__(self):
        """Initialize the guidance model pointing to Ollama"""
        self.model = None
        self._initialized = False

    def _initialize_model(self):
        """Lazy initialization of the guidance model"""
        if self._initialized:
            return

        try:
            # Extract base URL from the Ollama API URL
            # e.g., "http://localhost:11434/api/generate" -> "http://localhost:11434"
            base_url = settings.OLLAMA_API_URL.rsplit('/api/', 1)[0]

            logger.info(f"Initializing guidance model with Ollama at {base_url}")

            # Use OpenAI-compatible endpoint for Ollama
            # Ollama provides OpenAI-compatible API at /v1/completions
            self.model = models.OpenAI(
                model=settings.MODEL_NAME,
                api_base=f"{base_url}/v1",
                api_key="ollama",  # Dummy key for Ollama
                echo=False
            )

            self._initialized = True
            logger.info("Guidance model initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize guidance model: {e}")
            raise

    async def generate_badge_with_schema(
        self,
        course_content: str,
        style: str,
        tone: str,
        level: str,
        criterion_style: str,
        institution: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate badge metadata with guaranteed JSON structure using guidance.

        Args:
            course_content: Processed course input text
            style: Badge style description
            tone: Badge tone description
            level: Badge level description
            criterion_style: Criterion style template
            institution: Optional institution name
            custom_instructions: Optional custom instructions

        Returns:
            Dict containing validated badge_name, badge_description, and criteria
        """

        # Ensure model is initialized
        self._initialize_model()

        # Build the prompt
        prompt = self._build_prompt(
            course_content=course_content,
            style=style,
            tone=tone,
            level=level,
            criterion_style=criterion_style,
            institution=institution,
            custom_instructions=custom_instructions
        )

        try:
            # Run synchronously in thread pool since guidance is sync
            result = await asyncio.to_thread(self._generate_sync, prompt)
            logger.info(f"Generated badge with guidance: {result.get('badge_name', 'N/A')}")
            return result

        except Exception as e:
            logger.error(f"Guidance generation failed: {e}")
            raise

    def _generate_sync(self, prompt: str) -> Dict[str, Any]:
        """
        Synchronous generation with guidance (called in thread pool).

        Args:
            prompt: The complete prompt for badge generation

        Returns:
            Dict with validated badge data
        """
        try:
            # Create guidance program with JSON schema constraint
            lm = self.model

            # Add user prompt
            lm = lm + prompt

            # Generate with JSON schema validation
            # This ensures the output conforms to BadgeSchema
            lm = lm + "\n\nGenerate badge JSON:"
            lm = lm + guidance_json(name="badge_data", schema=BadgeSchema)

            # Extract the validated result
            result = lm["badge_data"]

            return result

        except Exception as e:
            logger.error(f"Synchronous guidance generation error: {e}")
            raise

    async def generate_badge_manual_structure(
        self,
        course_content: str,
        style: str,
        tone: str,
        level: str,
        criterion_style: str,
        institution: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Alternative generation method with manual JSON structure control.
        Provides more fine-grained control over each field generation.

        Args:
            course_content: Processed course input text
            style: Badge style description
            tone: Badge tone description
            level: Badge level description
            criterion_style: Criterion style template
            institution: Optional institution name
            custom_instructions: Optional custom instructions

        Returns:
            Dict containing badge_name, badge_description, and criteria
        """

        # Ensure model is initialized
        self._initialize_model()

        # Build the prompt
        prompt = self._build_prompt(
            course_content=course_content,
            style=style,
            tone=tone,
            level=level,
            criterion_style=criterion_style,
            institution=institution,
            custom_instructions=custom_instructions
        )

        try:
            result = await asyncio.to_thread(self._generate_manual_sync, prompt)
            logger.info(f"Generated badge manually with guidance: {result.get('badge_name', 'N/A')}")
            return result

        except Exception as e:
            logger.error(f"Manual guidance generation failed: {e}")
            raise

    def _generate_manual_sync(self, prompt: str) -> Dict[str, Any]:
        """
        Synchronous manual structure generation.
        This method explicitly controls JSON field generation.
        """
        try:
            lm = self.model
            lm = lm + prompt
            lm = lm + "\n\nGenerate badge JSON:\n{"

            # Generate badge_name field
            lm = lm + '\n    "badge_name": "'
            lm = lm + gen(name="badge_name", max_tokens=50, stop='"')
            lm = lm + '",'

            # Generate badge_description field
            lm = lm + '\n    "badge_description": "'
            lm = lm + gen(name="badge_description", max_tokens=200, stop='"')
            lm = lm + '",'

            # Generate criteria object
            lm = lm + '\n    "criteria": {'
            lm = lm + '\n        "narrative": "'
            lm = lm + gen(name="criteria_narrative", max_tokens=300, stop='"')
            lm = lm + '"\n    }\n}'

            # Build result from captured variables
            result = {
                "badge_name": lm["badge_name"],
                "badge_description": lm["badge_description"],
                "criteria": {
                    "narrative": lm["criteria_narrative"]
                }
            }

            return result

        except Exception as e:
            logger.error(f"Manual synchronous generation error: {e}")
            raise

    def _build_prompt(
        self,
        course_content: str,
        style: str,
        tone: str,
        level: str,
        criterion_style: str,
        institution: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Build the prompt for badge generation.

        Returns:
            Complete prompt string
        """
        prompt = f"""Course Content: {course_content}

Parameters:
- Style: {style}
- Tone: {tone}
- Level: {level}
- Criterion Style: {criterion_style}"""

        if institution:
            prompt += f"\n- Institution: {institution}, Highlight institutional credibility and authority in badge name and badge description briefly."

        if custom_instructions:
            prompt += f"\n- Special Instructions: {custom_instructions}"

        return prompt


# Singleton instance
guidance_generator = GuidanceBadgeGenerator()
