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


class RetrievedBadgeItem(BaseModel):
    """Model for a single retrieved badge"""
    score: float
    badge_name: str
    badge_description: str
    criteria: str


class RetrieveSimilarBadgesResponse(BaseModel):
    """Response model for similar badges retrieval"""
    query: str
    retrieved_badges: List[RetrievedBadgeItem]
    count: int
    message: str

