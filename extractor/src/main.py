# src/main.py
import asyncio
import sys
import traceback
from src.client import BaseOperaClient, OperaAuthError
from src.extractors.reservations import ReservationExtractor
from src.database import Database, DatabaseConnectionError

def main():
    print("Starting data extraction process...")

    try:
        # Initialize Database and setup schema/tables
        db = Database()
        print("Database initialized.")

        # Initialize API client and extractor
        reservation_extractor = ReservationExtractor()

        # Fetch data
        print("Fetching recent reservations...")
        reservations_data = reservation_extractor.extract()
        print(f"Fetched {len(reservations_data)} reservations.")

        # Insert data into database
        if reservations_data:
            print("Inserting data into PostgreSQL...")
            db.save_reservations(reservations_data)
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
    main()
