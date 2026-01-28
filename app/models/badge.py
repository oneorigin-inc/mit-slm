from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class BadgeValidated(BaseModel):
    badge_name: str
    badge_description: str
    criteria: Dict[str, Any]
    raw_model_output: str

class BadgeResponse(BaseModel):
    credentialSubject: Dict[str, Any]
    imageConfig: Optional[Dict[str, Any]] = None
    badge_id: str
    metrics: Optional[Dict[str, Any]] = None
    skills: Optional[List[Dict[str, Any]]] = None
    badge_configuration: Optional[Dict[str, Any]] = None
    enable_image_generation: bool = False
    enable_skill_extraction: bool = False


class PreviousBadge(BaseModel):
    """
    Model for a single previous badge retrieved from the database.
    Contains COMPLETE badge data including image, alignment/ESCO skills, and configuration.
    """
    similarity_score: float
    # Core badge info
    badge_name: str
    badge_description: str
    criteria: Dict[str, Any]
    # Complete credential subject (OB3 format) - contains everything
    credentialSubject: Optional[Dict[str, Any]] = None
    # Image data
    imageConfig: Optional[Dict[str, Any]] = None
    image_base64: Optional[str] = None
    # Alignment/ESCO skills (extracted from credentialSubject for quick access)
    alignment: Optional[List[Dict[str, Any]]] = None
    # Skills/LAiSER data
    skills: Optional[List[Dict[str, Any]]] = None
    # Configuration
    badge_configuration: Optional[Dict[str, Any]] = None
    badge_id: Optional[str] = None
    # Metrics
    metrics: Optional[Dict[str, Any]] = None
    # Flags
    enable_image_generation: Optional[bool] = False
    enable_skill_extraction: Optional[bool] = False
    # Original course input
    course_input: Optional[str] = None
    # Legacy fields
    courses: Optional[List[Dict[str, Any]]] = None


class PreviousBadgesResponse(BaseModel):
    """Response model for retrieving previous similar badges with COMPLETE data."""
    previous_badges: List[PreviousBadge]
    total_count: int
    query_summary: str
    rag_available: bool = True

