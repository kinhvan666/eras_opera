# extractor/src/models.py
from pydantic import BaseModel, Field
from typing import Optional, List

class ProfileName(BaseModel):
    name_id: int = Field(..., alias='nameId')
    name_type: str = Field(..., alias='nameType')
    first_name: Optional[str] = Field(None, alias='firstName')
    last_name: str = Field(..., alias='lastName')

class ReservationName(BaseModel):
    profile: ProfileName

class Reservation(BaseModel):
    reservation_id: str = Field(..., alias='reservationId')
    confirmation_no: str = Field(..., alias='confirmationNo')
    reservation_name_list: List[ReservationName] = Field(..., alias='reservationNameList')
    # Add other relevant reservation fields from the SPEC as needed
