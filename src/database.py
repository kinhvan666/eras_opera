import sqlite3
from src.config import Config

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_URL.replace("sqlite:///", ""))
        self._create_table()

    def _create_table(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, hotel_id TEXT, guest_name TEXT, room_number TEXT)")
        self.conn.commit()

    def save_reservations(self, reservations):
        for res in reservations:
            self.conn.execute("INSERT OR REPLACE INTO reservations VALUES (?, ?, ?, ?)", 
                              (res.id, res.hotel_id, res.guest_name, res.room_number))
        self.conn.commit()