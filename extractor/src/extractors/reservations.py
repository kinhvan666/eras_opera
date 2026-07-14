# extractor/src/extractors/reservations.py
from typing import List
from ..client import BaseOperaClient
from ..models import Reservation

class ReservationExtractor:
    def __init__(self, client: BaseOperaClient):
        self.client = client

    async def fetch_recent_reservations(self) -> List[dict]:
        """Fetches reservations created in the last day."""
        # The endpoint and params need to be confirmed from the OPERA Cloud API documentation.
        # Example endpoint and params:
        endpoint = "/res/v1/hotels/YOUR_HOTEL/reservations"
        params = {
            "query": "createDate=ge:$(SYSDATE-1)",
            "limit": 100
        }

        raw_reservations = await self.client.fetch_all(endpoint=endpoint, params=params)

        # For this phase, we return raw dicts. Pydantic validation can be added later.
        # validated_reservations = [Reservation.model_validate(res) for res in raw_reservations]
        return raw_reservations
