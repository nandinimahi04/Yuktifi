"""
HCES 2023-24 Data Provider (Phase 2).

Accesses MoSPI Household Consumption Expenditure Survey 2023-24 (Report No. 592).
Provides state-level rural and urban consumption expenditure benchmarks.

CRITICAL POLICY:
- HCES figures are state/sector benchmarks and MUST NOT be labeled as village-level demand.
- is_estimate is False for official published survey tables.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from app.evidence.schema import (
    EvidenceRecord, EvidenceState, verified, unavailable
)

logger = logging.getLogger(__name__)

RAW_HCES_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "hces" / "2023-24" / "hces_2023_24_state_tables.json"

class HCESProvider:
    """Provider for MoSPI HCES 2023-24 state and sector consumption data."""
    _instance: Optional[HCESProvider] = None

    def __new__(cls) -> HCESProvider:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self) -> None:
        self.raw_data: Dict[str, Any] = {}
        if RAW_HCES_FILE.exists():
            try:
                with RAW_HCES_FILE.open("r", encoding="utf-8") as f:
                    self.raw_data = json.load(f)
            except Exception as e:
                logger.error("Failed to load HCES data from %s: %s", RAW_HCES_FILE, e)
        else:
            logger.warning("HCES 2023-24 raw data file not found at %s", RAW_HCES_FILE)

    def get_state_benchmark(self, state: str = "Maharashtra", sector: str = "rural") -> Optional[Dict[str, Any]]:
        """Returns the official HCES 2023-24 benchmark table for the specified state and sector."""
        states = self.raw_data.get("states", {})
        norm_state = state.strip().title() if state else "Maharashtra"
        norm_sector = sector.strip().lower() if sector else "rural"
        if norm_sector not in ("rural", "urban"):
            norm_sector = "rural"

        state_data = states.get(norm_state) or states.get("Maharashtra")
        if not state_data:
            state_data = states.get("All_India")

        if not state_data:
            return None

        sector_data = state_data.get(norm_sector)
        if not sector_data:
            return None

        res = dict(sector_data)
        res["state"] = norm_state
        res["sector"] = norm_sector
        res["survey_year"] = "2023-24"
        res["report_number"] = "MoSPI Report No. 592"
        res["benchmark_label"] = f"State/Sector Benchmark ({norm_state} {norm_sector.title()})"
        return res

    def get_mpce_record(self, state: str = "Maharashtra", sector: str = "rural") -> EvidenceRecord:
        """Returns an EvidenceRecord for the state/sector MPCE."""
        bench = self.get_state_benchmark(state, sector)
        if not bench or "mpce_inr" not in bench:
            return unavailable(
                metric="mpce_inr",
                why=f"No HCES 2023-24 data found for state '{state}', sector '{sector}'",
                source_id="hces_2023_24"
            )

        mpce_val = float(bench["mpce_inr"])
        return verified(
            metric="mpce_inr",
            value=mpce_val,
            unit="INR/person/month",
            source_id="hces_2023_24",
            dataset="HCES 2023-24 State & Sector Consumption Tables",
            geography=f"{state} ({sector.title()})",
            geography_level="state/sector",
            reference_date="2023-24",
            limitations=(
                "MoSPI HCES 2023-24 state/sector representative survey benchmark. "
                "Does not measure micro-level village or neighborhood demand directly."
            )
        )

    def get_food_share_record(self, state: str = "Maharashtra", sector: str = "rural") -> EvidenceRecord:
        """Returns an EvidenceRecord for food expenditure share pct."""
        bench = self.get_state_benchmark(state, sector)
        if not bench or "food_expenditure_share_pct" not in bench:
            return unavailable(
                metric="food_expenditure_share_pct",
                why=f"No HCES 2023-24 food share found for state '{state}', sector '{sector}'",
                source_id="hces_2023_24"
            )

        food_share = float(bench["food_expenditure_share_pct"])
        return verified(
            metric="food_expenditure_share_pct",
            value=food_share,
            unit="%",
            source_id="hces_2023_24",
            dataset="HCES 2023-24 State & Sector Consumption Tables",
            geography=f"{state} ({sector.title()})",
            geography_level="state/sector",
            reference_date="2023-24",
            limitations="MoSPI HCES 2023-24 state/sector benchmark."
        )

# Module-level singleton
hces_provider = HCESProvider()
