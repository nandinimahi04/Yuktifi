from pydantic import BaseModel
from typing import List

class CompetitorAnalysis(BaseModel):
    customer_strengths: List[str]
    customer_complaints: List[str]
    opportunities: List[str]
