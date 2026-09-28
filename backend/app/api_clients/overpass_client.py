import httpx
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# Map YuktiFi category_ids to Overpass specific key-value pairs
CATEGORY_TAG_MAP = {
    "retail_kirana": '["shop"="convenience"]',
    "dairy": '["shop"="dairy"]',
    "tailoring": '["craft"="tailor"]',
    "flour_mill": '["craft"="mill"]',
    "poultry": '["landuse"="farm"]["farm"="poultry"]', # Example proxy
}


class OverpassClient:
    """
    Client for OpenStreetMap's Overpass API.
    Fetches actual shops and competitors within a radius.

    Two things this client is careful about, both of which used to be wrong.

    **A failed survey is not a survey that found nothing.** Both used to return
    `[]`, so a timeout, a DNS failure and an HTTP 504 were indistinguishable from
    "there are no competitors here". Downstream, that turned a network error
    into a measured competitor count of zero, and a founder reading a saturated
    market was told it was empty. `get_competitor_survey` now reports the two
    separately and `get_competitors_in_radius` is a wrapper that keeps the old
    list-returning signature for callers that do not care.

    **The client does not wait longer than the server has been asked to work.**
    The query used to declare `[timeout:25]` while the HTTP call abandoned it
    after 5 seconds, so the server was told it had 25 seconds to think about a
    query nobody was waiting for. The budget now comes from
    `settings.overpass_timeout_seconds`, and the HTTP timeout is that budget plus
    a margin for the response to come back.
    """

    BASE_URL = "https://overpass-api.de/api/interpreter"

    #: Extra seconds allowed for the response to arrive after the server's own
    #: budget is spent. Without this a server that uses its full budget
    #: successfully is still reported as a timeout.
    RESPONSE_MARGIN_S = 5.0

    def _budget(self) -> Tuple[float, float]:
        """(server budget, client wait) in seconds."""
        server = max(1.0, float(settings.overpass_timeout_seconds))
        return server, server + self.RESPONSE_MARGIN_S

    def get_competitor_survey(
        self, lat: float, lon: float, category_id: str, radius_meters: int = 5000
    ) -> Dict[str, Any]:
        """
        Run the survey and report whether it actually ran.

        Returns `{"status", "records", "error"}` where status is:

        * ``"ok"``     - the query completed; `records` may legitimately be empty
        * ``"failed"`` - the query did not complete; `records` is meaningless

        An empty list under ``"ok"`` is a statement about OpenStreetMap coverage.
        Under ``"failed"`` it is a statement about nothing at all.
        """
        tag_filter = CATEGORY_TAG_MAP.get(category_id, '["shop"]')
        server_timeout, client_timeout = self._budget()

        # The server-side budget is an integer in Overpass QL, so it is floored
        # to whole seconds. It is derived from the same setting as the client
        # wait rather than being a second, independently-maintained number.
        query = f"""
        [out:json][timeout:{int(server_timeout)}];
        (
          node{tag_filter}(around:{radius_meters},{lat},{lon});
          way{tag_filter}(around:{radius_meters},{lat},{lon});
          relation{tag_filter}(around:{radius_meters},{lat},{lon});
        );
        out center;
        """

        try:
            with httpx.Client(
                headers={"User-Agent": "YuktiFi/1.0 (market intelligence; contact@yukti.in)"},
                timeout=client_timeout,
            ) as client:
                response = client.post(self.BASE_URL, data={"data": query})
                response.raise_for_status()
                data = response.json()

            elements = data.get("elements", [])
            competitors: List[Dict[str, Any]] = []

            for el in elements:
                # 'center' for ways/relations, 'lat'/'lon' for nodes.
                el_lat = el.get("lat")
                el_lon = el.get("lon")
                if el_lat is None or el_lon is None:
                    center = el.get("center") or {}
                    el_lat = center.get("lat")
                    el_lon = center.get("lon")

                # `if not el_lat` would drop a node at exactly 0.0 - the Equator
                # or the Prime Meridian - because zero is falsy. Null is the only
                # thing that means "absent" here.
                if el_lat is None or el_lon is None:
                    continue

                el_tags = el.get("tags") or {}

                dist_km = self._haversine(lat, lon, el_lat, el_lon)

                competitors.append({
                    "id": str(el["id"]),
                    "name": el_tags.get("name", el_tags.get("brand", "Unnamed Business")),
                    "type": el_tags.get("shop", el_tags.get("craft", category_id)),
                    "lat": el_lat,
                    "lon": el_lon,
                    "distance_km": round(dist_km, 2),
                })

            # Sort by closest first.
            competitors.sort(key=lambda x: x["distance_km"])
            logger.info(
                "Overpass API found %d competitors for '%s' around %s,%s",
                len(competitors), category_id, lat, lon,
            )
            return {"status": "ok", "records": competitors, "error": None}

        except Exception as e:
            # Recorded rather than swallowed. The caller is expected to
            # distinguish this from a completed survey that found nothing.
            logger.error("Overpass API error for '%s': %s", category_id, e)
            return {"status": "failed", "records": [], "error": str(e)}

    def get_competitors_in_radius(
        self, lat: float, lon: float, category_id: str, radius_meters: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        Competitor records only, for callers that do not distinguish a failed
        survey from an empty one.

        Prefer `get_competitor_survey`. This wrapper keeps the old signature so
        that an existing caller cannot be silently handed a fabricated empty
        result by a change here.
        """
        return self.get_competitor_survey(lat, lon, category_id, radius_meters)["records"]

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance in kilometers between two points on the earth."""
        R = 6371.0 # Radius of earth in kilometers
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
