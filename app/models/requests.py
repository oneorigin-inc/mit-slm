from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class BadgeRequest(BaseModel):
    course_input: str = Field(..., description="Course content or description to generate badge from. Can be multiple courses separated by newlines, semicolons, or 'and'")
    badge_style: str = Field(default="", description="Style of badge generation")
    badge_tone: str = Field(default="", description="Tone for badge content")
    criterion_style: str = Field(default="", description="Style for criteria generation")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    badge_level: str = Field(default="", description="Badge difficulty level")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")

class RegenerationRequest(BaseModel):
    course_input: str = Field(..., description="Original course content")
    regenerate_parameters: List[str] = Field(..., description="List of parameters to regenerate: ['badge_style', 'badge_tone', 'criterion_style', 'badge_level']")
    custom_instructions: Optional[str] = Field(default=None, description="Additional custom requirements")
    institution: Optional[str] = Field(default=None, description="Issuing institution name")

class AppendDataRequest(BaseModel):
    badge_id: str = Field(..., description="ID of the badge to edit")
    append_data: Dict[str, Any] = Field(..., description="Additional data to append to the badge")

# Supporting Pydantic model for the regenerate request
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