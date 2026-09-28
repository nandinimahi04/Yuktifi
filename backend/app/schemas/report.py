from pydantic import BaseModel
from typing import Optional


class ReportRequest(BaseModel):
    session_id: str
    format: str = "html"  # "html" or "pdf"


class ReportResponse(BaseModel):
    session_id: str
    html_content: str
    generated_at: str


class ExplainRequest(BaseModel):
    session_id: str
    question: str
    language: str = "English"


class ExplainResponse(BaseModel):
    answer: str
    source: str  # "ai" or "template"
    confidence: str
