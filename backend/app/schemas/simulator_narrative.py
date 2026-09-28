from pydantic import BaseModel

class SimulatorNarrative(BaseModel):
    narrative: str
    advice: str
