import psycopg2
import json
import traceback

def query():
    print("Connecting to postgresql://user:password@localhost:5432/erg_opera_data")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="erg_opera_data",
            user="user",
            password="password"
        )
        cur = conn.cursor()
        
        print("Checking tables...")
        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('raw', 'public')
        """)
        tables = cur.fetchall()
        print(f"Found tables: {tables}")
        
        if ('raw', 'booking_core_reservations') in tables:
            print("\nQuerying raw.booking_core_reservations...")
            cur.execute("SELECT id, extracted_at, raw_data FROM raw.booking_core_reservations LIMIT 2;")
            rows = cur.fetchall()
            print(f"Got {len(rows)} rows.")
            for row in rows:
                id, extracted_at, raw_data = row
                print(f"\nID: {id}, Extracted at: {extracted_at}")
                print("Raw data sample (truncated):")
                json_str = json.dumps(raw_data, indent=2)
                if len(json_str) > 1000:
                    print(json_str[:1000] + "\n...[truncated]")
                else:
                    print(json_str)
        else:
            print("\nTable raw.booking_core_reservations not found!")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting/querying: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    query()
