from pydantic import BaseModel
from typing import Optional


class HeartPredictionRequest(BaseModel):
    age: Optional[int] = 50
    sex: Optional[int] = 1
    cp: Optional[int] = 0
    trestbps: Optional[int] = 120
    chol: Optional[int] = 200
    fbs: Optional[int] = 0
    restecg: Optional[int] = 1
    thalach: Optional[int] = 150
    exang: Optional[int] = 0
    oldpeak: Optional[float] = 1.0
    slope: Optional[int] = 1
    ca: Optional[int] = 0
    thal: Optional[int] = 2
    user_email: Optional[str] = None
    language: Optional[str] = "en"