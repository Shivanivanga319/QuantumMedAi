from pydantic import BaseModel
from typing import Optional


class EmergencyRequest(BaseModel):
    age: int = 35
    conscious: bool = True
    breathing: bool = True
    chest_pain: bool = False
    speech_problem: bool = False
    paralysis: bool = False
    severe_bleeding: bool = False
    choking: bool = False
    seizure: bool = False
    abdominal_pain: bool = False
    vomiting: bool = False
    fever: bool = False
    user_email: Optional[str] = None