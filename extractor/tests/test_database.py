# tests/test_database.py
import pytest
import psycopg2
from src.database import Database, DatabaseConnectionError

def test_database_connection_failure(monkeypatch):
    """
    Tests that the Database class raises DatabaseConnectionError on a connection failure.
    """
    # Mock psycopg2.connect to raise an OperationalError
    def mock_connect(*args, **kwargs):
        raise psycopg2.OperationalError("Mock connection error")

    monkeypatch.setattr(psycopg2, "connect", mock_connect)

    with pytest.raises(DatabaseConnectionError, match="Could not connect to database"):
        Database()