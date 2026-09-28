from typing import Optional
from .events.competition import NEW_COMPETITOR_EVENT, SimulatorEvent

class EventEngine:
    def __init__(self):
        self.events = {
            "new_competitor": NEW_COMPETITOR_EVENT
        }
        
    def get_event(self, event_id: str) -> Optional[SimulatorEvent]:
        return self.events.get(event_id)
