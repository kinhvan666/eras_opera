# src/main.py
import asyncio
import sys
import traceback
from datetime import date, timedelta

from src.client import BaseOperaClient, OperaAuthError
from src.extractors.reservations import ReservationExtractor
from src.extractors.hotel_config import HotelConfigExtractor
from src.extractors.cashiering import CashieringExtractor, BACKFILL_START_DATE
from src.database import Database, DatabaseConnectionError
from src.config import settings


async def run(arrival_start_date: str, arrival_end_date: str):
    print("Starting data extraction process...")

    db = None
    try:
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

        db.insert_hotel_config_snapshot(settings.opera_hotel_id, hotel_config_data, physical_room_count)
        print("Hotel config snapshot inserted.")

        print("Fetching transaction codes...")
        transaction_codes_data = await hotel_extractor.fetch_transaction_codes()
        db.insert_transaction_codes_snapshot(settings.opera_hotel_id, transaction_codes_data)
        print("Transaction codes snapshot inserted.")

        extractor = ReservationExtractor(client)

        print(f"Fetching reservations with arrival {arrival_start_date}..{arrival_end_date}...")
        historical = await extractor.fetch_reservations(arrival_start_date, arrival_end_date)
        print(f"Fetched {len(historical)} historical reservations.")

        print("Fetching active/in-house reservations (InHouse, CheckedIn, DueIn, DueOut)...")
        active = await extractor.fetch_active_reservations()
        print(f"Fetched {len(active)} active reservations.")

        historical_ids = {r["confirmationId"] for r in historical if r.get("confirmationId")}
        active_unique = [r for r in active if r.get("confirmationId") not in historical_ids]

        reservations_data = historical + active_unique
        print(f"Total unique reservations to process: {len(reservations_data)}")

        if reservations_data:
            print("Inserting data into PostgreSQL (ON CONFLICT upsert)...")
            db.insert_raw_data(reservations_data)
            print("Data insertion complete.")

        # Cashiering postings: independent raw table (raw.cashiering_postings), run order does
        # not matter relative to reservations. Backfill from BACKFILL_START_DATE to today.
        cashiering_extractor = CashieringExtractor(client)
        
        business_date = await hotel_extractor.fetch_business_date()
        print(f"Fetched business date: {business_date.isoformat()}")
        
        yesterday = business_date - timedelta(days=1)
        print(f"Fetching cashiering postings from {BACKFILL_START_DATE.isoformat()} to {yesterday.isoformat()}...")
        postings = await cashiering_extractor.fetch_postings(BACKFILL_START_DATE, yesterday)
        print(f"Fetched {len(postings)} cashiering postings.")
        if postings:
            print("Upserting cashiering postings (ON CONFLICT on transaction_no)...")
            db.insert_cashiering_postings(postings)
            print("Cashiering postings insertion complete.")

    finally:
        if db:
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
