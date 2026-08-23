from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from models.prediction import Prediction
from schemas.heart_schema import HeartPredictionRequest
from services.heart_service import predict_heart

router = APIRouter(
    prefix="/heart",
    tags=["Heart Prediction"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def heart_prediction(
    data: HeartPredictionRequest,
    db: Session = Depends(get_db)
):
    result = predict_heart(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease=result.get("disease", "Heart Disease"),
            result=result.get("risk", "Unknown"),
            recommendation=result.get("recommendation", "")
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging prediction: {e}")

    return result