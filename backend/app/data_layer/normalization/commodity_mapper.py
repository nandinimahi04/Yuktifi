"""
Commodity Taxonomy Mapper (Phase 2).

Loads configuration from commodity_taxonomy.yaml and resolves:
- Source specific commodity names (Consumer Affairs, AGMARKNET) to canonical commodity IDs
- Business category input cost profiles and weighting structures
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import logging

logger = logging.getLogger(__name__)

TAXONOMY_FILE = Path(__file__).resolve().parent.parent / "commodity_taxonomy.yaml"

class CommodityMapper:
    """Singleton mapper for commodity taxonomy across official data sources."""
    _instance: Optional[CommodityMapper] = None

    def __new__(cls) -> CommodityMapper:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        self.commodities: Dict[str, Any] = {}
        self.business_profiles: Dict[str, Any] = {}
        self.ca_lookup: Dict[str, str] = {}
        self.agmarknet_lookup: Dict[str, str] = {}

        if TAXONOMY_FILE.exists():
            try:
                with TAXONOMY_FILE.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    self.commodities = data.get("commodities", {})
                    self.business_profiles = data.get("business_input_profiles", {})

                # Build reverse lookup tables
                for cid, cdata in self.commodities.items():
                    for name in cdata.get("consumer_affairs", []):
                        self.ca_lookup[name.strip().lower()] = cid
                    for name in cdata.get("agmarknet", []):
                        self.agmarknet_lookup[name.strip().lower()] = cid
                    # Map canonical name itself
                    canon = cdata.get("canonical_name", "").strip().lower()
                    if canon:
                        self.ca_lookup[canon] = cid
                        self.agmarknet_lookup[canon] = cid
            except Exception as e:
                logger.error("Failed loading commodity taxonomy YAML: %s", e)
        else:
            logger.warning("Commodity taxonomy file not found at %s", TAXONOMY_FILE)

    def resolve_commodity(self, raw_name: str, source: str = "consumer_affairs") -> Optional[str]:
        """Resolve a raw commodity string into canonical commodity ID."""
        if not raw_name:
            return None
        norm = raw_name.strip().lower()
        if source == "consumer_affairs":
            if norm in self.ca_lookup:
                return self.ca_lookup[norm]
            # Match longest keys first to prevent 'wheat' matching inside 'wheat flour (atta)'
            sorted_keys = sorted(self.ca_lookup.keys(), key=lambda k: len(k), reverse=True)
            for key in sorted_keys:
                if key in norm or norm in key:
                    return self.ca_lookup[key]
        elif source == "agmarknet":
            if norm in self.agmarknet_lookup:
                return self.agmarknet_lookup[norm]
            sorted_keys = sorted(self.agmarknet_lookup.keys(), key=lambda k: len(k), reverse=True)
            for key in sorted_keys:
                if key in norm or norm in key:
                    return self.agmarknet_lookup[key]
        else:
            if norm in self.commodities:
                return norm
            if norm in self.ca_lookup:
                return self.ca_lookup[norm]
            if norm in self.agmarknet_lookup:
                return self.agmarknet_lookup[norm]
        return None

    def get_commodity_info(self, commodity_id: str) -> Optional[Dict[str, Any]]:
        return self.commodities.get(commodity_id)

    def get_business_input_profile(self, category_id: str) -> Dict[str, float]:
        """Returns input commodity weight mapping e.g. {'rice': 0.18, 'wheat': 0.12}"""
        cat_key = category_id.lower().strip()
        if cat_key in ("kirana", "retail_shop", "grocery"):
            cat_key = "retail_kirana"
        elif cat_key in ("tea_stall", "chai", "tea_shop"):
            cat_key = "tea_snacks"

        profile = self.business_profiles.get(cat_key, {})
        return profile.get("inputs", {})

    def list_all_commodities(self) -> List[str]:
        return list(self.commodities.keys())

# Module level helper
commodity_mapper = CommodityMapper()
