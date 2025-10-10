from pydantic import BaseModel
from typing import Dict, Any, Optional

class BadgeValidated(BaseModel):
    badge_name: str
    badge_description: str  
    criteria: Dict[str, Any]
    raw_model_output: str

class BadgeResponse(BaseModel):
    credentialSubject: Dict[str, Any]
    imageConfig: Dict[str, Any] 
    badge_id: str

