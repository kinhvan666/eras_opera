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
            # Append-only snapshot table: every extraction run inserts a new row so
            # history is preserved (SPEC AC2). Drop the legacy unique index on hotel_id
            # so plain INSERTs no longer collide; this is idempotent on re-run.
            cur.execute("DROP INDEX IF EXISTS raw.uq_enterprise_hotel_config_hotel_id;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw.enterprise_hotel_config (
                    id SERIAL PRIMARY KEY,
                    hotel_id TEXT NOT NULL,
                    extracted_at TIMESTAMPTZ DEFAULT NOW(),
                    raw_data JSONB NOT NULL,
                    physical_room_count INTEGER
                );
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

    def insert_hotel_config_snapshot(self, hotel_id: str, data: dict, physical_room_count: int | None = None):
        """Appends a new hotel config snapshot — one row per extraction run (SPEC AC2).

        Plain INSERT with no ON CONFLICT clause: history is never overwritten, so
        stg_hotel_config dedups to the latest snapshot per hotel via extracted_at.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw.enterprise_hotel_config (hotel_id, raw_data, physical_room_count, extracted_at)
                VALUES (%s, %s, %s, NOW())
                """,
                (hotel_id, json.dumps(data), physical_room_count)
            )
            self.conn.commit()

    def close(self):
        self.conn.close()
