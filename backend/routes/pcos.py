from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from models.prediction import Prediction
from schemas.pcos_schema import PCOSPredictionRequest
from services.pcos_service import predict_pcos

router = APIRouter(
    prefix="/pcos",
    tags=["PCOS Prediction"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def pcos_prediction(
    data: PCOSPredictionRequest,
    db: Session = Depends(get_db)
):
    result = predict_pcos(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease="PCOS (Polycystic Ovary Syndrome)",
            result=result.get("risk", "Unknown"),
            recommendation=result.get("recommendation", "")
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging prediction: {e}")

    return result