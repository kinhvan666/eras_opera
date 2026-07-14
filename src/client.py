import requests
from src.config import settings

class OperaAuthError(Exception):
    """Raised when authentication fails."""
    pass

class BaseOperaClient:
    def __init__(self):
        self.url = settings.opera_base_url
        self.key = settings.opera_client_secret
        self.token_url = settings.opera_token_url
        self.token = self._get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def _get_token(self):
        # Implementation for token retrieval
        response = requests.post(
            self.token_url,
            headers={"Authorization": f"Basic {self.key}"},
            data={"grant_type": "client_credentials"}
        )
        if response.status_code != 200:
            raise OperaAuthError(f"Failed to get token: {response.status_code} {response.text}")
        return response.json()["access_token"]

class APIClient(BaseOperaClient):
    def fetch_data(self, endpoint):
        response = requests.get(f"{self.url}/{endpoint}", headers=self.headers)
        response.raise_for_status()
        return response.json()