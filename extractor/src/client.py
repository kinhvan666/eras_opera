# extractor/src/client.py
import base64

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

        # Per docs/oAuth API for OHIP spec: client_id:client_secret goes in a Basic auth header,
        # not the form body — the form body only carries grant_type/scope (or username/password).
        basic = base64.b64encode(
            f"{settings.opera_client_id}:{settings.opera_client_secret}".encode()
        ).decode()
        auth_data = {"grant_type": "client_credentials"}
        if settings.opera_scope:
            auth_data["scope"] = settings.opera_scope
        headers = {
            "Authorization": f"Basic {basic}",
            "x-app-key": settings.opera_app_key,
        }
        if settings.opera_enterprise_id:
            headers["enterpriseId"] = settings.opera_enterprise_id

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
    async def _fetch_page(self, endpoint: str, params: Dict) -> Dict:
        """Fetch a single page with retry. Isolated so retry does NOT restart
        the pagination loop and re-fetch already-collected pages."""
        response = await self._session.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def fetch_one(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Fetch a single non-paginated resource (e.g. hotel config)."""
        if not self._token:
            await self._set_auth_headers()
        response = await self._session.get(endpoint, params=params or {})
        response.raise_for_status()
        return response.json()

    async def fetch_all(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[Any, Any]]:
        """Fetches all pages of `reservations.reservationInfo` using offset/limit/hasMore pagination
        (per the reservationsDetails response schema in the OPERA Reservation API spec).

        @retry is intentionally NOT on this method — it wraps _fetch_page instead so that a
        transient failure on page N retries only that page, not the whole collection from offset 0
        (which was the previous bug causing duplicate rows in raw.booking_core_reservations).
        """
        if not self._token:
            await self._set_auth_headers()

        all_results = []
        params = dict(params or {})
        offset = params.get("offset", 0)

        while True:
            params["offset"] = offset
            data = await self._fetch_page(endpoint, params)

            reservations = data.get("reservations", {})
            page_items = reservations.get("reservationInfo", [])
            all_results.extend(page_items)

            if not reservations.get("hasMore") or not page_items:
                break
            offset += len(page_items)

        return all_results
