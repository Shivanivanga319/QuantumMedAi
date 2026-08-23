from pydantic import BaseModel
from typing import Optional


class LiverPredictionRequest(BaseModel):
    age: Optional[int] = 45
    gender: Optional[int] = 1        # 1 = Male, 0 = Female
    total_bilirubin: Optional[float] = 1.0
    direct_bilirubin: Optional[float] = 0.3
    alkaline_phosphotase: Optional[int] = 180
    alamine_aminotransferase: Optional[int] = 30
    aspartate_aminotransferase: Optional[int] = 30
    total_proteins: Optional[float] = 6.8
    albumin: Optional[float] = 3.5
    albumin_globulin_ratio: Optional[float] = 1.0
    user_email: Optional[str] = None
    language: Optional[str] = "en"