# extractor/src/client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, List, Dict, Any

from .config import settings

class OperaAuthError(Exception):
    """Custom exception for authentication errors."""
    pass

class BaseOperaClient:
    def __init__(self):
        self._session = httpx.AsyncClient(base_url=settings.opera_base_url)
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Fetches an OAuth token from OPERA Cloud."""
        if self._token:
            # In a real scenario, you'd check for token expiry.
            # For this phase, we fetch it once.
            return self._token

        auth_data = {
            "grant_type": "client_credentials",
            "client_id": settings.opera_client_id,
            "client_secret": settings.opera_client_secret,
        }
        headers = {"x-app-key": settings.opera_app_key}

        try:
            response = await self._session.post(settings.opera_token_url, data=auth_data, headers=headers)
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token
        except httpx.HTTPStatusError as e:
            raise OperaAuthError(f"Failed to get token: {e.response.status_code} {e.response.text}") from e


    async def _set_auth_headers(self):
        token = await self._get_token()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "x-app-key": settings.opera_app_key,
            "x-hotelid": settings.opera_hotel_id,
            "Content-Type": "application/json",
        })

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_all(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[Any, Any]]:
        """Fetches all pages from a given paginated endpoint."""
        if not self._token:
            await self._set_auth_headers()

        all_results = []

        response = await self._session.get(endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        # The structure of the response payload needs to be confirmed from API docs.
        # This is a common pattern.
        items_key = next((key for key in data if isinstance(data.get(key), list)), None)
        if items_key:
            all_results.extend(data[items_key])

        # Pagination logic based on 'next' link in headers, a common REST pattern.
        # This may need adjustment based on OPERA Cloud's specific pagination implementation.
        while 'next' in response.links:
            next_url = response.links['next']['url']
            response = await self._session.get(next_url)
            response.raise_for_status()
            data = response.json()
            if items_key:
                all_results.extend(data[items_key])

        return all_results
