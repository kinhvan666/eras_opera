# tests/test_hotel_config_extractor.py
# AC1: real room count retrievable from OPERA per property
import pytest
import respx
from httpx import Response

from src.client import BaseOperaClient
from src.config import settings
from src.extractors.hotel_config import HotelConfigExtractor, _PAGE_SIZE

_TOKEN_RESP = {"access_token": "test-token"}

_HOTEL_CONFIG_RESP = {
    "hotelConfigInfo": {
        "hotelName": "Test Hotel",
        "generalInformation": {"roomCount": None},
    }
}

_HOTEL_ID = settings.opera_hotel_id
_TOKEN_URL = settings.opera_token_url
_BASE = settings.opera_base_url

_ENT_CONFIG_URL = f"{_BASE}/ent/config/v1/hotels/{_HOTEL_ID}"
_ROOMS_URL = f"{_BASE}/rm/config/v1/hotels/{_HOTEL_ID}/rooms"


def _rooms_page(room_ids: list[str]) -> dict:
    return {"rooms": [{"hotelId": _HOTEL_ID, "room": [{"roomId": r} for r in room_ids]}]}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_hotel_config_returns_json_body():
    """fetch_hotel_config() calls /ent/config/v1/hotels/{hotelId} and returns the JSON body."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    respx.get(_ENT_CONFIG_URL).mock(return_value=Response(200, json=_HOTEL_CONFIG_RESP))

    result = await HotelConfigExtractor(BaseOperaClient()).fetch_hotel_config()

    assert result == _HOTEL_CONFIG_RESP


@pytest.mark.asyncio
@respx.mock
async def test_fetch_physical_room_count_sums_inner_room_arrays():
    """Room count = sum of items in inner room[] sub-arrays, not the count of top-level groups.

    Response shape: { "rooms": [{ "room": [...individual rooms...] }] }
    Regression guard against the bug that returned 1 (group count) instead of 3 (room count).
    """
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    respx.get(_ROOMS_URL).mock(return_value=Response(200, json=_rooms_page(["101", "102", "103"])))

    count = await HotelConfigExtractor(BaseOperaClient()).fetch_physical_room_count()

    assert count == 3


@pytest.mark.asyncio
@respx.mock
async def test_fetch_physical_room_count_paginates_until_partial_page():
    """Pagination stops when a page returns fewer rooms than PAGE_SIZE; total spans all pages."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))

    full_page = _rooms_page([str(i) for i in range(_PAGE_SIZE)])
    last_page = _rooms_page(["last1", "last2"])

    pages = iter([full_page, last_page])
    respx.get(_ROOMS_URL).mock(side_effect=lambda req: Response(200, json=next(pages)))

    count = await HotelConfigExtractor(BaseOperaClient()).fetch_physical_room_count()

    assert count == _PAGE_SIZE + 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_physical_room_count_empty_rooms_returns_zero():
    """Empty rooms array from API yields count = 0 without raising."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    respx.get(_ROOMS_URL).mock(return_value=Response(200, json={"rooms": []}))

    count = await HotelConfigExtractor(BaseOperaClient()).fetch_physical_room_count()

    assert count == 0
