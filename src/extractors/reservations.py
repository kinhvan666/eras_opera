from src.client import APIClient
from src.models import Reservation

class ReservationExtractor:
    def __init__(self):
        self.client = APIClient()

    def extract(self):
        data = self.client.fetch_data("rsv/v1/reservations")
        return [Reservation(**item) for item in data]
