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
            reply = "నమస్కారం! నేను మీ క్వాంటమ్‌మెడ్ AI వైద్య సహాయకుడిని. నేను మీకు ఎలా సహాయపడగలను? మీరు మీ లక్షణాలను వివరించవచ్చు (ఉదాహరణకు: జ్వరం, గుండె సమస్యలు, కిడ్నీ, కాలేయం, డయాబెటిస్, థైరాయిడ్, PCOS మొదలైనవి), లేదా ప్రిస్క్రిప్షన్/ల్యాబ్ రిపోర్టులను అప్‌లోడ్ చేయవచ్చు."
            doc = "జనరల్ ఫిజీషియన్ (సాధారణ వైద్యులు)"
            rec = "మీరు ఎదుర్కొంటున్న లక్షణాలను లేదా ఆరోగ్య సమస్యలను వివరించండి."
        elif language == "hi":
            reply = "नमस्ते! मैं आपका क्वांटममेड AI चिकित्सा सहायक हूँ। मैं आपकी क्या मदद कर सकता हूँ? आप अपने लक्षणों का वर्णन कर सकते हैं (जैसे: बुखार, हृदय रोग, किडनी, लिवर, मधुमेह, थायराइड, पीसीओएस आदि) या लैब रिपोर्ट/पर्चे अपलोड कर सकते हैं।"
            doc = "सामान्य चिकित्सक (General Physician)"
            rec = "कृपया अपने लक्षणों या स्वास्थ्य संबंधी प्रश्नों को साझा करें।"
        else:
            reply = "Hello! I am Dr. Quantum, your clinical AI physician assistant at QuantumMedAI. How can I assist you today? You can describe any symptoms (e.g. fever, chest heaviness, kidney pain, liver issues, diabetes, PCOS, stroke risk, etc.), ask for disease predictions, or upload a prescription/lab report."
            doc = "General Physician"
            rec = "Feel free to describe your symptoms, ask about any health condition, or use our dedicated Disease Predictor calculators."

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

    # 3. Heart Disease, Hypertension & Cardiovascular Risk
    if any(w in t for w in ["heart", "cardiac", "cardiovascular", "cholesterol", "blood pressure", "hypertension", "palpitation", "arrhythmia", "angina", "coronary", "గుండె", "హై బీపీ", "హృదయ", "कोलेस्ट्रॉल"]):
        if language == "te":
            reply = (
                "🫀 **గుండె & రక్తనాళాల ఆరోగ్య విశ్లేషణ (Cardiovascular Assessment):**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** గుండె జబ్బులు మరియు అధిక రక్తపోటు రక్తనాళాలలో కొలెస్ట్రాల్ చేరడం వల్ల రక్తప్రసరణ తగ్గడం లేదా రక్తపోటు పెరగడం వల్ల కలుగుతాయి.\n"
                "• **ముఖ్యమైన లక్షణాలు:** ఛాతీలో అసౌకర్యం, ఆయాసం, గుండె దడ, అలసట, తలతిరగడం.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** కార్డియోవాస్కులర్ రిస్క్ ప్రొఫైల్ (మితమైన నుండి అధిక ప్రమాదం).\n"
                "• **జీవనశైలి & సంరక్షణ:** ఉప్పు తగ్గించండి, నూనె/కొవ్వు పదార్థాలకు దూరంగా ఉండండి, రోజూ 30 నిమిషాలు నడవండి.\n"
                "• **సిఫార్సు:** మా **🩺 Disease Predictors** ట్యాబ్‌లోని **Heart Disease Predictor** కాలిక్యులేటర్‌ను ఉపయోగించి ఖచ్చితమైన విశ్లేషణ పొందండి."
            )
            doc = "కార్డియాలజిస్ట్ (గుండె నిపుణులు)"
            rec = "బీపీ మరియు లిపిడ్ ప్రొఫైల్ తనిఖీ చేసుకోండి. కార్డియాలజిస్ట్‌ను సంప్రదించండి."
        elif language == "hi":
            reply = (
                "🫀 **हृदय और रक्तचाप स्वास्थ्य मूल्यांकन (Cardiovascular Assessment):**\n\n"
                "• **बुनियादी जानकारी (Basics):** हृदय रोग और उच्च रक्तचाप रक्त वाहिकाओं में रुकावट या उच्च तनाव के कारण होते हैं।\n"
                "• **प्रमुख लक्षण:** सीने में भारीपन, सांस फूलना, दिल की धड़कन तेज होना, थकान, चक्कर आना।\n"
                "• **रोग भविष्यवाणी (Prediction):** संभावित हृदय संबंधी जोखिम (मध्यम से उच्च)।\n"
                "• **घरेलू देखभाल व जीवनशैली:** नमक और वसायुक्त भोजन कम करें, नियमित टहलें, तनाव से बचें।\n"
                "• **सुझाव:** हमारे **🩺 Disease Predictors** टैब में जाकर **Heart Disease Predictor** का उपयोग करें।"
            )
            doc = "कार्डियोलॉजिस्ट (हृदय रोग विशेषज्ञ)"
            rec = "रक्तचाप और लिपिड प्रोफाइल की जांच करवाएं। कार्डियोलॉजिस्ट से मिलें।"
        else:
            reply = (
                "🫀 **Cardiovascular Disease & Heart Health Overview:**\n\n"
                "• **Condition Basics:** Cardiovascular disorders and hypertension occur when arterial elasticity decreases or plaque accumulates, increasing cardiac workload and impeding blood flow.\n"
                "• **Key Symptoms:** Chest tightness or aching, shortness of breath on exertion, irregular palpitations, unexplained fatigue, and lightheadedness.\n"
                "• **Diagnostic Prediction:** Potential Cardiovascular / Hypertensive Risk Profile.\n"
                "• **Supportive Lifestyle Actions:**\n"
                "  - Restrict sodium intake to under 2g/day and limit saturated fats.\n"
                "  - Engage in 30 minutes of moderate aerobic exercise (brisk walking).\n"
                "  - Regularly log resting systolic and diastolic blood pressure.\n\n"
                "💡 *QuantumMedAI Recommendation:* Visit our **🩺 Disease Predictors** tab and run the **Heart Disease Predictor** for full quantum-classical risk stratification."
            )
            doc = "Cardiologist"
            rec = "Monitor resting blood pressure, get a Lipid Profile & ECG, and consult a Cardiologist."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Cardiovascular Markers", "Hypertension", "Heart Health"],
            "detected_diseases": ["Cardiovascular Disease Risk"],
            "risk_level": "Moderate",
            "doctor": doc,
            "recommendation": rec
        }

    # 4. Kidney Disease, Chronic Kidney Disease (CKD) & Kidney Stones
    if any(w in t for w in ["kidney", "renal", "creatinine", "kidney stone", "proteinuria", "urea", "gfr", "కిడ్నీ", "మూత్రపిండ", "गुर्दा", "किडनी"]):
        if language == "te":
            reply = (
                "💧 **కిడ్నీ (మూత్రపిండాల) ఆరోగ్య విశ్లేషణ (Renal Assessment):**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** మూత్రపిండాలు రక్తాన్ని శుద్ధి చేసి వ్యర్థాలను బయటకు పంపుతాయి. క్రియాటినిన్ పెరగడం లేదా కిడ్నీలో రాళ్లు ఏర్పడటం మూత్రపిండాల పనితీరు తగ్గడానికి సూచికలు.\n"
                "• **లక్షణాలు:** నడుము/పక్కటెముకల కింద నొప్పి, మూత్రంలో మంట లేదా నురుగు, కాళ్ల వాపు, నీరసం.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** మూత్రపిండాల సమస్య లేదా కిడ్నీ స్టోన్ సంకేతం.\n"
                "• **సంరక్షణ:** రోజుకు 2.5–3 లీటర్ల నీరు త్రాగండి, నొప్పి నివారణ మందులు (NSAIDs) అతిగా వాడకండి.\n"
                "• **సిఫార్సు:** మా **🩺 Disease Predictors** ట్యాబ్‌లోని **Chronic Kidney Disease Predictor** ఉపయోగించండి."
            )
            doc = "నెఫ్రాలజిస్ట్ / యూరాలజిస్ట్"
            rec = "సీరమ్ క్రియాటినిన్, బ్లడ్ యూరియా మరియు యూరిన్ రొటీన్ పరీక్ష చేయించుకోండి."
        elif language == "hi":
            reply = (
                "💧 **किडनी (गुर्दे) का स्वास्थ्य मूल्यांकन (Renal Assessment):**\n\n"
                "• **बुनियादी जानकारी (Basics):** किडनी शरीर से विषाक्त पदार्थों को फ़िल्टर करती है। सीरम क्रिएटिनिन का बढ़ना या पथरी बनना किडनी की कार्यक्षमता में कमी का संकेत है।\n"
                "• **प्रमुख लक्षण:** पीठ के निचले हिस्से में दर्द, पेशाब में झाग या जलन, पैरों में सूजन, थकान।\n"
                "• **रोग भविष्यवाणी (Prediction):** संभावित क्रॉनिक किडनी डिजीज (CKD) या किडनी स्टोन।\n"
                "• **घरेलू देखभाल:** प्रतिदिन 3 लीटर पानी पिएं, बिना डॉक्टरी सलाह के पेनकिलर न लें।\n"
                "• **सुझाव:** सटीक परिणाम के लिए हमारे **Chronic Kidney Disease Predictor** का उपयोग करें।"
            )
            doc = "नेफ्रोलॉजिस्ट / यूरोलॉजिस्ट"
            rec = "किडनी फंक्शन टेस्ट (KFT) और यूरिन एनालिसिस करवाएं।"
        else:
            reply = (
                "💧 **Renal Function & Kidney Disease Overview:**\n\n"
                "• **Condition Basics:** The kidneys filter metabolic waste products and regulate electrolyte balance. Elevated serum creatinine, reduced eGFR, or crystal formation (stones) signal compromised renal clearance.\n"
                "• **Key Symptoms:** Flank or lower back pain, frothy/cloudy urine, peripheral edema (ankle swelling), persistent fatigue, and altered urinary frequency.\n"
                "• **Diagnostic Prediction:** Chronic Kidney Disease (CKD) / Nephrolithiasis Risk Profile.\n"
                "• **Supportive Home Care:**\n"
                "  - Maintain adequate hydration (2.5–3 Liters of water daily).\n"
                "  - Avoid self-medicating with over-the-counter NSAID pain relievers.\n"
                "  - Restrict high-sodium and processed phosphorus-rich foods.\n\n"
                "💡 *QuantumMedAI Recommendation:* Launch the **Chronic Kidney Disease Predictor** in our Disease Predictors tab for calibrated biomarker analysis."
            )
            doc = "Nephrologist / Urologist"
            rec = "Check Serum Creatinine, BUN, eGFR, and Urine Albumin-to-Creatinine Ratio (uACR)."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Renal Biomarkers", "Creatinine", "Kidney Function"],
            "detected_diseases": ["Chronic Kidney Disease / Renal Stone Evaluation"],
            "risk_level": "Moderate",
            "doctor": doc,
            "recommendation": rec
        }

    # 5. Liver Disease, Fatty Liver, Jaundice & Cirrhosis
    if any(w in t for w in ["liver", "fatty liver", "jaundice", "cirrhosis", "bilirubin", "sgot", "sgpt", "alt", "ast", "hepatitis", "కాలేయం", "పచ్చకామెర్లు", "लिवर", "पीलिया"]):
        if language == "te":
            reply = (
                "🧪 **కాలేయ (లివర్) ఆరోగ్య విశ్లేషణ (Hepatic Assessment):**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** కాలేయం జీర్ణక్రియ, విషపదార్థాల తొలగింపు మరియు జీవక్రియలను నియంత్రిస్తుంది. ఫ్యాటీ లివర్ లేదా కామెర్లు (జాండిస్) కాలేయ వాపును సూచిస్తాయి.\n"
                "• **లక్షణాలు:** కళ్ళు/చర్మం పసుపు రంగులోకి మారడం, కుడి పక్కటెముక కింద నొప్పి, ఆకలి మందగించడం, విపరీతమైన అలసట.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** ఫ్యాటీ లివర్ / హెపాటిక్ ఇన్‌ఫ్లమేషన్ ప్రొఫైల్.\n"
                "• **సంరక్షణ:** ఆల్కహాల్ పూర్తిగా మానేయండి, నూనె పదార్థాలు తగ్గించండి, యాంటీఆక్సిడెంట్లు అధికంగా ఉండే ఆహారం తీసుకోండి.\n"
                "• **సిఫార్సు:** మా **🩺 Disease Predictors** లోని **Liver Disease Predictor** కాలిక్యులేటర్‌ను ఉపయోగించండి."
            )
            doc = "హెపటాలజిస్ట్ / గ్యాస్ట్రోఎంటరాలజిస్ట్"
            rec = "లివర్ ఫంక్షన్ టెస్ట్ (LFT) మరియు అల్ట్రాసౌండ్ అబ్డామిన్ స్కాన్ చేయించుకోండి."
        elif language == "hi":
            reply = (
                "🧪 **लिवर स्वास्थ्य और पीलिया मूल्यांकन (Hepatic Assessment):**\n\n"
                "• **बुनियादी जानकारी (Basics):** लिवर शरीर में पाचन और डिटॉक्सीफिकेशन का मुख्य अंग है। फैटी लिवर या बिलीरुबिन का बढ़ना लिवर में सूजन का संकेत है।\n"
                "• **प्रमुख लक्षण:** आंखें या त्वचा पीली पड़ना (पीलिया), भूख में कमी, पेट के ऊपरी दाहिने हिस्से में दर्द, अत्यधिक थकान।\n"
                "• **रोग भविष्यवाणी (Prediction):** फैटी लिवर / हेपेटाइटिस जोखिम प्रोफ़ाइल।\n"
                "• **घरेलू देखभाल:** शराब और तैलीय भोजन से बचें, हरी पत्तेदार सब्जियां और ताजे फल खाएं।\n"
                "• **सुझाव:** विस्तृत जांच के लिए हमारे **Liver Disease Predictor** का उपयोग करें।"
            )
            doc = "हेपेटोलॉजिस्ट / गैस्ट्रोएंटेरोलॉजिस्ट"
            rec = "लिवर फंक्शन टेस्ट (LFT - Bilirubin, SGOT, SGPT) और अल्ट्रासाउंड करवाएं।"
        else:
            reply = (
                "🧪 **Hepatic Disease & Liver Health Overview:**\n\n"
                "• **Condition Basics:** The liver is central to metabolic detoxification, bile production, and protein synthesis. Fatty liver disease (NAFLD/NASH), hepatitis, and jaundice occur when hepatic parenchyma is inflamed or overloaded with lipid deposits.\n"
                "• **Key Symptoms:** Scleral/cutaneous jaundice (yellow eyes/skin), right upper quadrant abdominal tenderness, loss of appetite, dark urine, and chronic fatigue.\n"
                "• **Diagnostic Prediction:** Fatty Liver Disease / Hepatic Dysfunction Profile.\n"
                "• **Supportive Lifestyle Actions:**\n"
                "  - Completely eliminate alcohol and refined fructose/syrups.\n"
                "  - Adopt a Mediterranean diet rich in leafy greens, olive oil, and lean proteins.\n"
                "  - Aim for gradual weight management (5–10% body weight reduction).\n\n"
                "💡 *QuantumMedAI Recommendation:* Check your hepatic risk using the **Liver Disease Predictor** in our Disease Predictors suite."
            )
            doc = "Hepatologist / Gastroenterologist"
            rec = "Obtain a Liver Function Test (Total Bilirubin, SGOT/AST, SGPT/ALT, Alkaline Phosphatase) and Ultrasound Abdomen."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Hepatic Markers", "Bilirubin", "Liver Function"],
            "detected_diseases": ["Fatty Liver / Hepatic Disorder Evaluation"],
            "risk_level": "Moderate",
            "doctor": doc,
            "recommendation": rec
        }

    # 6. Brain Stroke & Neurological Symptoms
    if any(w in t for w in ["stroke", "brain stroke", "paralysis", "slurred", "numbness", "weakness on one side", "facial droop", "బ్రెయిన్ స్ట్రోక్", "పక్షవాతం", "लकवा", "ब्रेन स्ट्रोक"]):
        if language == "te":
            reply = (
                "🧠 **బ్రెయిన్ స్ట్రోక్ & న్యూరోలాజికల్ హెచ్చరిక (Stroke Warning):**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** మెదడుకు రక్తప్రసరణ ఆగిపోవడం వల్ల స్ట్రోక్ వస్తుంది. దీనికి తక్షణ చికిత్స అవసరం.\n"
                "• **FAST సూత్రం:** F - ముఖం వంకరపోవడం, A - చేయి బలహీనత, S - మాట తడబడటం, T - వెంటనే 108 కు కాల్ చేయడం.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** న్యూరోలాజికల్ స్ట్రోక్ రిస్క్ ప్రొఫైల్.\n"
                "• **సిఫార్సు:** అత్యవసరమైతే వెంటనే ఆసుపత్రికి వెళ్ళండి. నివారణ అంచనా కోసం **Brain Stroke Predictor** ఉపయోగించండి."
            )
            doc = "న్యూరాలజిస్ట్ / అత్యవసర వైద్యులు"
            rec = "లక్షణాలు ఉంటే వెంటనే సమీప స్ట్రోక్ సెంటర్ లేదా 108 ను సంప్రదించండి."
        elif language == "hi":
            reply = (
                "🧠 **ब्रेन स्ट्रोक और न्यूरोलॉजिकल मूल्यांकन (Stroke Assessment):**\n\n"
                "• **बुनियादी जानकारी (Basics):** मस्तिष्क में रक्त संचार बाधित होने से स्ट्रोक होता है। इसमें हर मिनट महत्वपूर्ण होता है।\n"
                "• **FAST नियम:** F - चेहरे का टेढ़ा होना, A - एक तरफ हाथ में कमजोरी, S - बोलने में लड़खड़ाहट, T - तुरंत 108 पर कॉल करना।\n"
                "• **रोग भविष्यवाणी (Prediction):** सेरेब्रोवास्कुलर स्ट्रोक जोखिम।\n"
                "• **सुझाव:** आपातकाल में तुरंत अस्पताल जाएं या हमारे **Brain Stroke Predictor** से जांच करें।"
            )
            doc = "न्यूरोलॉजिस्ट / आपातकालीन चिकित्सक"
            rec = "यदि लक्षण तीव्र हैं, तो तुरंत 108 पर कॉल करें और मस्तिष्क का MRI/CT स्कैन करवाएं।"
        else:
            reply = (
                "🧠 **Brain Stroke & Neurological Triage Overview:**\n\n"
                "• **Condition Basics:** An ischemic stroke occurs when cerebral blood supply is interrupted, leading to rapid cellular hypoxia. Transient Ischemic Attacks (TIAs) serve as critical precursor warnings.\n"
                "• **FAST Warning Signs:**\n"
                "  - **F (Face):** Unilateral facial droop or numbness.\n"
                "  - **A (Arms):** Sudden weakness or inability to raise one arm.\n"
                "  - **S (Speech):** Slurred speech, difficulty finding words, or comprehension loss.\n"
                "  - **T (Time):** Immediate emergency dispatch (Call 108 / 112).\n"
                "• **Diagnostic Prediction:** Cerebrovascular / Ischemic Stroke Risk Profile.\n\n"
                "💡 *QuantumMedAI Recommendation:* If acute, dial 108 immediately. For baseline risk evaluation, use our **Brain Stroke Predictor** calculator."
            )
            doc = "Neurologist / Emergency Physician"
            rec = "Urgent Neuro-evaluation, Brain CT/MRI scan, and Carotid Doppler."

        return {
            "ai_reply": reply,
            "is_emergency": any(w in t for w in ["sudden", "face droop", "slurred", "paralysis"]),
            "matched_keywords": ["Neurological Markers", "Stroke FAST"],
            "detected_diseases": ["Brain Stroke Risk Assessment"],
            "risk_level": "High",
            "doctor": doc,
            "recommendation": rec
        }

    # 7. PCOS / PCOD & Women's Hormonal Health
    if any(w in t for w in ["pcos", "pcod", "period", "menstrual", "ovarian", "cramps", "facial hair", "hirsutism", "irregular period", "పీసీఓఎస్", "పీసీఓడీ", "పీరియడ్స్", "माहवारी"]):
        if language == "te":
            reply = (
                "🌸 **PCOS / PCOD మరియు హార్మోన్ల ఆరోగ్య విశ్లేషణ:**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** PCOS/PCOD అనేది హార్మోన్ల అసమతుల్యత (ఆండ్రోజెన్లు పెరగడం మరియు ఇన్సులిన్ రెసిస్టెన్స్) వల్ల వచ్చే రుగ్మత.\n"
                "• **లక్షణాలు:** క్రమం తప్పిన పీరియడ్స్, మొటిమలు, ముఖంపై అవాంఛిత రోమాలు, బరువు పెరగడం, అండాశయంలో తిత్తులు.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** ఎండోక్రైన్ PCOS / PCOD హార్మోనల్ ప్రొఫైల్.\n"
                "• **సంరక్షణ:** తక్కువ గ్లైసెమిక్ (Low-GI) ఆహారం, రోజూ వ్యాయామం, ఒత్తిడి తగ్గించుకోవడం.\n"
                "• **సిఫార్సు:** మా **🩺 Disease Predictors** లోని **PCOS & PCOD Predictors** ను ఉపయోగించండి."
            )
            doc = "గైనకాలజిస్ట్ / ఎండోక్రైనాలజిస్ట్"
            rec = "పెల్విక్ అల్ట్రాసౌండ్ స్కాన్ మరియు హార్మోన్ ప్రొఫైల్ (FSH, LH, AMH, థైరాయిడ్) పరీక్షించండి."
        elif language == "hi":
            reply = (
                "🌸 **PCOS / PCOD और हार्मोनल स्वास्थ्य मूल्यांकन:**\n\n"
                "• **बुनियादी जानकारी (Basics):** पीसीओएस/पीसीओडी हार्मोनल असंतुलन और इंसुलिन प्रतिरोध के कारण होता है।\n"
                "• **प्रमुख लक्षण:** अनियमित मासिक धर्म, चेहरे पर अनचाहे बाल (हिर्सुटिज़्म), मुंहासे, अचानक वजन बढ़ना।\n"
                "• **रोग भविष्यवाणी (Prediction):** पॉलीसिस्टिक ओवरी सिंड्रोम (PCOS) प्रोफाइल।\n"
                "• **घरेलू देखभाल:** कम चीनी व फाइबर युक्त भोजन लें, प्रतिदिन 30 मिनट योग या व्यायाम करें।\n"
                "• **सुझाव:** सटीक जोखिम जानने के लिए हमारे **PCOS Predictor** का उपयोग करें।"
            )
            doc = "स्त्री रोग विशेषज्ञ (Gynecologist) / एंडोक्रिनोलॉजिस्ट"
            rec = "पेल्विक अल्ट्रासाउंड और हार्मोनल प्रोफाइल (LH, FSH, Testosterone) करवाएं।"
        else:
            reply = (
                "🌸 **PCOS / PCOD & Endocrine Health Overview:**\n\n"
                "• **Condition Basics:** Polycystic Ovary Syndrome (PCOS) is a complex endocrine disorder characterized by hyperandrogenism, ovulatory dysfunction, and insulin resistance.\n"
                "• **Key Symptoms:** Oligomenorrhea (irregular or absent periods), hirsutism (excess facial/body hair), persistent cystic acne, unexplained central adiposity, and pelvic aching.\n"
                "• **Diagnostic Prediction:** Polycystic Ovarian Endocrine Risk Profile.\n"
                "• **Supportive Lifestyle Actions:**\n"
                "  - Adopt a low-glycemic index (Low-GI), anti-inflammatory diet.\n"
                "  - Perform 30–45 minutes of strength and aerobic exercise 4–5 times weekly.\n"
                "  - Optimize sleep patterns to regulate cortisol and insulin sensitivity.\n\n"
                "💡 *QuantumMedAI Recommendation:* Check your personalized clinical indicators using our **PCOS & PCOD Predictors** in the Disease Predictors tab."
            )
            doc = "Gynecologist / Endocrinologist"
            rec = "Schedule a Pelvic Ultrasound (USG) and comprehensive Hormone Profile (FSH, LH, DHEA-S, Total Testosterone, AMH)."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Endocrine Indicators", "PCOS / PCOD", "Menstrual Cycle"],
            "detected_diseases": ["PCOS / PCOD Endocrine Risk Profile"],
            "risk_level": "Moderate",
            "doctor": doc,
            "recommendation": rec
        }

    # 8. Diabetes, High Blood Sugar & Metabolic Health
    if any(w in t for w in ["diabetes", "sugar", "glucose", "hba1c", "insulin", "thirst", "frequent urination", "డయాబెటిస్", "షుగర్", "మధుమేహం", "मधुमेह"]):
        if language == "te":
            reply = (
                "🍬 **డయాబెటిస్ & రక్తంలో చక్కెర స్థాయిల విశ్లేషణ:**\n\n"
                "• **ప్రాథమిక సమాచారం (Basics):** ఇన్సులిన్ సరిగ్గా పనిచేయకపోవడం వల్ల రక్తంలో గ్లూకోజ్ స్థాయిలు పెరుగుతాయి (టైప్-2 డయాబెటిస్).\n"
                "• **లక్షణాలు:** ఎక్కువ దాహం వేయడం, తరచుగా మూత్రవిసర్జన, విపరీతమైన ఆకలి, గాయాలు త్వరగా మానకపోవడం, కంటిచూపు మందగించడం.\n"
                "• **ప్రాథమిక అంచనా (Disease Prediction):** ప్రీ-డయాబెటిస్ లేదా డయాబెటిస్ మెల్లిటస్ ప్రొఫైల్.\n"
                "• **సంరక్షణ:** తీపి పదార్థాలు మానేయండి, తృణధాన్యాలు తీసుకోండి, రోజూ నడవండి.\n"
                "• **సిఫార్సు:** ఫాస్టింగ్ బ్లడ్ షుగర్ మరియు HbA1c పరీక్షలు చేయించుకోండి."
            )
            doc = "ఎండోక్రైనాలజిస్ట్ / డయాబెటాలజిస్ట్"
            rec = "Fasting Blood Sugar (FBS), Post-Prandial (PPBS), మరియు HbA1c పరీక్షలు చేయించుకోండి."
        elif language == "hi":
            reply = (
                "🍬 **मधुमेह (Diabetes) और ब्लड शुगर मूल्यांकन:**\n\n"
                "• **बुनियादी जानकारी (Basics):** शरीर में इंसुलिन का उत्पादन कम होने या इंसुलिन रेजिस्टेंस के कारण ब्लड शुगर बढ़ता है।\n"
                "• **प्रमुख लक्षण:** अत्यधिक प्यास लगना, बार-बार पेशाब आना, थकान, घाव देर से भरना, धुंधला दिखना।\n"
                "• **रोग भविष्यवाणी (Prediction):** संभावित प्रीडायबिटीज / टाइप-2 डायबिटीज।\n"
                "• **घरेलू देखभाल:** मीठा और मैदा बंद करें, फाइबर युक्त आहार लें, नियमित व्यायाम करें।\n"
                "• **सुझाव:** खाली पेट ब्लड शुगर और HbA1c टेस्ट करवाएं।"
            )
            doc = "एंडोक्रिनोलॉजिस्ट / डायबेटोलॉजिस्ट"
            rec = "Fasting Blood Glucose और HbA1c टेस्ट करवाएं।"
        else:
            reply = (
                "🍬 **Diabetes Mellitus & Glycemic Health Overview:**\n\n"
                "• **Condition Basics:** Diabetes occurs when the pancreas produces insufficient insulin or peripheral tissues develop insulin resistance, leading to chronic hyperglycemia.\n"
                "• **Key Symptoms:** Polydipsia (excessive thirst), polyuria (frequent urination), polyphagia (constant hunger), blurred vision, unexplained weight loss, and slow-healing wounds.\n"
                "• **Diagnostic Prediction:** Pre-Diabetes / Type-2 Diabetes Glycemic Profile.\n"
                "• **Supportive Lifestyle Actions:**\n"
                "  - Limit simple carbohydrates, sugary drinks, and ultra-processed items.\n"
                "  - Emphasize high-fiber vegetables, whole grains, and lean proteins.\n"
                "  - Walk for 15 minutes after main meals to blunt post-prandial glycemic spikes.\n\n"
                "💡 *QuantumMedAI Recommendation:* Check your metabolic indicators and BMI in our Disease Predictors suite."
            )
            doc = "Endocrinologist / Diabetologist"
            rec = "Get Fasting Blood Sugar (FBS), Post-Prandial Blood Sugar (PPBS), and HbA1c testing."

        return {
            "ai_reply": reply,
            "is_emergency": False,
            "matched_keywords": ["Glycemic Biomarkers", "Diabetes", "HbA1c"],
            "detected_diseases": ["Diabetes Mellitus / Glycemic Dysregulation"],
            "risk_level": "Moderate",
            "doctor": doc,
            "recommendation": rec
        }

    # 9. Thyroid Disorders (Hypothyroidism / Hyperthyroidism)
    if any(w in t for w in ["thyroid", "hypothyroid", "hyperthyroid", "tsh", "t3", "t4", "goiter", "థైరాయిడ్", "थायराइड"]):
        return {
            "ai_reply": (
                "🦋 **Thyroid Function & Endocrine Assessment:**\n\n"
                "• **Condition Basics:** The thyroid gland regulates whole-body metabolism, thermogenesis, and heart rate through T3 and T4 hormones.\n"
                "• **Hypothyroid Signs:** Weight gain despite normal appetite, extreme cold sensitivity, dry skin, constipation, and hair loss.\n"
                "• **Hyperthyroid Signs:** Rapid heart rate, heat intolerance, tremor, unintended weight loss, and restlessness.\n"
                "• **Diagnostic Prediction:** Thyroid Endocrine Dysfunction Profile.\n"
                "• **Next Steps:** Obtain a comprehensive Serum Thyroid Panel (TSH, Free T3, Free T4) and consult an Endocrinologist."
            ),
            "is_emergency": False,
            "matched_keywords": ["Thyroid Hormones", "TSH", "Endocrine"],
            "detected_diseases": ["Thyroid Dysfunction Profile"],
            "risk_level": "Low" if "mild" in t else "Moderate",
            "doctor": "Endocrinologist",
            "recommendation": "Check Serum TSH, Free T3, and Free T4 levels."
        }

    # 10. Respiratory, Asthma & Chronic Cough
    if any(w in t for w in ["asthma", "wheezing", "cough", "bronchitis", "pneumonia", "breath", "dammam", "ఆయాసం", "దగ్గు", "खांसी", "दमा"]):
        return {
            "ai_reply": (
                "🫁 **Respiratory & Pulmonary Health Assessment:**\n\n"
                "• **Condition Basics:** Respiratory tract symptoms stem from airway inflammation, bronchospasm (asthma), or viral/bacterial infections (bronchitis/pneumonia).\n"
                "• **Key Symptoms:** Wheezing sound while breathing out, persistent dry or productive cough, chest tightness, and shortness of breath during exertion.\n"
                "• **Diagnostic Prediction:** Bronchial Asthma / Respiratory Infection Profile.\n"
                "• **Supportive Actions:**\n"
                "  - Practice steam inhalation twice daily and stay in well-ventilated environments.\n"
                "  - Avoid allergen triggers (dust, smoke, cold air, pet dander).\n"
                "  - Use prescribed inhalers as directed by your physician.\n\n"
                "⚠️ *Warning: Seek emergency care immediately if you experience severe shortness of breath or blue lips.*"
            ),
            "is_emergency": "severe breath" in t or "can't breathe" in t,
            "matched_keywords": ["Pulmonary Airway", "Wheezing", "Cough"],
            "detected_diseases": ["Bronchial Asthma / Pulmonary Condition"],
            "risk_level": "High" if "severe" in t else "Moderate",
            "doctor": "Pulmonologist / Chest Physician",
            "recommendation": "Consult a Pulmonologist for Spirometry (Pulmonary Function Test) and Chest X-ray."
        }

    # 11. Infectious Tropical Fevers: Dengue, Malaria, Typhoid
    if any(w in t for w in ["dengue", "malaria", "typhoid", "chills", "platelet", "డెంగ్యూ", "మలేరియా", "టైఫాయిడ్", "डेंगू", "मलेरिया"]):
        return {
            "ai_reply": (
                "🦟 **Tropical & Infectious Fever Assessment:**\n\n"
                "• **Condition Basics:** Vector-borne and bacterial infections (Dengue, Malaria, Typhoid) cause acute systemic inflammation, high fever, and hematological shifts (platelet drops).\n"
                "• **Key Symptoms:** Sudden high-grade fever with shaking chills, severe retro-orbital (behind eyes) pain, joint/muscle aches, and rash.\n"
                "• **Diagnostic Prediction:** Tropical Infection / Dengue / Malaria Evaluation.\n"
                "• **Supportive Home Care:**\n"
                "  - Maintain aggressive oral hydration (ORS, coconut water, soups).\n"
                "  - Avoid aspirin and ibuprofen which can increase bleeding risk.\n"
                "  - Get a Complete Blood Count (CBC) to monitor platelet counts every 24 hours."
            ),
            "is_emergency": "bleeding" in t or "low platelet" in t,
            "matched_keywords": ["Tropical Fever", "Platelets", "Infection"],
            "detected_diseases": ["Dengue / Malaria / Typhoid Fever Profile"],
            "risk_level": "High",
            "doctor": "General Physician / Infectious Disease Specialist",
            "recommendation": "Get CBC (Complete Blood Picture), Dengue NS1/IgM, and Malaria Rapid Test immediately."
        }

    # 12. Gastrointestinal & Acid Reflux / Ulcers
    if any(w in t for w in ["acidity", "acid reflux", "gerd", "heartburn", "ulcer", "gastritis", "stomach pain", "nausea", "vomit", "కడుపు నొప్పి", "ఎసిడిటీ", "गैस", "पेट दर्द"]):
        return {
            "ai_reply": (
                "🍽️ **Gastrointestinal & Digestive Health Overview:**\n\n"
                "• **Condition Basics:** Acidity, GERD, and gastritis occur when stomach acid irritates the esophageal lining or gastric mucosa due to delayed emptying, diet, or H. pylori.\n"
                "• **Key Symptoms:** Burning sensation in chest/upper abdomen, acid regurgitation, bloating, nausea, and discomfort after meals.\n"
                "• **Supportive Home Care:**\n"
                "  - Eat smaller, frequent meals and avoid lying down for 2 hours post-meal.\n"
                "  - Eliminate spicy, oily, caffeinated, and deeply acidic foods.\n"
                "  - Sip warm chamomile or ginger water for soothing digestion."
            ),
            "is_emergency": False,
            "matched_keywords": ["Gastrointestinal", "Acid Reflux", "Gastritis"],
            "detected_diseases": ["GERD / Gastritis / Peptic Discomfort"],
            "risk_level": "Low" if "mild" in t else "Moderate",
            "doctor": "Gastroenterologist / General Physician",
            "recommendation": "Adopt bland diet, avoid lying flat after meals, and consult a doctor if pain persists."
        }

    # 13. Orthopedic, Arthritis & Joint Pain
    if any(w in t for w in ["joint pain", "arthritis", "knee pain", "uric acid", "gout", "back pain", "నొప్పులు", "కీళ్ల నొప్పులు", "जोड़ों का दर्द", "गठिया"]):
        return {
            "ai_reply": (
                "🦴 **Joint Health, Arthritis & Musculoskeletal Assessment:**\n\n"
                "• **Condition Basics:** Joint pain and stiffness often indicate Osteoarthritis (cartilage wear), Rheumatoid Arthritis (autoimmune inflammation), or Gout (uric acid crystals).\n"
                "• **Key Symptoms:** Joint swelling, morning stiffness lasting >30 minutes, cracking sounds, and restricted mobility.\n"
                "• **Supportive Home Care:**\n"
                "  - Apply warm compresses for chronic stiffness or cold packs for acute swelling.\n"
                "  - Low-impact exercises like swimming and gentle stretching.\n"
                "  - Restrict high-purine foods (red meat, seafood) if uric acid is elevated."
            ),
            "is_emergency": False,
            "matched_keywords": ["Musculoskeletal", "Joint Pain", "Uric Acid"],
            "detected_diseases": ["Arthritis / Musculoskeletal Evaluation"],
            "risk_level": "Low" if "mild" in t else "Moderate",
            "doctor": "Orthopedic Specialist / Rheumatologist",
            "recommendation": "Check Serum Uric Acid, ESR, CRP, and X-ray of affected joints."
        }

    # 14. Anemia & Blood Deficiency
    if any(w in t for w in ["anemia", "hemoglobin", "low hb", "pale", "dizzy", "fatigue", "రక్తహీనత", "ఎనీమియా", "खून की कमी"]):
        return {
            "ai_reply": (
                "🩸 **Hematological & Anemia Assessment:**\n\n"
                "• **Condition Basics:** Anemia occurs when blood lacks sufficient healthy red blood cells or hemoglobin to carry adequate oxygen throughout tissues.\n"
                "• **Key Symptoms:** Chronic fatigue, pale skin, dizziness upon standing, cold hands and feet, and brittle nails.\n"
                "• **Supportive Actions:** Increase iron-rich foods (spinach, beetroot, lentils, dates, pomegranate) alongside Vitamin C to enhance absorption."
            ),
            "is_emergency": False,
            "matched_keywords": ["Hematological", "Hemoglobin", "Iron Deficiency"],
            "detected_diseases": ["Iron Deficiency Anemia Profile"],
            "risk_level": "Moderate",
            "doctor": "Hematologist / General Physician",
            "recommendation": "Get Complete Blood Picture (CBP), Serum Ferritin, and Iron profile."
        }

    # 15. General Multi-Symptom Pattern Matching Engine
    # For any general question or symptom description not explicitly matching above
    found_symptoms = []
    for sym, category in [
        ("fever", "Febrile Illness"), ("headache", "Cranial Discomfort"), ("pain", "Somatic Discomfort"),
        ("vomit", "Gastric Distress"), ("swelling", "Edema / Inflammation"), ("fatigue", "Systemic Fatigue"),
        ("rash", "Dermatological"), ("dizzy", "Equilibrium Shift"), ("cough", "Respiratory"),
        ("weakness", "Malaise"), ("infection", "Infectious Pathology"), ("sweat", "Autonomic Signs")
    ]:
        if sym in t:
            found_symptoms.append(category)

    if not found_symptoms:
        found_symptoms = ["Clinical Inquiry"]

    if language == "te":
        reply = (
            f"🩺 **వైద్య విశ్లేషణ మరియు ప్రాథమిక అంచనా (Clinical Assessment):**\n\n"
            f"మీరు వివరించిన లక్షణాలు: **{text}**\n\n"
            "• **ప్రాథమిక సమాచారం (Basics):** ఈ రకమైన లక్షణాలు శరీరంలో తాపజనక ప్రతిస్పందన, రోగనిరోధక చర్య లేదా జీవక్రియల అసమతుల్యత వల్ల సంభవించవచ్చు.\n"
            "• **ప్రాథమిక అంచనా (Disease Prediction):** ప్రాథమిక క్లినికల్ ప్రొఫైల్ - క్రమం తప్పకుండా పర్యవేక్షించవలసిన పరిస్థితి.\n"
            "• **స్వీయ సంరక్షణ సలహాలు:**\n"
            "  - పుష్కలంగా నీరు మరియు ద్రవపదార్థాలు తీసుకోండి.\n"
            "  - శరీరానికి తగినంత విశ్రాంతి ఇవ్వండి.\n"
            "  - శరీర ఉష్ణోగ్రత మరియు రక్తపోటును గమనించండి.\n\n"
            "• **ముఖ్య సూచన:** సమస్య కొనసాగితే లేదా తీవ్రమైతే వెంటనే వైద్యుడిని సంప్రదించండి. మా **🩺 Disease Predictors** ట్యాబ్‌లోని కాలిక్యులేటర్లను కూడా ఉపయోగించవచ్చు."
        )
        doc = "జనరల్ ఫిజీషియన్ (సాధారణ వైద్యులు)"
        rec = "తగినంత విశ్రాంతి తీసుకోండి, పుష్కలంగా నీరు త్రాగండి మరియు వైద్యుడిని సంప్రదించండి."
    elif language == "hi":
        reply = (
            f"🩺 **चिकित्सीय मूल्यांकन एवं रोग भविष्यवाणी (Clinical Assessment):**\n\n"
            f"आपके द्वारा बताए गए लक्षण: **{text}**\n\n"
            "• **बुनियादी जानकारी (Basics):** इस प्रकार के लक्षण संक्रमण, सूजन या चयापचय में बदलाव के कारण हो सकते हैं।\n"
            "• **रोग भविष्यवाणी (Prediction):** प्राथमिक स्वास्थ्य मूल्यांकन प्रोफ़ाइल।\n"
            "• **प्राथमिक देखभाल:**\n"
            "  - पर्याप्त मात्रा में पानी और तरल पदार्थ पिएं।\n"
            "  - भरपूर आराम करें।\n"
            "  - शरीर के तापमान और लक्षणों पर नज़र रखें।\n\n"
            "• **सुझाव:** यदि लक्षण 24-48 घंटों से अधिक बने रहते हैं, तो डॉक्टर से सलाह लें या हमारे **Disease Predictors** का उपयोग करें।"
        )
        doc = "सामान्य चिकित्सक (General Physician)"
        rec = "आराम करें, पानी पिएं और सामान्य चिकित्सक से परामर्श लें।"
    else:
        reply = (
            f"🩺 **Clinical Evaluation & Disease Prediction Overview:**\n\n"
            f"**Reported Concern / Symptoms:** \"{text}\"\n\n"
            "• **Clinical Basics:** The symptom cluster you described typically reflects an inflammatory response, physiological metabolic shift, or localized bodily strain.\n"
            "• **Preliminary Diagnostic Prediction:** General Medical Evaluation Profile.\n"
            "• **Recommended Clinical Workup:** Complete Blood Count (CBC), Basic Metabolic Panel, and vitals monitoring.\n"
            "• **Supportive Home Care:**\n"
            "  - Maintain optimal hydration with water and electrolyte broths.\n"
            "  - Ensure 7–8 hours of restful sleep and avoid physical overexertion.\n"
            "  - Monitor any changes in temperature, pain intensity, or respiration.\n\n"
            "💡 *QuantumMedAI Recommendation:* You can run dedicated precision assessments in our **🩺 Disease Predictors** tab (Heart, Kidney, Liver, Stroke, PCOS, BMI) or consult a General Physician."
        )
        doc = "General Physician"
        rec = "Hydrate, rest, monitor symptoms, and consult a General Physician for clinical evaluation."

    return {
        "ai_reply": reply,
        "is_emergency": False,
        "matched_keywords": found_symptoms,
        "detected_diseases": ["Clinical Symptom Assessment Profile"],
        "risk_level": "Low" if "mild" in t else "Moderate",
        "doctor": doc,
        "recommendation": rec
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
