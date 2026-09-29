"""
Consumer Affairs Retail Price Provider (Phase 2).

Accesses Department of Consumer Affairs (DCA) Price Monitoring Division daily retail prices.
Monitors 22 core essential commodities across official market centres (Solapur, Pune, Mumbai, State Average).

Rules:
- Daily observations preserved with exact observed_at dates.
- Timeseries analytics (7D, 30D, 90D, YoY, Volatility CV).
- If insufficient observations, returns INSUFFICIENT_DATA / UNAVAILABLE rather than 0.
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

RAW_DCA_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "consumer_affairs" / "daily" / "consumer_affairs_daily_prices.json"

class ConsumerAffairsProvider:
    """Provider for DCA daily retail commodity prices and timeseries analytics."""
    _instance: Optional[ConsumerAffairsProvider] = None

    def __new__(cls) -> ConsumerAffairsProvider:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self._by_centre_commodity: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

        if RAW_DCA_FILE.exists():
            try:
                with RAW_DCA_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.records = data.get("records", [])

                for r in self.records:
                    centre = r.get("market_centre", "").strip().lower()
                    cid = r.get("commodity_id") or commodity_mapper.resolve_commodity(r.get("commodity", ""), "consumer_affairs")
                    if cid:
                        r["commodity_id"] = cid
                        key = (centre, cid)
                        if key not in self._by_centre_commodity:
                            self._by_centre_commodity[key] = []
                        self._by_centre_commodity[key].append(r)

                # Sort chronologically
                for k in self._by_centre_commodity:
                    self._by_centre_commodity[k].sort(key=lambda x: x.get("observed_at", ""))
            except Exception as e:
                logger.error("Failed to load DCA data from %s: %s", RAW_DCA_FILE, e)
        else:
            logger.warning("DCA raw prices file not found at %s", RAW_DCA_FILE)

    def _resolve_centre(self, preferred_centre: Optional[str] = None) -> str:
        """Resolve market centre with fallback to Solapur or Maharashtra State Average."""
        if preferred_centre:
            norm = preferred_centre.strip().lower()
            for (c, _), _ in self._by_centre_commodity.items():
                if norm in c or c in norm:
                    return c
        return "solapur"

    def get_price_series(
        self,
        commodity_id_or_name: str,
        market_centre: Optional[str] = "Solapur",
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Returns chronological list of observations for the commodity and centre."""
        cid = commodity_mapper.resolve_commodity(commodity_id_or_name, "consumer_affairs") or commodity_id_or_name.lower().strip()
        centre = self._resolve_centre(market_centre)

        series = self._by_centre_commodity.get((centre, cid), [])
        if not series:
            # Fallback to state average
            series = self._by_centre_commodity.get(("maharashtra state average", cid), [])
        if not series:
            # Fallback to any available centre for this commodity
            for (c, c_id), items in self._by_centre_commodity.items():
                if c_id == cid and items:
                    series = items
                    break

        if not series:
            return []

        if days and len(series) > 0:
            # Filter to last `days` days of records
            latest_date_str = series[-1].get("observed_at", "")
            try:
                latest_d = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
                cutoff = latest_d - timedelta(days=days)
                return [r for r in series if datetime.strptime(r["observed_at"], "%Y-%m-%d").date() >= cutoff]
            except Exception:
                return series[-days:]

        return series

    def compute_retail_metrics(
        self,
        commodity_id_or_name: str,
        market_centre: Optional[str] = "Solapur"
    ) -> Dict[str, Any]:
        """
        Computes current_price, avg_7d, avg_30d, avg_90d, change_30d_pct, yoy_pct, and volatility_cv.
        If data is missing or observations < 3, returns state INSUFFICIENT_DATA.
        """
        cid = commodity_mapper.resolve_commodity(commodity_id_or_name, "consumer_affairs") or commodity_id_or_name.lower().strip()
        cinfo = commodity_mapper.get_commodity_info(cid) or {}
        canon_name = cinfo.get("canonical_name", cid.replace("_", " ").title())
        unit = cinfo.get("unit", "INR/kg")

        centre = self._resolve_centre(market_centre)
        series = self._by_centre_commodity.get((centre, cid), [])
        if not series:
            series = self._by_centre_commodity.get(("maharashtra state average", cid), [])

        if not series or len(series) < 3:
            return {
                "commodity_id": cid,
                "commodity_name": canon_name,
                "market_centre": centre.title(),
                "unit": unit,
                "status": "INSUFFICIENT_DATA",
                "current_price": None,
                "avg_7d": None,
                "avg_30d": None,
                "avg_90d": None,
                "change_30d_pct": None,
                "yoy_pct": None,
                "volatility_cv": None,
                "observation_count": len(series),
                "latest_observed_at": None,
                "evidence_state": EvidenceState.MISSING.value,
                "limitations": f"Fewer than 3 daily retail price observations available for {canon_name} in {centre.title()}."
            }

        # Filter out 1-year baseline for daily rolling calculations
        latest_date_str = series[-1]["observed_at"]
        latest_d = datetime.strptime(latest_date_str, "%Y-%m-%d").date()
        
        # Recent observations (within last 90 days)
        cutoff_90 = latest_d - timedelta(days=90)
        cutoff_30 = latest_d - timedelta(days=30)
        cutoff_7 = latest_d - timedelta(days=7)

        recent_obs = [r for r in series if datetime.strptime(r["observed_at"], "%Y-%m-%d").date() >= cutoff_90]
        obs_30d = [r for r in series if datetime.strptime(r["observed_at"], "%Y-%m-%d").date() >= cutoff_30]
        obs_7d = [r for r in series if datetime.strptime(r["observed_at"], "%Y-%m-%d").date() >= cutoff_7]

        current_price = series[-1]["price"]
        avg_7d = round(sum(r["price"] for r in obs_7d) / len(obs_7d), 2) if obs_7d else current_price
        avg_30d = round(sum(r["price"] for r in obs_30d) / len(obs_30d), 2) if obs_30d else current_price
        avg_90d = round(sum(r["price"] for r in recent_obs) / len(recent_obs), 2) if recent_obs else current_price

        # 30-day percentage change
        price_30d_ago = obs_30d[0]["price"] if obs_30d else current_price
        change_30d_pct = round(((current_price - price_30d_ago) / price_30d_ago) * 100.0, 2) if price_30d_ago else 0.0

        # YoY percentage change
        year_ago_cutoff_start = latest_d - timedelta(days=380)
        year_ago_cutoff_end = latest_d - timedelta(days=340)
        yoy_obs = [r for r in series if year_ago_cutoff_start <= datetime.strptime(r["observed_at"], "%Y-%m-%d").date() <= year_ago_cutoff_end]
        
        yoy_pct = None
        if yoy_obs:
            base_year_price = yoy_obs[0]["price"]
            if base_year_price > 0:
                yoy_pct = round(((current_price - base_year_price) / base_year_price) * 100.0, 2)

        # Volatility CV over 30d: std_dev / mean
        prices_30d = [r["price"] for r in obs_30d]
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
            "market_centre": centre.title(),
            "unit": unit,
            "status": "VALID",
            "current_price": current_price,
            "avg_7d": avg_7d,
            "avg_30d": avg_30d,
            "avg_90d": avg_90d,
            "change_30d_pct": change_30d_pct,
            "yoy_pct": yoy_pct,
            "volatility_cv": volatility_cv,
            "observation_count": len(series),
            "latest_observed_at": latest_date_str,
            "evidence_state": EvidenceState.VERIFIED.value,
            "source_id": "consumer_affairs",
            "source_name": "Department of Consumer Affairs (PMS)",
            "limitations": f"Daily retail price monitored at {centre.title()} market centre."
        }

    def get_retail_price_record(self, commodity_id_or_name: str, market_centre: Optional[str] = "Solapur") -> EvidenceRecord:
        """Returns a verified EvidenceRecord for the retail price of the commodity."""
        metrics = self.compute_retail_metrics(commodity_id_or_name, market_centre)
        if metrics.get("status") != "VALID" or metrics.get("current_price") is None:
            return unavailable(
                metric=f"retail_price_{metrics.get('commodity_id')}",
                why=metrics.get("limitations", "Insufficient retail price data"),
                source_id="consumer_affairs"
            )

        return verified(
            metric=f"retail_price_{metrics['commodity_id']}",
            value=metrics["current_price"],
            unit=metrics["unit"],
            source_id="consumer_affairs",
            dataset="DCA Price Monitoring System (PMS)",
            geography=metrics["market_centre"],
            geography_level="market_centre",
            reference_date=metrics.get("latest_observed_at", ""),
            limitations=metrics["limitations"]
        )

# Module-level singleton
consumer_affairs_provider = ConsumerAffairsProvider()
