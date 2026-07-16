# extractor/src/extractors/reservations.py
from typing import List
from ..client import BaseOperaClient
from ..config import settings

# Statuses that represent actively staying guests not yet captured by
# arrival-date range queries (OPERA excludes them from that path).
_ACTIVE_STATUSES = ["InHouse", "CheckedIn", "DueIn", "DueOut"]


class ReservationExtractor:
    def __init__(self, client: BaseOperaClient):
        self.client = client

    async def fetch_reservations(self, arrival_start_date: str, arrival_end_date: str) -> List[dict]:
        """Fetches reservations with arrival date in the given range (YYYY-MM-DD).
        OPERA's reservation search only supports a range on arrival/stay dates, not created date."""
        endpoint = f"/rsv/v1/hotels/{settings.opera_hotel_id}/reservations"
        params = {
            "arrivalStartDate": arrival_start_date,
            "arrivalEndDate": arrival_end_date,
            "limit": 100,
        }

        response = await self.client.fetch_all(endpoint=endpoint, params=params)
        return response

    async def fetch_active_reservations(self) -> List[dict]:
        """Fetches all currently active/in-house reservations regardless of arrival date.

        OPERA does not return InHouse/CheckedIn guests in the arrivalDate range query,
        so we make a separate request filtered by status.  These records are upserted
        alongside historical data — the ON CONFLICT clause in insert_raw_data deduplicates.

        httpx serialises list values as repeated query params (collectionFormat: multi),
        so {"reservationStatuses": ["InHouse", "CheckedIn"]} -> ?reservationStatuses=InHouse&reservationStatuses=CheckedIn.
        """
        endpoint = f"/rsv/v1/hotels/{settings.opera_hotel_id}/reservations"
        params = {
            "reservationStatuses": _ACTIVE_STATUSES,
            "limit": 100,
        }

        response = await self.client.fetch_all(endpoint=endpoint, params=params)
        return response
