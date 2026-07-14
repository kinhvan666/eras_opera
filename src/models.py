from pydantic import BaseModel
from typing import Optional

class Reservation(BaseModel):
    id: str
    hotel_id: str
    guest_name: str
    room_number: Optional[str]