from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database import SessionLocal
from models.prediction import Prediction
from schemas.emergency_schema import EmergencyRequest
from services.emergency_service import emergency_response
from services.ai_service import emergency_with_ai
from services.hospital_service import find_nearby_hospitals, register_hospital_pre_alert
from services.sms_service import format_emergency_sms_payload, dispatch_sms_via_cloud

router = APIRouter(
    prefix="/emergency",
    tags=["Emergency Response & Resource Navigation"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SmsDispatchRequest(BaseModel):
    patient_name: Optional[str] = "Patient"
    emergency_type: str
    severity: Optional[str] = "Critical"
    lat: Optional[float] = None
    lng: Optional[float] = None
    first_aid_summary: Optional[str] = None
    destination_number: Optional[str] = "108"
    user_email: Optional[str] = "guest@quantummed.ai"


class PreAlertRequest(BaseModel):
    hospital_id: str
    patient_name: Optional[str] = "Patient"
    emergency_type: str
    severity: Optional[str] = "Critical"
    eta_minutes: Optional[int] = 8
    contact_phone: Optional[str] = None
    user_email: Optional[str] = "guest@quantummed.ai"


@router.post("/check")
def check_emergency(
    data: EmergencyRequest,
    db: Session = Depends(get_db)
):
    # 1. Try Generative AI Emergency Triage if API key present
    ai_result = emergency_with_ai(data.dict())

    if ai_result:
        result = ai_result
    else:
        # Fallback to deterministic triage rules
        result = emergency_response(data)

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"

    try:
        prediction = Prediction(
            user_email=user_email,
            disease=f"Emergency: {result.get('emergency', 'Triage Assessment')}",
            result=f"Severity: {result.get('severity', 'Moderate')}",
            recommendation=f"Specialist: {result.get('doctor', 'Emergency Physician')}"
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging emergency triage: {e}")

    return result


@router.get("/nearby-hospitals")
def get_nearby_hospitals_endpoint(
    lat: float = Query(17.4258, description="User Latitude"),
    lng: float = Query(78.4116, description="User Longitude"),
    radius_km: float = Query(35.0, description="Search radius in kilometers"),
    specialty: Optional[str] = Query(None, description="Specialty filter (e.g. Cardiac, Stroke, Trauma, ICU)"),
    city: Optional[str] = Query(None, description="City or locality filter (e.g. Hyderabad, Bengaluru, Delhi)"),
    scheme: Optional[str] = Query(None, description="Health scheme filter (e.g. Aarogyasri, Ayushman Bharat, CGHS)")
):
    """
    Returns nearest hospitals with live ICU availability telemetry,
    Ambulance travel time (ETA), and Google Maps driving direction links.
    """
    hospitals = find_nearby_hospitals(
        user_lat=lat,
        user_lng=lng,
        radius_km=radius_km,
        specialty_filter=specialty,
        city_filter=city,
        scheme_filter=scheme
    )
    return {
        "status": "success",
        "user_coordinates": {"lat": lat, "lng": lng},
        "search_radius_km": radius_km,
        "count": len(hospitals),
        "hospitals": hospitals
    }


@router.post("/pre-alert")
def send_hospital_pre_alert(
    data: PreAlertRequest,
    db: Session = Depends(get_db)
):
    """
    Sends an advance ER Pre-Alert directly to the hospital trauma team,
    reserving emergency triage bay and generating a pre-arrival intake pass.
    """
    alert_info = register_hospital_pre_alert(
        hospital_id=data.hospital_id,
        patient_name=data.patient_name or "Patient",
        emergency_type=data.emergency_type,
        severity=data.severity or "Critical",
        eta_minutes=data.eta_minutes or 8,
        contact_phone=data.contact_phone
    )

    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"
    try:
        prediction = Prediction(
            user_email=user_email,
            disease=f"ER Pre-Alert: {data.emergency_type}",
            result=f"Hospital Alerted: {alert_info.get('hospital_name', data.hospital_id)}",
            recommendation=f"Token: {alert_info.get('pre_alert_token')}"
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging ER pre-alert: {e}")

    return alert_info


@router.post("/sms-dispatch")
def dispatch_emergency_sms(
    data: SmsDispatchRequest,
    db: Session = Depends(get_db)
):
    """
    Generates an automated Offline SMS and WhatsApp SOS dispatch payload,
    complete with live GPS coordinates, Google Maps pin, and native hardware protocols.
    """
    payload = format_emergency_sms_payload(
        patient_name=data.patient_name or "Patient",
        emergency_type=data.emergency_type,
        severity=data.severity or "Critical",
        lat=data.lat,
        lng=data.lng,
        first_aid_summary=data.first_aid_summary
    )

    # Attempt cloud gateway dispatch if credentials present, or deliver direct hardware protocols
    dispatch_result = dispatch_sms_via_cloud(payload, destination_number=data.destination_number or "108")

    # Log to DB
    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"
    try:
        prediction = Prediction(
            user_email=user_email,
            disease=f"SMS SOS Dispatch: {data.emergency_type}",
            result=f"{data.severity} Priority Alert Dispatched",
            recommendation=f"GPS: {data.lat}, {data.lng}" if (data.lat and data.lng) else "Location Alert Sent"
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging SMS dispatch: {e}")

    return dispatch_result