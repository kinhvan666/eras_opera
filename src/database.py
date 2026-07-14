import psycopg2
from src.config import settings

class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(settings.DATABASE_URL)
            self._create_table()
        except Exception as e:
            raise DatabaseConnectionError(f"Database connection failed: {e}")

    def _create_table(self):
        with self.conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, hotel_id TEXT, guest_name TEXT, room_number TEXT)")
        self.conn.commit()

    def save_reservations(self, reservations):
        with self.conn.cursor() as cur:
            for res in reservations:
                cur.execute("INSERT INTO reservations (id, hotel_id, guest_name, room_number) VALUES (%s, %s, %s, %s) ON CONFLICT(id) DO UPDATE SET hotel_id=EXCLUDED.hotel_id, guest_name=EXCLUDED.guest_name, room_number=EXCLUDED.room_number", 
        self.conn.commit()

    def close(self):
        self.conn.close()
