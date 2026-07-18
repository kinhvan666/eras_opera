# tests/test_main_wiring.py
# AC6: run() invokes both HotelConfigExtractor and ReservationExtractor
#      (historical arrival-range fetch + active InHouse fetch)
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import run

_START = "2026-04-17"
_END = "2026-07-16"

_HOTEL_DATA = {"hotelConfigInfo": {"hotelName": "Test Hotel"}}
_ROOM_COUNT = 49

_HISTORICAL = [{"reservationIdList": [{"id": "R001"}]}]
_ACTIVE = [{"reservationIdList": [{"id": "R002"}]}]


@pytest.fixture
def patched_run():
    """Patches all external dependencies in main.run() and returns the mocks."""
    with (
        patch("src.main.Database") as MockDB,
        patch("src.main.BaseOperaClient") as MockClient,
        patch("src.main.HotelConfigExtractor") as MockHotel,
        patch("src.main.ReservationExtractor") as MockResv,
        patch("src.main.CashieringExtractor") as MockCash,
    ):
        mock_db = MagicMock()
        MockDB.return_value = mock_db

        MockClient.return_value = MagicMock()

        mock_hotel = MagicMock()
        mock_hotel.fetch_hotel_config = AsyncMock(return_value=_HOTEL_DATA)
        mock_hotel.fetch_physical_room_count = AsyncMock(return_value=_ROOM_COUNT)
        MockHotel.return_value = mock_hotel

        mock_resv = MagicMock()
        mock_resv.fetch_reservations = AsyncMock(return_value=_HISTORICAL)
        mock_resv.fetch_active_reservations = AsyncMock(return_value=_ACTIVE)
        MockResv.return_value = mock_resv

        mock_cash = MagicMock()
        mock_cash.fetch_postings = AsyncMock(return_value=[])
        MockCash.return_value = mock_cash

        yield {"db": mock_db, "hotel": mock_hotel, "resv": mock_resv, "cash": mock_cash}


@pytest.mark.asyncio
async def test_run_invokes_hotel_config_extractor(patched_run):
    """AC6: run() calls fetch_hotel_config() and fetch_physical_room_count() and inserts snapshot."""
    await run(_START, _END)

    patched_run["hotel"].fetch_hotel_config.assert_called_once()
    patched_run["hotel"].fetch_physical_room_count.assert_called_once()
    patched_run["db"].insert_hotel_config_snapshot.assert_called_once()


@pytest.mark.asyncio
async def test_run_fetches_both_historical_and_active_reservations(patched_run):
    """AC6: run() calls fetch_reservations (historical) AND fetch_active_reservations (InHouse)."""
    await run(_START, _END)

    patched_run["resv"].fetch_reservations.assert_called_once_with(_START, _END)
    patched_run["resv"].fetch_active_reservations.assert_called_once()


@pytest.mark.asyncio
async def test_run_merges_and_inserts_all_reservations(patched_run):
    """AC6: historical + active results are merged before insert_raw_data is called."""
    await run(_START, _END)

    patched_run["db"].insert_raw_data.assert_called_once_with(_HISTORICAL + _ACTIVE)


@pytest.mark.asyncio
async def test_run_invokes_cashiering_extractor(patched_run):
    """run() calls CashieringExtractor.fetch_postings (backfill from BACKFILL_START_DATE)."""
    await run(_START, _END)

    patched_run["cash"].fetch_postings.assert_called_once()


@pytest.mark.asyncio
async def test_run_skips_cashiering_insert_when_no_postings(patched_run):
    """run() does NOT call insert_cashiering_postings when fetch returns []."""
    await run(_START, _END)

    patched_run["db"].insert_cashiering_postings.assert_not_called()
