from pydantic import BaseModel
from typing import Optional


class KidneyPredictionRequest(BaseModel):
    age: Optional[int] = 48
    creatinine: Optional[float] = 1.0
    urea: Optional[float] = 30.0
    hemoglobin: Optional[float] = 13.0
    blood_pressure: Optional[int] = 120
    pus_cells: Optional[int] = 0
    bacteria: Optional[int] = 0
    red_blood_cells: Optional[int] = 0
    user_email: Optional[str] = None
    language: Optional[str] = "en"