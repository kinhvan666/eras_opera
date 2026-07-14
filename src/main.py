# src/main.py
import asyncio
import sys
import traceback
from .client import BaseOperaClient, OperaAuthError
from .extractors.reservations import ReservationExtractor
from .database import Database, DatabaseConnectionError

async def main():
    print("Starting data extraction process...")

    try:
        # Initialize Database and setup schema/tables
        db = Database()
        print("Setting up database schema and tables...")
        db.setup()

        # Initialize API client and extractor
        opera_client = BaseOperaClient()
        reservation_extractor = ReservationExtractor(opera_client)

        # Fetch data
        print("Fetching recent reservations...")
        reservations_data = await reservation_extractor.fetch_recent_reservations()
        print(f"Fetched {len(reservations_data)} reservations.")

        # Insert data into database
        if reservations_data:
            print("Inserting data into PostgreSQL...")
            db.insert_raw_data(reservations_data)
            print("Data insertion complete.")

        # Clean up
        db.close()
        print("Extraction process finished.")

    except (OperaAuthError, DatabaseConnectionError) as e:
        print(f"A critical error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
