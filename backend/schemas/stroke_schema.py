from pydantic import BaseModel
from typing import Optional


class StrokePredictionRequest(BaseModel):
    age: Optional[int] = 50
    hypertension: Optional[int] = 0
    heart_disease: Optional[int] = 0
    avg_glucose_level: Optional[float] = 100.0
    bmi: Optional[float] = 24.5
    smoking_status: Optional[int] = 0
    user_email: Optional[str] = None
    language: Optional[str] = "en"