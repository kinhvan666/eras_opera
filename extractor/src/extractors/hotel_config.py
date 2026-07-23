# extractor/src/extractors/hotel_config.py
from ..client import BaseOperaClient
from ..config import settings

_PAGE_SIZE = 1000  # max allowed by Room Config API


class HotelConfigExtractor:
    def __init__(self, client: BaseOperaClient):
        self.client = client

    async def fetch_hotel_config(self) -> dict:
        """Fetches hotel-level config from Enterprise Configuration API.

        Endpoint: GET /ent/config/v1/hotels/{hotelId}
        """
        endpoint = f"/ent/config/v1/hotels/{settings.opera_hotel_id}"
        return await self.client.fetch_one(endpoint)

    async def fetch_physical_room_count(self) -> int:
        """Counts physical rooms via Room Configuration API.

        Response shape: { "rooms": [ { "room": [...individual rooms...], "hotelId": "..." } ] }
        Each top-level item in rooms[] wraps a room[] sub-array, so we sum inner lengths.

        Uses offset/limit pagination (no hasMore — last page detected when inner
        room count across all items is less than the page size).

        Endpoint: GET /rm/config/v1/hotels/{hotelId}/rooms?physical=true
        """
        endpoint = f"/rm/config/v1/hotels/{settings.opera_hotel_id}/rooms"
        params = {"physical": "true", "limit": _PAGE_SIZE, "offset": 0}
        total = 0

        while True:
            data = await self.client.fetch_one(endpoint, params=dict(params))
            groups = data.get("rooms") or []
            page_count = sum(len(g.get("room") or []) for g in groups)
            total += page_count
            if page_count < _PAGE_SIZE:
                break
            params["offset"] += _PAGE_SIZE

        return total

    async def fetch_business_date(self) -> "datetime.date":
        """Fetches the current business date of the hotel.
        
        Endpoint: GET /bof/v1/hotels/{hotelId}/businessDate
        """
        import datetime
        endpoint = f"/bof/v1/hotels/{settings.opera_hotel_id}/businessDate"
        data = await self.client.fetch_one(endpoint)
        
        hotels = data.get("hotels", [])
        if not hotels:
            raise ValueError(f"No business date returned for hotel {settings.opera_hotel_id}")
            
        b_date_str = hotels[0].get("businessDate")
        if not b_date_str:
            raise ValueError(f"businessDate field missing in response: {data}")
            
        return datetime.date.fromisoformat(b_date_str)

    async def fetch_transaction_codes(self) -> dict:
        """Fetches transaction codes configuration.
        
        Endpoint: GET /csh/v1/hotels/{hotelId}/transactionCodes
        """
        endpoint = f"/csh/v1/hotels/{settings.opera_hotel_id}/transactionCodes"
        params = {"limit": _PAGE_SIZE, "offset": 0}
        all_codes = []
        
        while True:
            data = await self.client.fetch_one(endpoint, params=dict(params))
            codes = data.get("trxCodes") or data.get("transactionCodes") or []
            all_codes.extend(codes)
            
            if not data.get("hasMore") or not codes:
                break
            params["offset"] += len(codes)
            
        return {"transactionCodes": all_codes}
