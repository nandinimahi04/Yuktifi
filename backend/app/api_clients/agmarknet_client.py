"""
Commodity prices from AGMARKNET / data.gov.in.

The previous version of this client asked a language model to "estimate realistic
live wholesale commodity prices" and, if that also failed, returned a hardcoded
dict (`Wheat: 2200`, `Milk: 55`). Both paths were then reported to the user as
`data_origin: "AGMARKNET / Estimations"`, which put a fabricated number under a
government dataset's name and let it drive revenue projections and break-even
analysis.

Price is one of the two inputs that decide whether a business is viable. A
hallucinated price is worse than no price, because it produces a confident answer
rather than an abstention. So there is no heuristic fallback here at all: if the
official source cannot supply a price, this client returns None and the caller
reports the price as UNAVAILABLE.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.evidence import finite, validated, EvidenceState

logger = logging.getLogger(__name__)

#: data.gov.in resource for daily AGMARKNET arrivals and prices.
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

#: Prices older than this are reported as STALE rather than as current.
MAX_PRICE_AGE_DAYS = 7

#: A modal price outside this band is a data error, not a market. Indian
#: agricultural commodities do not span four orders of magnitude in a week.
MIN_PLAUSIBLE_PRICE = 0.5
MAX_PLAUSIBLE_PRICE = 200_000.0


class AgmarknetClient:
    """Fetches wholesale mandi prices. Returns None rather than guessing."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else settings.data_gov_in_api_key
        self.base_url = BASE_URL

    # ── Public API ──────────────────────────────────────────────────────────

    async def get_prices_async(
        self, state: str, commodity: str
    ) -> Optional[dict[str, Any]]:
        """
        Low / high / modal wholesale price for a commodity in a state.

        Returns None when no price can be sourced. Callers must treat None as
        "price unknown" and abstain, not as zero.
        """
        if not state or not commodity:
            return None
        if not self.api_key:
            logger.info("No data.gov.in key configured; commodity price is unavailable.")
            return None
        if not settings.network_allowed:
            logger.info("Network disabled (demo mode); commodity price is unavailable.")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "api-key": self.api_key,
                        "format": "json",
                        "filters[state]": state.title(),
                        "filters[commodity]": commodity.title(),
                        "limit": 100,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 - any transport failure means no price
            logger.error("AGMARKNET request failed: %s", exc)
            return None

        return self._summarise(payload.get("records", []), state, commodity)

    # ── Parsing ─────────────────────────────────────────────────────────────

    def _summarise(
        self, records: list[dict[str, Any]], state: str, commodity: str
    ) -> Optional[dict[str, Any]]:
        """
        Reduce a batch of mandi rows to a low/modal/high price band.

        Rows with a missing or implausible modal price are dropped rather than
        coerced to zero, because `sum(...)/len(...)` over a list containing zeros
        silently understates the market.
        """
        modals: list[float] = []
        mandis: list[str] = []
        for row in records:
            modal = finite(row.get("modal_price"))
            if modal is None or not (MIN_PLAUSIBLE_PRICE <= modal <= MAX_PLAUSIBLE_PRICE):
                continue
            modals.append(modal)
            mandi = row.get("market") or row.get("market_center")
            if mandi:
                mandis.append(str(mandi))

        if not modals:
            logger.warning(
                "AGMARKNET returned %d rows for %s/%s but none had a usable modal price.",
                len(records), state, commodity,
            )
            return None

        modals.sort()
        n = len(modals)
        # Median, not mean: one mis-reported mandi should not move the price.
        modal_price = (
            modals[n // 2] if n % 2 else (modals[n // 2 - 1] + modals[n // 2]) / 2
        )
        low = modals[0]
        high = modals[-1]

        record = validated(
            "commodity_price",
            round(modal_price, 2),
            "agmarknet",
            unit="INR per quintal (as reported)",
            minimum=MIN_PLAUSIBLE_PRICE,
            maximum=MAX_PLAUSIBLE_PRICE,
        )
        if record.state is EvidenceState.CONFLICTING:
            logger.error("AGMARKNET price for %s/%s failed validation: %s", state, commodity, record.limitations)
            return None

        return {
            "low": round(low, 2),
            "modal": record.value,
            "high": round(high, 2),
            "unit": "INR per quintal",
            "reporting_mandis": n,
            "mandi_names": sorted(set(mandis))[:10],
            "state": state,
            "commodity": commodity,
            "evidence_state": record.state.value,
            "confidence": record.confidence.value,
            "is_estimate": False,
            "data_origin": "AGMARKNET (Ministry of Agriculture)",
            "source_url": "https://www.enam.gov.in/web/dashboard/agmarknet",
            "method": f"Median modal price across {n} reporting mandi rows",
            "limitations": (
                "Wholesale mandi price, not retail. A retail price requires a documented margin "
                f"on top. Based on {n} reporting mandis in {state} only; mandi coverage is uneven "
                "and does not represent every market in the state."
            ),
        }
