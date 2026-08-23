from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from models.prediction import Prediction
from schemas.stroke_schema import StrokePredictionRequest
from services.stroke_service import predict_stroke

router = APIRouter(
    prefix="/stroke",
    tags=["Stroke Prediction"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def stroke_prediction(
    data: StrokePredictionRequest,
    db: Session = Depends(get_db)
):
    result = predict_stroke(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease=result.get("disease", "Brain Stroke"),
            result=result.get("risk", "Unknown"),
            recommendation=result.get("recommendation", "")
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging prediction: {e}")

    return result