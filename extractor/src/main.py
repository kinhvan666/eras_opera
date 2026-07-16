# src/main.py
import asyncio
import sys
import traceback
from datetime import date, timedelta

from src.client import BaseOperaClient, OperaAuthError
from src.extractors.reservations import ReservationExtractor
from src.extractors.hotel_config import HotelConfigExtractor
from src.database import Database, DatabaseConnectionError
from src.config import settings


async def run(arrival_start_date: str, arrival_end_date: str):
    print("Starting data extraction process...")

    db = Database()
    print("Database initialized.")
    db.setup()

    client = BaseOperaClient()

    hotel_extractor = HotelConfigExtractor(client)

    print(f"Fetching hotel config for hotel {settings.opera_hotel_id}...")
    hotel_config_data = await hotel_extractor.fetch_hotel_config()

    print("Counting physical rooms...")
    physical_room_count = await hotel_extractor.fetch_physical_room_count()
    print(f"Physical room count: {physical_room_count}")

    db.upsert_hotel_config(settings.opera_hotel_id, hotel_config_data, physical_room_count)
    print("Hotel config upserted.")

    extractor = ReservationExtractor(client)

    print(f"Fetching reservations with arrival {arrival_start_date}..{arrival_end_date}...")
    historical = await extractor.fetch_reservations(arrival_start_date, arrival_end_date)
    print(f"Fetched {len(historical)} historical reservations.")

    print("Fetching active/in-house reservations (InHouse, CheckedIn, DueIn, DueOut)...")
    active = await extractor.fetch_active_reservations()
    print(f"Fetched {len(active)} active reservations.")

    reservations_data = historical + active
    print(f"Total before dedup: {len(reservations_data)} reservations.")

    if reservations_data:
        print("Inserting data into PostgreSQL (ON CONFLICT upsert)...")
        db.insert_raw_data(reservations_data)
        print("Data insertion complete.")

    db.close()
    print("Extraction process finished.")


def main():
    # Default range: last 90 days of arrivals; override via CLI args (start end, YYYY-MM-DD).
    end = date.today()
    start = end - timedelta(days=90)
    if len(sys.argv) == 3:
        start, end = date.fromisoformat(sys.argv[1]), date.fromisoformat(sys.argv[2])

    try:
        asyncio.run(run(start.isoformat(), end.isoformat()))
    except (OperaAuthError, DatabaseConnectionError) as e:
        print(f"A critical error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
