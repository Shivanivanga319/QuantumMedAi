from pydantic import BaseModel
from typing import Optional


class PCOSPredictionRequest(BaseModel):
    age: Optional[int] = 24
    bmi: Optional[float] = 23.5
    menstrual_irregularity: Optional[int] = 0
    testosterone: Optional[float] = 45.0
    insulin: Optional[float] = 12.0
    lh_fsh_ratio: Optional[float] = 1.5
    acne: Optional[int] = 0
    hair_growth: Optional[int] = 0
    skin_darkening: Optional[int] = 0
    hair_loss: Optional[int] = 0
    user_email: Optional[str] = None
    language: Optional[str] = "en"