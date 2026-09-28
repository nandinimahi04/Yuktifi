import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CensusClient:
    """
    Census India demographics. **Not implemented — this is a stub.**

    It has never made a request. There is no URL, no request construction and no
    response parsing, and it will keep returning `None` after a key is supplied.
    The reason is recorded here rather than left to be discovered: the earlier
    version of this file imported `httpx`, accepted an `api_key`, and logged
    "Falling back to next data source" on every call, which reads as a working
    client that degrades gracefully. It is not a working client. It performs no
    lookup, and the fallback it claimed to make is the caller's decision, not
    this class's.

    Census population is currently supplied by the areal-interpolation path in
    `WorldPopClient`, which does produce figures and labels them as estimates
    rather than as census counts. `DataRetrieval` therefore treats a `None` from
    here as "no census figure available" and says so, rather than treating it as
    a transport failure worth retrying.

    Implementing this properly means resolving a coordinate to a Census Village
    Code before any catalogue lookup is possible, because data.gov.in census
    tables are keyed by village code and not by latitude. Until that exists,
    `get_demographics` is honest about returning nothing.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def get_demographics(self, lat: float, lon: float) -> Optional[Dict[str, int]]:
        """
        Always returns `None`. No census request is made, with or without a key.
        """
        if self.api_key:
            logger.info(
                "Census India client is not implemented; the supplied API key will not be used. "
                "Population is served by the areal-estimate path and is labelled as an estimate."
            )
        else:
            logger.info(
                "No Census India API key provided, and the client is not implemented in any case. "
                "Population figures come from the areal-estimate path, which reports estimates and "
                "not census counts."
            )
        return None
