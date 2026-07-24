"""Quick check: fetch transaction codes from OPERA API."""
import asyncio
from src.config import settings
from src.client import BaseOperaClient

async def main():
    c = BaseOperaClient()
    try:
        data = await c.fetch_one('/fof/config/v1/transactionCodes')
        codes = data.get('transactionCodes', data.get('trxCodes', data.get('hotelTransactionCodes', [])))
        if isinstance(codes, list):
            print(f'Found {len(codes)} transaction codes')
            if codes:
                print(f'Sample: {codes[0]}')
        else:
            print(f'Response keys: {list(data.keys())}')
            print(f'Response preview: {str(data)[:500]}')
    except Exception as e:
        print(f'ERROR: {e}')

asyncio.run(main())
