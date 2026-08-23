from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from models.prediction import Prediction
from schemas.pcod_schema import PCODPredictionRequest
from services.pcod_service import predict_pcod

router = APIRouter(
    prefix="/pcod",
    tags=["PCOD Prediction"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def pcod_prediction(
    data: PCODPredictionRequest,
    db: Session = Depends(get_db)
):
    result = predict_pcod(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease="PCOD (Polycystic Ovarian Disease)",
            result=result.get("risk", "Unknown"),
            recommendation=result.get("recommendation", "")
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging prediction: {e}")

    return result