from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    user_email = Column(String)

    disease = Column(String)

    result = Column(String)

    recommendation = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)