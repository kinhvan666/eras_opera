# tests/test_hotel_config_database.py
# AC2: hotel config upserted correctly per extraction run
# AC5: None/missing room count does not corrupt existing data
import json
import pytest
from unittest.mock import MagicMock

from src.database import Database

_HOTEL_ID = "TEST"
_HOTEL_DATA = {"hotelConfigInfo": {"hotelName": "Test Hotel"}}
_ROOM_COUNT = 49


@pytest.fixture
def db(monkeypatch):
    """Database with mocked psycopg2 connection — no real Postgres needed."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Context-manager protocol for `with self.conn.cursor() as cur:`
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    monkeypatch.setattr("psycopg2.connect", lambda *a, **kw: mock_conn)

    instance = Database()
    instance._mock_cursor = mock_cursor
    return instance


def test_insert_hotel_config_snapshot_uses_plain_insert(db):
    """AC2: insert_hotel_config_snapshot runs a plain append INSERT with no ON CONFLICT clause."""
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)

    sql = db._mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO raw.enterprise_hotel_config" in sql
    assert "ON CONFLICT" not in sql


def test_insert_hotel_config_snapshot_appends_new_row(db):
    """AC2: two calls issue two independent append INSERTs (no upsert/overwrite)."""
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, 49)
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, 52)

    assert db._mock_cursor.execute.call_count == 2
    for call in db._mock_cursor.execute.call_args_list:
        assert "ON CONFLICT" not in call[0][0]


def test_insert_hotel_config_snapshot_passes_correct_params(db):
    """AC2: hotel_id, raw JSON, and room_count are bound as parameters in the right order."""
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)

    params = db._mock_cursor.execute.call_args[0][1]
    assert params[0] == _HOTEL_ID
    assert json.loads(params[1]) == _HOTEL_DATA
    assert params[2] == _ROOM_COUNT


def test_insert_hotel_config_snapshot_commits_after_insert(db):
    """AC2: connection is committed so the row is persisted."""
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)
    db.conn.commit.assert_called_once()


def test_insert_hotel_config_snapshot_accepts_none_room_count(db):
    """AC5: None room_count is passed as NULL — does not raise, does not silently zero-out."""
    db.insert_hotel_config_snapshot(_HOTEL_ID, _HOTEL_DATA, None)

    params = db._mock_cursor.execute.call_args[0][1]
    assert params[2] is None
    db.conn.commit.assert_called_once()


def test_insert_transaction_codes_snapshot(db):
    """Test inserting transaction codes snapshot."""
    db.insert_transaction_codes_snapshot(_HOTEL_ID, {"transactionCodes": []})
    
    sql = db._mock_cursor.execute.call_args[0][0]
    params = db._mock_cursor.execute.call_args[0][1]
    
    assert "INSERT INTO raw.transaction_codes" in sql
    assert params[0] == _HOTEL_ID
    assert json.loads(params[1]) == {"transactionCodes": []}
    db.conn.commit.assert_called_once()
