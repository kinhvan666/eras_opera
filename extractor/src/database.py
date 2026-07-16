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
            # Unique constraint on reservation_id (extracted from JSONB) so that
            # re-runs and pagination retries are idempotent — no duplicate rows.
            # Uses a generated column expression index (functional unique index).
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_core_reservation_id
                ON raw.booking_core_reservations
                ((raw_data->'reservationIdList'->0->>'id'))
                WHERE raw_data->'reservationIdList'->0->>'id' IS NOT NULL;
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.enterprise_hotel_config (
                    id SERIAL PRIMARY KEY,
                    hotel_id TEXT NOT NULL,
                    extracted_at TIMESTAMPTZ DEFAULT NOW(),
                    raw_data JSONB NOT NULL,
                    physical_room_count INTEGER
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_enterprise_hotel_config_hotel_id
                ON raw.enterprise_hotel_config (hotel_id);
            """)
            # Add physical_room_count column to existing tables created before this field existed.
            cur.execute("""
                ALTER TABLE raw.enterprise_hotel_config
                ADD COLUMN IF NOT EXISTS physical_room_count INTEGER;
            """)
            self.conn.commit()

    def insert_raw_data(self, data: list[dict]):
        """Upserts a list of raw JSON objects into the database.

        Uses INSERT ... ON CONFLICT DO UPDATE so that:
        - Re-running the extractor for the same date range is safe (no duplicates).
        - If a reservation's data changed in OPERA (e.g. status update), the latest
          raw_data and extracted_at are stored.
        """
        if not data:
            return

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO raw.booking_core_reservations (raw_data)
                VALUES %s
                ON CONFLICT ((raw_data->'reservationIdList'->0->>'id'))
                WHERE raw_data->'reservationIdList'->0->>'id' IS NOT NULL
                DO UPDATE SET
                    raw_data     = EXCLUDED.raw_data,
                    extracted_at = NOW()
                """,
                [(json.dumps(item),) for item in data]
            )
            self.conn.commit()

    def upsert_hotel_config(self, hotel_id: str, data: dict, physical_room_count: int | None = None):
        """Upserts hotel config — one row per hotel_id, always keeps the latest."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.enterprise_hotel_config (hotel_id, raw_data, physical_room_count)
                VALUES (%s, %s, %s)
                ON CONFLICT (hotel_id) DO UPDATE SET
                    raw_data             = EXCLUDED.raw_data,
                    physical_room_count  = EXCLUDED.physical_room_count,
                    extracted_at         = NOW()
                """,
                (hotel_id, json.dumps(data), physical_room_count)
            )
            self.conn.commit()

    def close(self):
        self.conn.close()
