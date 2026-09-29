"""
AGMARKNET / eNAM Mandi Price Provider (Phase 2).

Accesses official agricultural mandi prices (Ministry of Agriculture).
Resolves nearest APMC mandi, arrival dates, min/max/modal prices, and wholesale price dynamics.

POLICY:
- Mandi price is labeled "Nearest mapped mandi price".
- Distance to mapped mandi is reported explicitly.
- Wholesale INR/quintal is converted cleanly to equivalent INR/kg (price / 100).
- If insufficient observations, flags INSUFFICIENT_DATA.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
import logging

from app.evidence.schema import (
    EvidenceRecord, EvidenceState, verified, unavailable
)
from app.data_layer.normalization.commodity_mapper import commodity_mapper

logger = logging.getLogger(__name__)

RAW_AGMARKNET_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "agmarknet" / "daily" / "agmarknet_daily_mandi_prices.json"

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

class AgmarknetProvider:
    """Provider for AGMARKNET/eNAM mandi wholesale prices and proximity resolution."""
    _instance: Optional[AgmarknetProvider] = None

    def __new__(cls) -> AgmarknetProvider:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self._by_market_commodity: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._markets_geo: Dict[str, Dict[str, float]] = {}

        if RAW_AGMARKNET_FILE.exists():
            try:
                with RAW_AGMARKNET_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.records = data.get("records", [])

                for r in self.records:
                    market = r.get("market", "").strip().lower()
                    cid = r.get("commodity_id") or commodity_mapper.resolve_commodity(r.get("commodity", ""), "agmarknet")
                    if cid:
                        r["commodity_id"] = cid
                        key = (market, cid)
                        if key not in self._by_market_commodity:
                            self._by_market_commodity[key] = []
                        self._by_market_commodity[key].append(r)

                    if market and "market_lat" in r and "market_lon" in r:
                        if market not in self._markets_geo:
                            self._markets_geo[market] = {
                                "lat": r["market_lat"],
                                "lon": r["market_lon"],
                                "name": r.get("market", "")
                            }

                # Sort chronologically
                for k in self._by_market_commodity:
                    self._by_market_commodity[k].sort(key=lambda x: x.get("arrival_date", ""))
            except Exception as e:
                logger.error("Failed to load AGMARKNET data from %s: %s", RAW_AGMARKNET_FILE, e)
        else:
            logger.warning("AGMARKNET raw prices file not found at %s", RAW_AGMARKNET_FILE)

    def resolve_nearest_market(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        preferred_market: Optional[str] = None
    ) -> Tuple[str, Optional[float]]:
        """Returns (market_key, distance_km)."""
        if preferred_market:
            norm = preferred_market.strip().lower()
            for m in self._markets_geo:
                if norm in m or m in norm:
                    dist = _haversine_km(lat, lon, self._markets_geo[m]["lat"], self._markets_geo[m]["lon"]) if (lat and lon) else None
                    return m, dist

        if lat is not None and lon is not None and self._markets_geo:
            best_m = None
            min_dist = float("inf")
            for m, geo in self._markets_geo.items():
                d = _haversine_km(lat, lon, geo["lat"], geo["lon"])
                if d < min_dist:
                    min_dist = d
                    best_m = m
            if best_m:
                return best_m, min_dist

        # Default fallback
        return "solapur apmc", 0.0

    def compute_mandi_metrics(
        self,
        commodity_id_or_name: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        preferred_market: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Computes latest min, max, modal prices, 7D/30D/90D averages, 30D change %, and volatility CV.
        """
        cid = commodity_mapper.resolve_commodity(commodity_id_or_name, "agmarknet") or commodity_id_or_name.lower().strip()
        cinfo = commodity_mapper.get_commodity_info(cid) or {}
        canon_name = cinfo.get("canonical_name", cid.replace("_", " ").title())

        market_key, dist_km = self.resolve_nearest_market(lat, lon, preferred_market)
        series = self._by_market_commodity.get((market_key, cid), [])

        if not series:
            # Fallback to solapur apmc
            series = self._by_market_commodity.get(("solapur apmc", cid), [])
            market_key = "solapur apmc"

        market_display = self._markets_geo.get(market_key, {}).get("name", market_key.title())

        if not series or len(series) < 3:
            return {
                "commodity_id": cid,
                "commodity_name": canon_name,
                "market_name": market_display,
                "distance_km": dist_km,
                "status": "INSUFFICIENT_DATA",
                "latest_arrival_date": None,
                "modal_price_quintal": None,
                "min_price_quintal": None,
                "max_price_quintal": None,
                "modal_price_kg": None,
                "avg_7d_modal": None,
                "avg_30d_modal": None,
                "avg_90d_modal": None,
                "change_30d_pct": None,
                "volatility_cv": None,
                "observation_count": len(series),
                "evidence_state": EvidenceState.MISSING.value,
                "limitations": f"Fewer than 3 mandi arrival price observations available for {canon_name} at {market_display}."
            }

        latest_rec = series[-1]
        latest_d = datetime.strptime(latest_rec["arrival_date"], "%Y-%m-%d").date()

        cutoff_90 = latest_d - timedelta(days=90)
        cutoff_30 = latest_d - timedelta(days=30)
        cutoff_7 = latest_d - timedelta(days=7)

        recent_obs = [r for r in series if datetime.strptime(r["arrival_date"], "%Y-%m-%d").date() >= cutoff_90]
        obs_30d = [r for r in series if datetime.strptime(r["arrival_date"], "%Y-%m-%d").date() >= cutoff_30]
        obs_7d = [r for r in series if datetime.strptime(r["arrival_date"], "%Y-%m-%d").date() >= cutoff_7]

        modal_p = latest_rec["modal_price"]
        min_p = latest_rec.get("min_price", modal_p)
        max_p = latest_rec.get("max_price", modal_p)
        modal_kg = round(modal_p / 100.0, 2)

        avg_7d = round(sum(r["modal_price"] for r in obs_7d) / len(obs_7d), 2) if obs_7d else modal_p
        avg_30d = round(sum(r["modal_price"] for r in obs_30d) / len(obs_30d), 2) if obs_30d else modal_p
        avg_90d = round(sum(r["modal_price"] for r in recent_obs) / len(recent_obs), 2) if recent_obs else modal_p

        price_30d_ago = obs_30d[0]["modal_price"] if obs_30d else modal_p
        change_30d_pct = round(((modal_p - price_30d_ago) / price_30d_ago) * 100.0, 2) if price_30d_ago else 0.0

        # Volatility CV over 30d
        prices_30d = [r["modal_price"] for r in obs_30d]
        if len(prices_30d) >= 2:
            mean_p = sum(prices_30d) / len(prices_30d)
            variance = sum((p - mean_p) ** 2 for p in prices_30d) / (len(prices_30d) - 1)
            std_dev = math.sqrt(variance)
            volatility_cv = round(std_dev / mean_p, 4) if mean_p > 0 else 0.0
        else:
            volatility_cv = 0.0

        return {
            "commodity_id": cid,
            "commodity_name": canon_name,
            "market_name": market_display,
            "distance_km": dist_km,
            "status": "VALID",
            "latest_arrival_date": latest_rec["arrival_date"],
            "variety": latest_rec.get("variety", "Standard"),
            "grade": latest_rec.get("grade", "FAQ"),
            "unit": "INR/quintal",
            "unit_kg": "INR/kg",
            "modal_price_quintal": modal_p,
            "min_price_quintal": min_p,
            "max_price_quintal": max_p,
            "modal_price_kg": modal_kg,
            "avg_7d_modal": avg_7d,
            "avg_30d_modal": avg_30d,
            "avg_90d_modal": avg_90d,
            "change_30d_pct": change_30d_pct,
            "volatility_cv": volatility_cv,
            "observation_count": len(series),
            "evidence_state": EvidenceState.VERIFIED.value,
            "source_id": "agmarknet",
            "source_name": "AGMARKNET / eNAM (MoA)",
            "limitations": f"Nearest mapped mandi modal price from {market_display} ({dist_km} km away). Wholesale APMC arrival, not retail."
        }

    def get_mandi_price_record(
        self,
        commodity_id_or_name: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        preferred_market: Optional[str] = None
    ) -> EvidenceRecord:
        """Returns a verified EvidenceRecord for the mandi modal price."""
        metrics = self.compute_mandi_metrics(commodity_id_or_name, lat, lon, preferred_market)
        if metrics.get("status") != "VALID" or metrics.get("modal_price_quintal") is None:
            return unavailable(
                metric=f"mandi_price_{metrics.get('commodity_id')}",
                why=metrics.get("limitations", "Insufficient mandi price data"),
                source_id="agmarknet"
            )

        return verified(
            metric=f"mandi_price_{metrics['commodity_id']}",
            value=metrics["modal_price_quintal"],
            unit="INR/quintal",
            source_id="agmarknet",
            dataset="AGMARKNET Daily Mandi Prices",
            geography=metrics["market_name"],
            geography_level="market",
            reference_date=metrics.get("latest_arrival_date", ""),
            limitations=metrics["limitations"]
        )

# Module-level singleton
agmarknet_provider = AgmarknetProvider()
