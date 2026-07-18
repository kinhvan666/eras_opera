# tests/test_cashiering_database.py
# AC-1: transaction_no is the dedup key — re-inserting the same transaction_no upserts
#       (no duplicate row) and updated raw_data overwrites the prior row.
import json

import pytest
from unittest.mock import MagicMock

from src.database import Database


def _row(tno, code="1000", amount=100.0, rev_date="2026-01-15", extra=None):
    raw = {"transactionNo": tno, "transactionCode": code, "note": extra}
    return {
        "transaction_no": tno,
        "hotel_id": "TEST",
        "revenue_date": rev_date,
        "transaction_code": code,
        "posted_amount": amount,
        "raw_data": raw,
    }


@pytest.fixture
def db(monkeypatch):
    """Database with mocked psycopg2 connection and a captured execute_values."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    monkeypatch.setattr("psycopg2.connect", lambda *a, **kw: mock_conn)

    # execute_values would try to mogrify against the mock cursor — capture instead.
    captured = MagicMock()
    monkeypatch.setattr("psycopg2.extras.execute_values", captured)

    instance = Database()
    instance._mock_cursor = mock_cursor
    instance._execute_values = captured
    return instance


def test_insert_creates_table_inside_method(db):
    """E6: CREATE TABLE IF NOT EXISTS raw.cashiering_postings runs inside the method."""
    db.insert_cashiering_postings([_row(1)])

    executed_sql = " ".join(call[0][0] for call in db._mock_cursor.execute.call_args_list)
    assert "CREATE TABLE IF NOT EXISTS raw.cashiering_postings" in executed_sql


def test_insert_uses_on_conflict_transaction_no(db):
    """AC-1: upsert keyed on transaction_no guarantees no duplicate rows on re-run."""
    db.insert_cashiering_postings([_row(1)])

    sql = db._execute_values.call_args[0][1]
    assert "ON CONFLICT (transaction_no) DO UPDATE" in sql
    assert "raw_data" in sql and "EXCLUDED.raw_data" in sql


def test_reinsert_same_transaction_no_updates_raw_data(db):
    """AC-1: re-inserting the same transaction_no passes updated raw_data (overwrite, not append)."""
    db.insert_cashiering_postings([_row(1, extra="first")])
    db.insert_cashiering_postings([_row(1, extra="second")])

    # both calls target the same upsert; second call carries the updated raw_data
    second_values = db._execute_values.call_args_list[1][0][2]
    assert len(second_values) == 1
    txn_no, _hotel, _rev, _code, _amt, raw_json = second_values[0]
    assert txn_no == 1
    assert json.loads(raw_json)["note"] == "second"


def test_insert_empty_list_is_noop(db):
    """Empty input does not touch the DB."""
    db.insert_cashiering_postings([])

    db._execute_values.assert_not_called()
    db._mock_cursor.execute.assert_not_called()


def test_insert_commits(db):
    """The upsert is committed so rows persist."""
    db.insert_cashiering_postings([_row(1)])

    db.conn.commit.assert_called_once()
