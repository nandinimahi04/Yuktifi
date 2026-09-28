from pydantic import BaseModel
from typing import Optional

class CompetitorResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    estimated_scale: Optional[int] = None
    confidence: Optional[str] = None

    class Config:
        orm_mode = True
