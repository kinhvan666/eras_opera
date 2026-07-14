# extractor/src/database.py
import psycopg2
import psycopg2.extras
import json
from .config import settings

class DatabaseConnectionError(Exception):
    """Custom exception for database connection errors."""
    pass

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(settings.database_url)
        except psycopg2.OperationalError as e:
            raise DatabaseConnectionError(f"Could not connect to database: {e}") from e

    def setup(self):
        """Creates the necessary schema and tables."""
        with self.conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS raw;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.booking_core_reservations (
                    id SERIAL PRIMARY KEY,
                    extracted_at TIMESTAMPTZ DEFAULT NOW(),
                    raw_data JSONB NOT NULL
                );
            """)
            self.conn.commit()

    def insert_raw_data(self, data: list[dict]):
        """Inserts a list of raw JSON objects into the database."""
        if not data:
            return

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "INSERT INTO raw.booking_core_reservations (raw_data) VALUES %s",
                [(json.dumps(item),) for item in data]
            )
            self.conn.commit()

    def close(self):
        self.conn.close()
