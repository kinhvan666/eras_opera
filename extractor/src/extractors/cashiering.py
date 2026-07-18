# extractor/src/extractors/cashiering.py
from datetime import date, timedelta
from typing import List

from ..client import BaseOperaClient
from ..config import settings

# Max records per page for /financialPostings per OPERA spec (maximum: 4000).
_PAGE_LIMIT = 4000

# Default backfill start for cashiering postings. Named constant — never hardcode the
# literal at the call site (validate-contract E3).
BACKFILL_START_DATE = date(2026, 1, 1)


def generate_date_windows(start: date, end: date, window_days: int = 30) -> List[tuple[date, date]]:
    """Split [start, end] into consecutive, non-overlapping, inclusive windows.

    Each window spans at most ``window_days`` calendar days (inclusive of both ends).
    The final window is truncated to ``end`` when the range is not an exact multiple.
    The window count is computed from date arithmetic — never hardcoded.

    The OPERA /financialPostings API allows a maximum 30-day time span per request,
    so ``window_days`` defaults to 30.

    Raises:
        ValueError: if ``window_days`` < 1, or if ``start`` > ``end``.
    """
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    if start > end:
        raise ValueError("start must be <= end")

    windows: List[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=window_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows


class CashieringExtractor:
    """Extracts raw financial postings from OPERA Cloud /financialPostings.

    Stores ALL transaction types (Revenue, Payment, Wrapper) raw — no extraction-time
    filter. The dbt staging model (Phase 2) applies the Revenue-only filter.
    """

    def __init__(self, client: BaseOperaClient):
        self.client = client

    async def fetch_postings(self, start_date: date, end_date: date) -> List[dict]:
        """Fetch all postings in [start_date, end_date], chunked into <=30-day windows.

        Pagination per window (validate-contract E4/E5):
        - PRIMARY stop condition: ``hasMore == False`` in the response.
        - SECONDARY safety fallback: ``len(page_results) < limit`` (mirrors the
          hotel_config safety pattern; guards against a truthy hasMore + short page).

        Returns a list of row dicts (extracted top-level columns + full ``raw_data``).
        """
        endpoint = f"/csh/v1/hotels/{settings.opera_hotel_id}/financialPostings"
        all_rows: List[dict] = []

        for window_start, window_end in generate_date_windows(start_date, end_date):
            offset = 0
            while True:
                params = {
                    "startDate": window_start.isoformat(),
                    "endDate": window_end.isoformat(),
                    "limit": _PAGE_LIMIT,
                    "offset": offset,
                }
                response = await self.client.fetch_one(endpoint, params=params)

                page_results = (response.get("journalPostings") or {}).get("postings") or []
                for posting in page_results:
                    all_rows.append(self._to_row(posting))

                has_more = response.get("hasMore", False)
                # PRIMARY: hasMore False stops. SECONDARY: short page stops (safety fallback).
                if not has_more or len(page_results) < _PAGE_LIMIT:
                    break
                offset += len(page_results)

        return all_rows

    @staticmethod
    def _to_row(posting: dict) -> dict:
        """Extract indexed columns from a posting; keep the full posting as raw_data."""
        posted_amount = posting.get("postedAmount") or {}
        return {
            "transaction_no": posting.get("transactionNo"),
            "hotel_id": settings.opera_hotel_id,
            "revenue_date": posting.get("revenueDate"),
            "transaction_code": posting.get("transactionCode"),
            "posted_amount": posted_amount.get("amount"),
            "raw_data": posting,
        }
