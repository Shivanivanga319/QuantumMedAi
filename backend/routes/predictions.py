from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import re
import time
import base64
from datetime import datetime

from database import SessionLocal
from models.prediction import Prediction

from services.ai_service import analyze_with_ai, get_api_key
from services.vision_service import analyze_medical_image_with_ai, fallback_image_analysis

router = APIRouter(
    prefix="/predictions",
    tags=["Predictions & Diagnostics History"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SymptomAnalysisRequest(BaseModel):
    text: str
    user_email: Optional[str] = "guest@quantummed.ai"
    document_name: Optional[str] = None
    image_base64: Optional[str] = None
    mime_type: Optional[str] = "image/jpeg"
    language: Optional[str] = "en"


def generate_well_mannered_clinical_response(text: str, document_name: Optional[str] = None, language: str = "en") -> dict:
    t = text.lower().strip()
    
    # 1. Flexible Greetings & Introductions
    is_greeting = bool(re.search(r'^(h+i+|h+e+y+|h+e+l+l+o+|namaste|greetings|good\s*(morning|afternoon|evening)|నమస్కారం|హలో|नमस्ते|who\s*are\s*you|what\s*is\s*your\s*name|help|start)[\s!.,?]*$', t, re.IGNORECASE)) or t in ["hi", "hello", "hey", "namaste", "help"]
    
    if is_greeting:
        if language == "te":
            reply = "నమస్కారం! నేను మీ క్వాంటమ్‌మెడ్ AI వైద్య సహాయకుడిని. నేను మీకు ఎలా సహాయపడగలను? మీరు మీ లక్షణాలను వివరించవచ్చు, ఆరోగ్య సంబంధిత ప్రశ్నలు అడగవచ్చు లేదా ప్రిస్క్రిప్షన్/ల్యాబ్ నివేదికలను అప్‌లోడ్ చేయవచ్చు."
            doc = "జనరల్ ఫిజీషియన్ (సాధారణ వైద్యులు)"
            rec = "మీరు ఎదుర్కొంటున్న లక్షణాలను లేదా ఆరోగ్య సమస్యలను వివరించండి."
        elif language == "hi":
            reply = "नमस्ते! मैं आपका क्वांटममेड AI चिकित्सा सहायक हूँ। मैं आपकी क्या मदद कर सकता हूँ? आप अपने लक्षणों का वर्णन कर सकते हैं, स्वास्थ्य प्रश्न पूछ सकते हैं या लैब रिपोर्ट/पर्चे अपलोड कर सकते हैं।"
            doc = "सामान्य चिकित्सक (General Physician)"
            rec = "कृपया अपने लक्षणों या स्वास्थ्य संबंधी प्रश्नों को साझा करें।"
        else:
            reply = "Hello! I am QuantumMedAI, an AI medical assistant. How can I help you today? You can describe any symptoms you are experiencing, ask health questions, or upload a prescription/lab report."
            doc = "General Physician"
            rec = "Feel free to describe any symptoms, when they began, or attach a medical report."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Greeting"],
            "detected_diseases": ["General Health Consultation"],
            "risk_level": "Low",
            "doctor": doc,
            "recommendation": rec
        }


    # 2. Acute Emergency Red Flags
    emergency_patterns = [
        ('chest pain', 'Severe pressure or pain in the chest'),
        ('shortness of breath', 'Difficulty breathing / acute hypoxia'),
        ('face drooping', 'Facial asymmetry / stroke warning sign'),
        ('slurred speech', 'Speech impairment / neurological emergency'),
        ('paralysis', 'Loss of limb movement'),
        ('severe bleeding', 'Heavy uncontrollable blood loss'),
        ('unconscious', 'Loss of consciousness'),
        ('choking', 'Airway blockage'),
        ('ఛాతీ నొప్పి', 'ఛాతీలో తీవ్ర నొప్పి'),
        ('శ్వాస తీసుకోవడంలో ఇబ్బంది', 'ఆయాసం'),
        ('సీనే మే దర్ద్', 'सीने में दर्द')
    ]
    
    for term, desc in emergency_patterns:
        if term in t:
            if language == "te":
                reply = f"🚨 తక్షణ అత్యవసర వైద్య సహాయం అవసరం: మీరు పేర్కొన్న '{term}' తీవ్రమైన అత్యవసర పరిస్థితిని సూచిస్తుంది. దయచేసి ప్రశాంతంగా ఉండండి మరియు వెంటనే 108 లేదా 112 కు కాల్ చేసి సమీప అత్యవసర విభాగానికి (ER) వెళ్ళండి."
                doc = "అత్యవసర వైద్యులు / కార్డియాలజిస్ట్ / న్యూరాలజిస్ట్"
                rec = "వెంటనే అత్యవసర సేవలను (108 / 112) సంప్రదించండి."
            elif language == "hi":
                reply = f"🚨 तत्काल आपातकालीन चिकित्सा सहायता की आवश्यकता है: आपके द्वारा बताए गए '{term}' एक गंभीर स्थिति का संकेत है। कृपया तुरंत 108 या 112 पर कॉल करें और नजदीकी आपातकालीन कक्ष में जाएं।"
                doc = "आपातकालीन चिकित्सक / कार्डियोलॉजिस्ट"
                rec = "तुरंत आपातकालीन सेवाओं (108 / 112) को कॉल करें।"
            else:
                reply = f"🚨 URGENT MEDICAL ATTENTION REQUIRED: Your mention of '{term}' indicates a potential acute emergency. Please stay calm, avoid physical exertion, and seek immediate emergency medical care or call 108 / 112 right away. Do not attempt to drive yourself."
                doc = "Emergency Physician / Cardiologist / Neurologist"
                rec = "Call Emergency Services (108 / 112) or proceed to the nearest Emergency Room immediately."

            return {
                "ai_reply": reply,
                "is_emergency": True,
                "matched_keywords": [term],
                "detected_diseases": ["Critical Emergency Alert"],
                "risk_level": "Critical",
                "doctor": doc,
                "recommendation": rec
            }

    # 3. General Malaise / "Not feeling well"
    if any(phrase in t for phrase in ["not feeling well", "feeling sick", "feel unwell", "unwell", "not well", "బాగా లేదు", "నీరసంగా ఉంది", "तबीयत खराब", "अच्छा नहीं लग रहा"]):
        if language == "te":
            reply = (
                "మీ ఆరోగ్యం బాగాలేదని వినడానికి చింతిస్తున్నాను. మీకు మరింత సహాయపడటానికి కొన్ని వివరాలు చెప్పగలరా?\n\n"
                "• **ముఖ్యమైన ప్రశ్నలు:**\n"
                "  1. ఈ సమస్య ఎప్పుడు ప్రారంభమైంది?\n"
                "  2. మీకు జ్వరం, తలనొప్పి, వాంతులు లేదా ఒంటి నొప్పులు ఉన్నాయా?\n"
                "  3. తగినంత నీరు తాగుతున్నారా?\n\n"
                "• **స్వీయ సంరక్షణ సలహాలు:**\n"
                "  - బాగా విశ్రాంతి తీసుకోండి.\n"
                "  - గోరువెచ్చని నీరు మరియు ఓఆర్‌ఎస్ (ORS) ద్రావణం తాగండి.\n"
                "  - సమస్య 24-48 గంటలకు పైగా కొనసాగితే జనరల్ ఫిజీషియన్‌ను సంప్రదించండి."
            )
            doc = "జనరల్ ఫిజీషియన్"
            rec = "విశ్రాంతి తీసుకోండి, పుష్కలంగా నీరు తాగండి మరియు శరీర ఉష్ణోగ్రతను గమనించండి."
        elif language == "hi":
            reply = (
                "मुझे यह जानकर खेद है कि आपकी तबीयत ठीक नहीं है। बेहतर मार्गदर्शन के लिए कृपया कुछ जानकारी साझा करें:\n\n"
                "• **मुख्य प्रश्न:**\n"
                "  1. यह समस्या कब से शुरू हुई?\n"
                "  2. क्या बुखार, सिरदर्द, उल्टी या बदन दर्द है?\n\n"
                "• **प्राथमिक देखभाल:**\n"
                "  - भरपूर आराम करें।\n"
                "  - गुनगुना पानी और ओआरएस पिएं।\n"
                "  - यदि समस्या 24-48 घंटों तक बनी रहे, तो डॉक्टर से सलाह लें।"
            )
            doc = "सामान्य चिकित्सक (General Physician)"
            rec = "आराम करें, पानी पिएं और तापमान की निगरानी करें।"
        else:
            reply = (
                "Hello. I'm sorry to hear that you are not feeling well. Because \"not feeling well\" (general malaise) can be an early sign of many different things—such as a mild viral infection, fatigue, dehydration, or stress—I would like to understand your situation a bit better.\n\n"
                "### Follow-up Questions to Help Clarify:\n"
                "1. **Specific Symptoms:** Are you experiencing fever, chills, headache, body aches, sore throat, cough, nausea, stomach upset, or dizziness?\n"
                "2. **Onset & Duration:** How long have you felt this way, and did it come on suddenly or gradually?\n"
                "3. **Severity:** How intense is the discomfort on a scale of 1 to 10?\n\n"
                "### Supportive Home Care Measures:\n"
                "- **Hydration:** Sip water, clear broths, or warm herbal teas throughout the day.\n"
                "- **Rest:** Allow your body ample rest and avoid strenuous physical activities.\n\n"
                "If your symptoms persist over the next 24–48 hours, please consult a General Physician."
            )
            doc = "General Physician"
            rec = "Rest, maintain hydration, monitor your temperature, and share specific symptoms."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["General Malaise"],
            "detected_diseases": ["General Health Assessment"],
            "risk_level": "Low",
            "doctor": doc,
            "recommendation": rec
        }


    # 4. Headache / Migraine
    if "headache" in t or "migraine" in t or "head pain" in t:
        return {
            "ai_reply": (
                "Headaches can arise from several causes including tension, dehydration, eye strain, lack of sleep, or sinus congestion.\n\n"
                "• **Recommended Actions:**\n"
                "  - Rest in a dimly lit, quiet room.\n"
                "  - Drink 1–2 glasses of water to rule out dehydration.\n"
                "  - Apply a cool or warm compress to your forehead or the back of your neck.\n"
                "  - Avoid screen time and bright lights.\n\n"
                "⚠️ *Warning*: If the headache is sudden, severe ('thunderclap'), or accompanied by vision changes, numbness, or vomiting, seek immediate medical care."
            ),
            "is_emergency": False,
            "matched_keywords": ["Headache", "Cranial discomfort"],
            "detected_diseases": ["Tension Headache / Migraine Profile"],
            "risk_level": "Moderate" if "severe" in t else "Low",
            "doctor": "General Physician / Neurologist",
            "recommendation": "Hydrate, rest in a dark room, and seek evaluation if pain is unusually severe or recurrent."
        }

    # 5. Fever / Cold / Cough / Flu
    if any(w in t for w in ["fever", "cold", "cough", "flu", "sore throat", "runny nose", "congestion"]):
        return {
            "ai_reply": (
                "These symptoms frequently indicate an upper respiratory tract infection or seasonal viral illness.\n\n"
                "• **Supportive Home Care:**\n"
                "  - Stay well-hydrated with warm water, soups, and broths.\n"
                "  - Steam inhalation can help relieve nasal and chest congestion.\n"
                "  - Warm salt water gargles for sore throat relief.\n"
                "  - Monitor your temperature with a thermometer.\n\n"
                "Please consult a physician if fever exceeds 102°F (38.9°C), lasts over 3 days, or if breathing becomes labored."
            ),
            "is_emergency": False,
            "matched_keywords": ["Fever / Respiratory Symptoms"],
            "detected_diseases": ["Viral Infection / Upper Respiratory Condition"],
            "risk_level": "Moderate" if "high fever" in t else "Low",
            "doctor": "General Physician / ENT Specialist",
            "recommendation": "Stay hydrated, rest, take steam inhalation, and monitor temperature regularly."
        }

    # 6. Stomach Pain / Digestion / Nausea / Vomiting / Acidity
    if any(w in t for w in ["stomach", "abdominal", "nausea", "vomit", "acidity", "diarrhea", "constipation", "gas", "indigestion", "belly"]):
        return {
            "ai_reply": (
                "Gastrointestinal discomfort can stem from indigestion, acidity, food intolerance, or mild gastroenteritis.\n\n"
                "• **Helpful Relief Steps:**\n"
                "  - Avoid heavy, spicy, fried, or acidic foods; opt for light items like bananas, rice, or crackers (BRAT diet).\n"
                "  - Drink small sips of water or Oral Rehydration Solution (ORS) to prevent dehydration.\n"
                "  - Avoid lying down flat immediately after meals.\n\n"
                "⚠️ *Seek urgent care if you experience severe localized abdominal pain, inability to keep liquids down, or high fever.*"
            ),
            "is_emergency": False,
            "matched_keywords": ["Gastrointestinal Discomfort"],
            "detected_diseases": ["Gastric / Digestive Disturbance"],
            "risk_level": "Moderate",
            "doctor": "Gastroenterologist / General Physician",
            "recommendation": "Eat light bland foods, hydrate with ORS, and consult a doctor if severe pain or vomiting persists."
        }

    # 7. Heart & Cardiovascular Signs
    if any(w in t for w in ["palpitation", "irregular heartbeat", "high blood pressure", "cholesterol", "pulse", "hypertension"]):
        return {
            "ai_reply": (
                "Cardiovascular indicators require careful monitoring.\n\n"
                "• **Key Considerations:**\n"
                "  - Check and log your resting blood pressure and pulse rate.\n"
                "  - Minimize caffeine, sodium, and high-stress triggers.\n"
                "  - Practice slow deep breathing.\n\n"
                "We recommend visiting our **🩺 Disease Predictors** tab to run the full Heart Disease Risk Assessment, or scheduling an appointment with a Cardiologist."
            ),
            "is_emergency": False,
            "matched_keywords": ["Cardiovascular Markers"],
            "detected_diseases": ["Cardiovascular Evaluation Profile"],
            "risk_level": "Moderate",
            "doctor": "Cardiologist",
            "recommendation": "Log BP readings, avoid excessive stimulants, and run the precision Heart Disease Calculator."
        }

    # 8. PCOS / PCOD / Women's Hormonal Health
    if any(w in t for w in ["pcos", "pcod", "period", "menstrual", "ovarian", "cramps", "hormone", "facial hair", "acne"]):
        return {
            "ai_reply": (
                "Hormonal and menstrual patterns are important indicators of reproductive and endocrine health.\n\n"
                "• **Recommendations:**\n"
                "  - Maintain a balanced low-glycemic diet rich in whole foods and fiber.\n"
                "  - Engage in regular moderate physical activity.\n"
                "  - Track your cycle dates and any related symptoms (weight shifts, skin changes).\n\n"
                "You can use the **PCOS / PCOD Assessment** in our Disease Predictors tab for a detailed risk analysis, and consult a Gynecologist for ultrasound or hormone profiles."
            ),
            "is_emergency": False,
            "matched_keywords": ["Endocrine / Gynecological Indicators"],
            "detected_diseases": ["PCOS / PCOD Hormonal Profile"],
            "risk_level": "Moderate",
            "doctor": "Gynecologist / Endocrinologist",
            "recommendation": "Track menstrual cycles, adopt low-GI nutrition, and consult a Gynecologist for hormonal testing."
        }

    # Default General Consultation
    return {
        "ai_reply": (
            f"Thank you for sharing your concern: \"{text}\".\n\n"
            "To provide the most accurate medical advice, please let me know:\n"
            "• How long have you had this concern?\n"
            "• Are there any other symptoms you are noticing (pain, fever, fatigue, nausea)?\n\n"
            "In the meantime, prioritize adequate rest and hydration. You can also explore our **🩺 Disease Predictors** tab for specific condition evaluations."
        ),
        "is_emergency": False,
        "matched_keywords": ["Patient Query"],
        "detected_diseases": ["General Health Inquiry"],
        "risk_level": "Low",
        "doctor": "General Physician",
        "recommendation": "Provide additional symptom details or consult a General Physician for clinical evaluation."
    }


@router.get("/status")
def get_ai_status():
    api_key, provider = get_api_key()
    return {
        "ai_enabled": bool(api_key),
        "provider": provider,
        "model": "Gemini Multimodal Vision & Clinical Intelligence",
        "vision_enabled": True
    }


@router.get("/history")
def get_prediction_history(
    email: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Prediction)
    if email:
        clean_email = email.lower().strip()
        query = query.filter((Prediction.user_email == clean_email) | (Prediction.user_email == "guest@quantummed.ai"))
    
    records = query.order_by(Prediction.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "user_email": r.user_email,
            "disease": r.disease,
            "result": r.result,
            "recommendation": r.recommendation,
            "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat()
        }
        for r in records
    ]


@router.post("/symptoms")
def analyze_symptoms(
    data: SymptomAnalysisRequest,
    db: Session = Depends(get_db)
):
    # 1. If an image is provided in base64, route through Medical Vision Engine
    if data.image_base64:
        vision_result = analyze_medical_image_with_ai(
            image_base64=data.image_base64,
            mime_type=data.mime_type or "image/jpeg",
            user_query=data.text,
            language=data.language or "en"
        )
        if not vision_result:
            vision_result = fallback_image_analysis(data.document_name or "Medical Image", data.text)

        # Log prediction to DB
        user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"
        try:
            prediction = Prediction(
                user_email=user_email,
                disease=f"Image Vision: {vision_result.get('document_title', 'Medical Document')}",
                result=f"{vision_result.get('risk_level', 'Low')} Risk",
                recommendation=f"Specialist: {vision_result.get('doctor', 'General Physician')}"
            )
            db.add(prediction)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error logging vision prediction: {e}")

        return {
            "status": "success",
            "ai_reply": vision_result.get("ai_reply", ""),
            "is_emergency": vision_result.get("is_emergency", False),
            "matched_keywords": [vision_result.get("document_type", "Medical Document")],
            "detected_diseases": [vision_result.get("document_title", "Document Analysis")],
            "risk_level": vision_result.get("risk_level", "Low"),
            "doctor": vision_result.get("doctor", "General Physician"),
            "recommendation": vision_result.get("recommendations", ["Consult your healthcare provider."])[0] if vision_result.get("recommendations") else "Consult your physician.",
            "vision_data": vision_result
        }

    t_clean = data.text.lower().strip()
    is_greeting = bool(re.search(r'^(h+i+|h+e+y+|h+e+l+l+o+|namaste|greetings|good\s*(morning|afternoon|evening)|నమస్కారం|హలో|नमस्ते|who\s*are\s*you|what\s*is\s*your\s*name|help|start)[\s!.,?]*$', t_clean, re.IGNORECASE)) or t_clean in ["hi", "hello", "hey", "namaste", "help"]

    print(f"[/symptoms START] text: '{data.text}', is_greeting: {is_greeting}")
    import time
    _t_start = time.time()

    if is_greeting:
        clinical_res = generate_well_mannered_clinical_response(data.text, data.document_name, data.language or "en")
        ai_reply = clinical_res["ai_reply"]
        is_emergency = clinical_res["is_emergency"]
        matched_keywords = clinical_res["matched_keywords"]
        detected_diseases = clinical_res["detected_diseases"]
        risk_level = clinical_res["risk_level"]
        doctor = clinical_res["doctor"]
        recommendation = clinical_res["recommendation"]
        print(f"[/symptoms GREETING DONE in {time.time() - _t_start:.3f}s]")
    else:
        # 2. Route clinical queries through AI Consultation Service (Groq / Gemini / OpenAI)
        ai_result = analyze_with_ai(
            query_text=data.text,
            document_name=data.document_name,
            language=data.language or "en"
        )
        print(f"[/symptoms AI CALL DONE in {time.time() - _t_start:.3f}s, got result: {bool(ai_result)}]")

        if ai_result and ai_result.get("ai_reply"):
            ai_reply = ai_result.get("ai_reply", "")
            is_emergency = ai_result.get("is_emergency", False)
            matched_keywords = ai_result.get("matched_keywords", [])
            detected_diseases = ai_result.get("detected_diseases", [])
            risk_level = ai_result.get("risk_level", "Low")
            doctor = ai_result.get("doctor", "General Physician")
            recommendation = ai_result.get("recommendation", "Consult a healthcare provider.")
        else:
            clinical_res = generate_well_mannered_clinical_response(data.text, data.document_name, data.language or "en")
            ai_reply = clinical_res["ai_reply"]
            is_emergency = clinical_res["is_emergency"]
            matched_keywords = clinical_res["matched_keywords"]
            detected_diseases = clinical_res["detected_diseases"]
            risk_level = clinical_res["risk_level"]
            doctor = clinical_res["doctor"]
            recommendation = clinical_res["recommendation"]

    _t_db = time.time()
    # Save to prediction history
    user_email = data.user_email.lower().strip() if data.user_email else "guest@quantummed.ai"
    try:
        prediction = Prediction(
            user_email=user_email,
            disease=", ".join(detected_diseases) if detected_diseases else ("Emergency Alert" if is_emergency else "Clinical AI Consultation"),
            result=f"{risk_level} Risk",
            recommendation=recommendation
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging symptom analysis: {e}")
    print(f"[/symptoms DB DONE in {time.time() - _t_db:.3f}s | TOTAL: {time.time() - _t_start:.3f}s]")


    return {
        "status": "success",
        "ai_reply": ai_reply,
        "is_emergency": is_emergency,
        "matched_keywords": matched_keywords,
        "detected_diseases": detected_diseases,
        "risk_level": risk_level,
        "doctor": doctor,
        "recommendation": recommendation
    }


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    query: Optional[str] = Form(""),
    user_email: Optional[str] = Form("guest@quantummed.ai"),
    language: Optional[str] = Form("en"),
    db: Session = Depends(get_db)
):
    """
    Direct multipart upload endpoint for medical prescriptions and lab reports.
    """
    contents = await file.read()
    b64_str = base64.b64encode(contents).decode("utf-8")
    mime_type = file.content_type or "image/jpeg"

    vision_result = analyze_medical_image_with_ai(
        image_base64=b64_str,
        mime_type=mime_type,
        user_query=query,
        language=language
    )

    if not vision_result:
        vision_result = fallback_image_analysis(file.filename or "Uploaded Document", query)

    # Save to DB
    clean_email = user_email.lower().strip() if user_email else "guest@quantummed.ai"
    try:
        prediction = Prediction(
            user_email=clean_email,
            disease=f"Image Scan: {vision_result.get('document_title', file.filename)}",
            result=f"{vision_result.get('risk_level', 'Low')} Risk",
            recommendation=f"Specialist: {vision_result.get('doctor', 'General Physician')}"
        )
        db.add(prediction)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving uploaded document prediction: {e}")

    return {
        "status": "success",
        "filename": file.filename,
        "ai_reply": vision_result.get("ai_reply", ""),
        "is_emergency": vision_result.get("is_emergency", False),
        "document_type": vision_result.get("document_type", "Medical Document"),
        "document_title": vision_result.get("document_title", file.filename),
        "doctor": vision_result.get("doctor", "General Physician"),
        "risk_level": vision_result.get("risk_level", "Low"),
        "prescriptions": vision_result.get("prescriptions", []),
        "lab_biomarkers": vision_result.get("lab_biomarkers", []),
        "abnormal_findings": vision_result.get("abnormal_findings", []),
        "recommendations": vision_result.get("recommendations", [])
    }
