from typing import Optional, Literal
from pydantic import BaseModel
from datetime import datetime

class DataProvenance(BaseModel):
    source_type: Literal[
        "government",
        "open_data",
        "user_input",
        "calculated",
        "model_estimate",
        "ai_inference",
        "demo_data"
    ]
    source_name: str
    source_url: Optional[str] = None
    dataset_name: Optional[str] = None
    last_updated: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    methodology: Optional[str] = None

class MetricWithProvenance(BaseModel):
    value: float | int | str | dict | list
    provenance: DataProvenance
