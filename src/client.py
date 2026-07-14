import requests
from src.config import settings

class APIClient:
    def __init__(self):
        self.url = settings.OPERA_BASE_URL
        self.key = settings.OPERA_CLIENT_SECRET
        self.headers = {"Authorization": f"Bearer {self.key}"}

    def fetch_data(self, endpoint):
        response = requests.get(f"{self.url}/{endpoint}", headers=self.headers)
        response.raise_for_status()
        return response.json()