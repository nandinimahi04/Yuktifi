from typing import Dict, Any, List

class SimulatorEvent:
    def __init__(self, event_id: str, title: str, category: str, trigger_month: int, effects: Dict[str, float], decisions: List[str]):
        self.event_id = event_id
        self.title = title
        self.category = category
        self.trigger_month = trigger_month
        self.effects = effects
        self.decisions = decisions

# Example event from the user's specification
NEW_COMPETITOR_EVENT = SimulatorEvent(
    event_id="new_competitor",
    title="A new competitor enters your market",
    category="competition",
    trigger_month=4,
    effects={
        "demand_change": -0.08,
        "price_pressure": -0.03
    },
    decisions=[
        "reduce_price",
        "increase_marketing",
        "improve_service",
        "do_nothing"
    ]
)
