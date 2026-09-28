from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

# In a real app this would come from an LGD database.
# For the prototype, we provide a static structured list to make the UI dynamic.
STATES = [
    {"id": "MH", "name": "Maharashtra"},
    {"id": "GJ", "name": "Gujarat"},
    {"id": "KA", "name": "Karnataka"}
]

DISTRICTS = {
    "MH": [
        {"id": "MH_SOL", "name": "Solapur"},
        {"id": "MH_PUN", "name": "Pune"},
        {"id": "MH_NSK", "name": "Nashik"}
    ],
    "GJ": [
        {"id": "GJ_AMD", "name": "Ahmedabad"},
        {"id": "GJ_SUR", "name": "Surat"}
    ],
    "KA": [
        {"id": "KA_BLR", "name": "Bangalore"},
        {"id": "KA_MYS", "name": "Mysore"}
    ]
}

@router.get("/states")
async def get_states() -> List[Dict[str, str]]:
    return STATES

@router.get("/districts")
async def get_districts(state_id: str) -> List[Dict[str, str]]:
    return DISTRICTS.get(state_id, [])
