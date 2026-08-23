from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from models.prediction import Prediction
from schemas.liver_schema import LiverPredictionRequest
from services.liver_service import predict_liver

router = APIRouter(
    prefix="/liver",
    tags=["Liver Prediction"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/predict")
def liver_prediction(
    data: LiverPredictionRequest,
    db: Session = Depends(get_db)
):
    result = predict_liver(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease=result.get("disease", "Liver Disease"),
            result=result.get("risk", "Unknown"),
            recommendation=result.get("recommendation", "")
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging prediction: {e}")

    return result