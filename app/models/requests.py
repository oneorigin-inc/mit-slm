from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
import re
import base64


# ============================================================================
# Nested Configuration Models for BadgeRequest
# ============================================================================

class ContentConfig(BaseModel):
    """Badge content configuration - what the badge is about"""
    input: str = Field(
        ...,
        min_length=1,
        description="Course content or description to generate badge from. Can be multiple courses separated by newlines, semicolons, or 'and'"
    )
    style: str = Field(
        default="",
        description="Badge style: Professional, Academic, Industry, Technical, Creative. Empty for random."
    )
    tone: str = Field(
        default="",
        description="Badge tone: Authoritative, Encouraging, Detailed, Concise, Engaging. Empty for random."
    )
    criteria: str = Field(
        default="",
        description="Criteria style: Task-Oriented, Evidence-Based, Outcome-Focused. Empty for random."
    )
    level: str = Field(
        default="",
        description="Badge difficulty level: Beginner, Intermediate, Advanced. Empty for random."
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Custom instructions for badge generation"
    )


class IssuerConfig(BaseModel):
    """Issuing institution configuration"""
    name: Optional[str] = Field(
        default=None,
        description="Issuing institution name (e.g., 'MIT', 'WGU')"
    )
    url: Optional[str] = Field(
        default=None,
        description="Institution URL for brand color scraping (e.g., 'https://www.mit.edu')"
    )


class ColorsConfig(BaseModel):
    """Color configuration for badge image"""
    primary: Optional[str] = Field(
        default=None,
        description="Primary hex color (e.g., '#A31F34')"
    )
    secondary: Optional[str] = Field(
        default=None,
        description="Secondary hex color (e.g., '#8A8B8C')"
    )

    @field_validator('primary', 'secondary')
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize hex color format"""
        if v is None:
            return v
        # Allow with or without # prefix
        if not re.match(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', v):
            raise ValueError(f"Invalid hex color format: {v}. Expected format: #RRGGBB or #RGB")
        # Normalize to include # prefix and uppercase
        if not v.startswith('#'):
            v = f'#{v}'
        return v.upper()


class ImageConfig(BaseModel):
    """Badge image configuration - how the badge looks"""
    enabled: bool = Field(
        default=True,
        description="Whether to generate badge image. If False, skips image generation."
    )
    type: Optional[Literal["text_overlay", "icon_based"]] = Field(
        default=None,
        description="Force image type. If None, randomly selected."
    )
    shape: Optional[Literal["hexagon", "circle", "rounded_rect"]] = Field(
        default=None,
        description="Badge shape"
    )
    colors: Optional[ColorsConfig] = Field(
        default=None,
        description="Color configuration"
    )
    border: Optional[str] = Field(
        default=None,
        description="Border color hex (e.g., '#000000')"
    )
    border_width: Optional[int] = Field(
        default=None,
        ge=0,
        le=20,
        description="Border width in pixels (0-20)"
    )
    logo: Optional[str] = Field(
        default=None,
        description="Base64 encoded logo image. Include data URI prefix or raw base64."
    )

    @field_validator('border')
    @classmethod
    def validate_border_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize border color"""
        if v is None:
            return v
        if not re.match(r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', v):
            raise ValueError(f"Invalid border color format: {v}. Expected format: #RRGGBB or #RGB")
        if not v.startswith('#'):
            v = f'#{v}'
        return v.upper()

    @field_validator('logo')
    @classmethod
    def validate_logo_base64(cls, v: Optional[str]) -> Optional[str]:
        """Validate base64 logo format and size"""
        if v is None or v == "":
            return None

        logo_data = v
        # Strip data URI prefix if present
        if v.startswith('data:'):
            try:
                logo_data = v.split(',', 1)[1]
            except IndexError:
                raise ValueError("Invalid data URI format for logo")

        # Validate base64 encoding and size
        try:
            decoded = base64.b64decode(logo_data, validate=True)
            if len(decoded) < 8:
                raise ValueError("Logo data too small to be a valid image")
            if len(decoded) > 5 * 1024 * 1024:  # 5MB limit
                raise ValueError("Logo exceeds 5MB size limit")
        except Exception as e:
            if "Logo" in str(e) or "logo" in str(e):
                raise
            raise ValueError(f"Invalid base64 encoding for logo: {str(e)}")

        return logo_data  # Return just the base64 data without prefix


class SkillsConfig(BaseModel):
    """Skill extraction configuration"""
    enabled: bool = Field(
        default=False,
        description="Enable LAiSER skill extraction for ESCO taxonomy alignment"
    )


# ============================================================================
# Main Request Model
# ============================================================================

class BadgeRequest(BaseModel):
    """
    Badge generation request with nested configuration.

    Structure:
    - content: Badge content configuration (required)
    - issuer: Institution information (optional)
    - image: Image generation settings (optional, defaults enabled)
    - skills: Skill extraction settings (optional, defaults disabled)

    Example minimal request:
    {
        "content": {
            "input": "Introduction to Machine Learning"
        }
    }

    Example full request:
    {
        "content": {
            "input": "Advanced Python Programming",
            "style": "Technical",
            "tone": "Detailed",
            "criteria": "Outcome-Focused",
            "level": "Advanced",
            "instructions": "Focus on practical coding skills"
        },
        "issuer": {
            "name": "MIT",
            "url": "https://www.mit.edu"
        },
        "image": {
            "enabled": true,
            "type": "text_overlay",
            "shape": "hexagon",
            "colors": {
                "primary": "#A31F34",
                "secondary": "#8A8B8C"
            },
            "border": "#000000",
            "border_width": 4,
            "logo": null
        },
        "skills": {
            "enabled": true
        }
    }
    """
    content: ContentConfig
    issuer: Optional[IssuerConfig] = Field(default=None)
    image: Optional[ImageConfig] = Field(default_factory=ImageConfig)
    skills: Optional[SkillsConfig] = Field(default_factory=SkillsConfig)

    class Config:
        json_schema_extra = {
            "example": {
                "content": {
                    "input": "Introduction to Machine Learning",
                    "style": "Technical",
                    "level": "Intermediate"
                },
                "issuer": {
                    "name": "MIT"
                },
                "image": {
                    "enabled": True,
                    "shape": "hexagon"
                },
                "skills": {
                    "enabled": False
                }
            }
        }


# ============================================================================
# Other Request Models (unchanged)
# ============================================================================

class RegenerationRequest(BaseModel):
    course_input: str = Field(..., description="Original course content")
    regenerate_parameters: List[str] = Field(..., description="List of parameters to regenerate: ['badge_style', 'badge_tone', 'criterion_style', 'badge_level']")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")


class AppendDataRequest(BaseModel):
    badge_id: str = Field(..., description="ID of the badge to edit")
    append_data: Dict[str, Any] = Field(..., description="Additional data to append to the badge")


class BadgeRegenerateRequest(BaseModel):
    """Request model for badge regeneration using custom instructions"""
    custom_instructions: str  # e.g., "give badge name", "make it more concise", "focus on leadership"
    institution: Optional[str] = None  # Optional: override institution from last badge


class FieldRegenerateRequest(BaseModel):
    """Request model for regenerating specific badge fields"""
    badge_id: str = Field(..., description="ID of the badge to regenerate")
    field_to_change: Literal["title", "description", "criteria"] = Field(..., description="Which field to regenerate")
    badge_style: Optional[str] = Field(default=None, description="Override badge style")
    badge_tone: Optional[str] = Field(default=None, description="Override badge tone")
    criterion_style: Optional[str] = Field(default=None, description="Override criteria style")
    badge_level: Optional[str] = Field(default=None, description="Override badge level")
    institution: Optional[str] = Field(default=None, description="Override institution")
    custom_instructions: Optional[str] = Field(default=None, description="Custom instructions for regeneration")
