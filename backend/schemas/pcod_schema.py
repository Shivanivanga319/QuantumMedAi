from pydantic import BaseModel
from typing import Optional


class PCODPredictionRequest(BaseModel):
    age: Optional[int] = 24
    bmi: Optional[float] = 23.5
    irregular_periods: Optional[int] = 0
    weight_gain: Optional[int] = 0
    acne: Optional[int] = 0
    hair_loss: Optional[int] = 0
    ovarian_cysts: Optional[int] = 0
    insulin_resistance: Optional[int] = 0
    user_email: Optional[str] = None
    language: Optional[str] = "en"