# tests/test_cashiering_extractor.py
# AC-9: date-window chunking (pure) + pagination (hasMore primary, len<limit fallback)
# AC-10: multi-page fetch within a single window
# AC-9-alltype: all transaction types stored raw (no extraction-time filter)
from datetime import date

import pytest
import respx
from httpx import Response

from src.client import BaseOperaClient
from src.config import settings
from src.extractors.cashiering import (
    CashieringExtractor,
    generate_date_windows,
    _PAGE_LIMIT,
    BACKFILL_START_DATE,
)

_TOKEN_RESP = {"access_token": "test-token"}
_HOTEL_ID = settings.opera_hotel_id
_TOKEN_URL = settings.opera_token_url
_BASE = settings.opera_base_url
_POSTINGS_URL = f"{_BASE}/csh/v1/hotels/{_HOTEL_ID}/financialPostings"


# ----------------------------------------------------------------------------
# generate_date_windows — pure function (AC-9-windows)
# ----------------------------------------------------------------------------

def test_windows_exact_multiple_of_window_days():
    """60-day range at window_days=30 → two full 30-day windows, non-overlapping."""
    windows = generate_date_windows(date(2026, 1, 1), date(2026, 3, 1), window_days=30)
    assert windows == [
        (date(2026, 1, 1), date(2026, 1, 30)),
        (date(2026, 1, 31), date(2026, 3, 1)),
    ]


def test_windows_partial_final_window():
    """Non-multiple range: final window is truncated to end (no overshoot)."""
    windows = generate_date_windows(date(2026, 1, 1), date(2026, 2, 14), window_days=30)
    assert windows == [
        (date(2026, 1, 1), date(2026, 1, 30)),
        (date(2026, 1, 31), date(2026, 2, 14)),
    ]
    # last window end never exceeds the requested end
    assert windows[-1][1] == date(2026, 2, 14)


def test_windows_single_day_range():
    """A range shorter than one window yields exactly one window."""
    windows = generate_date_windows(date(2026, 1, 1), date(2026, 1, 10), window_days=30)
    assert windows == [(date(2026, 1, 1), date(2026, 1, 10))]


def test_windows_start_equals_end():
    """start == end yields a single one-day window."""
    windows = generate_date_windows(date(2026, 1, 1), date(2026, 1, 1), window_days=30)
    assert windows == [(date(2026, 1, 1), date(2026, 1, 1))]


def test_windows_start_after_end_raises():
    """start > end raises ValueError."""
    with pytest.raises(ValueError):
        generate_date_windows(date(2026, 2, 1), date(2026, 1, 1), window_days=30)


def test_windows_real_backfill_range_no_gaps_or_overlaps():
    """Real backfill range (2026-01-01 to today): windows are contiguous, non-overlapping,
    fully cover the range, and never exceed 30 days each."""
    end = date(2026, 7, 18)
    windows = generate_date_windows(BACKFILL_START_DATE, end, window_days=30)

    assert windows[0][0] == BACKFILL_START_DATE
    assert windows[-1][1] == end
    for start, stop in windows:
        assert start <= stop
        assert (stop - start).days <= 29  # 30 days inclusive => max 29-day delta
    # each window starts the day after the previous window ends (contiguous, no gap/overlap)
    for prev, nxt in zip(windows, windows[1:]):
        assert (nxt[0] - prev[1]).days == 1


# ----------------------------------------------------------------------------
# fixtures for extraction tests
# ----------------------------------------------------------------------------

def _posting(tno, ttype="Revenue", code="1000", amount=100.0, rev_date="2026-01-15"):
    return {
        "transactionNo": tno,
        "transactionType": ttype,
        "transactionCode": code,
        "postedAmount": {"amount": amount, "currencyCode": "USD"},
        "revenueDate": rev_date,
    }


def _page(postings, has_more):
    return {"journalPostings": {"postings": postings}, "hasMore": has_more}


# ----------------------------------------------------------------------------
# pagination (AC-9-pagination)
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_pagination_stops_on_hasmore_false_primary():
    """PRIMARY stop: hasMore=False ends fetch after one page even if the page is full."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    full_page = _page([_posting(i) for i in range(_PAGE_LIMIT)], has_more=False)
    route = respx.get(_POSTINGS_URL).mock(return_value=Response(200, json=full_page))

    rows = await CashieringExtractor(BaseOperaClient()).fetch_postings(
        date(2026, 1, 1), date(2026, 1, 10)
    )

    assert route.call_count == 1  # stopped after one fetch (hasMore=False)
    assert len(rows) == _PAGE_LIMIT


@pytest.mark.asyncio
@respx.mock
async def test_pagination_continues_on_short_page_until_empty():
    """A short page with hasMore=True does NOT stop the loop; only an empty page (or
    hasMore=False) ends it. Guards against silently dropping pages when the API returns a
    partial page but signals more data remains."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    short_page = _page([_posting(1), _posting(2), _posting(3)], has_more=True)
    empty_page = _page([], has_more=True)
    pages = iter([short_page, empty_page])
    route = respx.get(_POSTINGS_URL).mock(
        side_effect=lambda req: Response(200, json=next(pages))
    )

    rows = await CashieringExtractor(BaseOperaClient()).fetch_postings(
        date(2026, 1, 1), date(2026, 1, 10)
    )

    assert route.call_count == 2  # short page kept going; empty page stopped the loop
    assert len(rows) == 3


# ----------------------------------------------------------------------------
# multi-page within a window (AC-10-multipage)
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_multipage_within_single_window():
    """page1 hasMore=True + _PAGE_LIMIT rows, page2 hasMore=False + partial → total = _PAGE_LIMIT + partial."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))

    page1 = _page([_posting(i) for i in range(_PAGE_LIMIT)], has_more=True)
    page2 = _page([_posting(1000 + i) for i in range(7)], has_more=False)
    pages = iter([page1, page2])
    respx.get(_POSTINGS_URL).mock(side_effect=lambda req: Response(200, json=next(pages)))

    rows = await CashieringExtractor(BaseOperaClient()).fetch_postings(
        date(2026, 1, 1), date(2026, 1, 10)
    )

    assert len(rows) == _PAGE_LIMIT + 7


# ----------------------------------------------------------------------------
# all transaction types stored raw (AC-9-alltype)
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
@respx.mock
async def test_all_transaction_types_stored_raw():
    """Revenue, Payment, and Wrapper postings are all stored — no extraction-time filter."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    page = _page(
        [
            _posting(1, ttype="Revenue"),
            _posting(2, ttype="Payment"),
            _posting(3, ttype="Wrapper"),
        ],
        has_more=False,
    )
    respx.get(_POSTINGS_URL).mock(return_value=Response(200, json=page))

    rows = await CashieringExtractor(BaseOperaClient()).fetch_postings(
        date(2026, 1, 1), date(2026, 1, 10)
    )

    assert len(rows) == 3
    stored_types = {r["raw_data"]["transactionType"] for r in rows}
    assert stored_types == {"Revenue", "Payment", "Wrapper"}


@pytest.mark.asyncio
@respx.mock
async def test_row_extracts_indexed_columns():
    """Top-level indexed columns are parsed from the posting; postedAmount.amount is unwrapped."""
    respx.post(_TOKEN_URL).mock(return_value=Response(200, json=_TOKEN_RESP))
    page = _page(
        [_posting(42, code="9500", amount=250.75, rev_date="2026-02-03")], has_more=False
    )
    respx.get(_POSTINGS_URL).mock(return_value=Response(200, json=page))

    rows = await CashieringExtractor(BaseOperaClient()).fetch_postings(
        date(2026, 1, 1), date(2026, 1, 10)
    )

    row = rows[0]
    assert row["transaction_no"] == 42
    assert row["hotel_id"] == _HOTEL_ID
    assert row["revenue_date"] == "2026-02-03"
    assert row["transaction_code"] == "9500"
    assert row["posted_amount"] == 250.75
    assert row["raw_data"]["transactionNo"] == 42
