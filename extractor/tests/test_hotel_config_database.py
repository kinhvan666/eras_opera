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


def test_upsert_hotel_config_executes_insert_on_conflict_sql(db):
    """AC2: upsert_hotel_config runs INSERT...ON CONFLICT DO UPDATE, not a bare INSERT."""
    db.upsert_hotel_config(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)

    sql = db._mock_cursor.execute.call_args[0][0]
    assert "INSERT INTO raw.enterprise_hotel_config" in sql
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql


def test_upsert_hotel_config_passes_correct_params(db):
    """AC2: hotel_id, raw JSON, and room_count are bound as parameters in the right order."""
    db.upsert_hotel_config(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)

    params = db._mock_cursor.execute.call_args[0][1]
    assert params[0] == _HOTEL_ID
    assert json.loads(params[1]) == _HOTEL_DATA
    assert params[2] == _ROOM_COUNT


def test_upsert_hotel_config_commits_after_insert(db):
    """AC2: connection is committed so the row is persisted."""
    db.upsert_hotel_config(_HOTEL_ID, _HOTEL_DATA, _ROOM_COUNT)
    db.conn.commit.assert_called_once()


def test_upsert_hotel_config_accepts_none_room_count(db):
    """AC5: None room_count is passed as NULL — does not raise, does not silently zero-out."""
    db.upsert_hotel_config(_HOTEL_ID, _HOTEL_DATA, None)

    params = db._mock_cursor.execute.call_args[0][1]
    assert params[2] is None
    db.conn.commit.assert_called_once()
