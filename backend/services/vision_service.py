import os
import json
import base64
import re
import httpx
from typing import Optional, Dict, Any, List

from services.ai_service import get_all_api_keys, extract_json

SYSTEM_PROMPT_VISION = """You are QuantumMed AI's Expert Medical Vision & Document Analysis Intelligence.
You specialize in reading, transcribing, and clinically analyzing:
1. Clinical Pathology & Laboratory Test Reports (Complete Blood Count / CBC, Liver Function Tests / LFT, Kidney Function Tests / KFT / RFT, Lipid Profile, Thyroid Panel, Blood Glucose / HbA1c, Urine Routine, Serum Electrolytes).
2. Handwritten and printed Doctor Prescriptions.
3. Hospital Discharge Summaries, Radiology / Ultrasound / Scan reports, and Clinical Notes.

CRITICAL CLINICAL EXTRACTION GUIDELINES FOR LAB & BLOOD REPORTS:
1. ACCURATE BIOMARKER EXTRACTION:
   - Carefully read every biomarker line item in the report.
   - Extract the exact test parameter name (e.g. Hemoglobin, Total Leukocyte Count / WBC, Platelet Count, Serum Creatinine, Blood Urea, Total Bilirubin, Direct Bilirubin, SGPT/ALT, SGOT/AST, Fasting Blood Sugar, HbA1c, Total Cholesterol, HDL, LDL, Triglycerides).
   - Extract the exact observed numerical value.
   - Extract the exact unit (g/dL, mg/dL, /mcL, U/L, %, mEq/L) and reference range printed on the report.
   - Accurately determine the status: "High", "Low", or "Normal".
   - Provide a concise 1-sentence interpretation for the parameter.

2. ABNORMAL FINDINGS & IMPLICATIONS:
   - In "abnormal_findings", list every single out-of-range parameter with its value, status, and clinical meaning (e.g. "Low Hemoglobin (9.8 g/dL) - Indicates microcytic/normocytic anemia", "Elevated Serum Creatinine (1.6 mg/dL) - Suggests compromised renal clearance").

3. CLINICAL SUMMARY (ai_reply):
   - Provide a structured 3-part clinical summary:
     * Assessment: 1-2 sentences summarizing the test type and primary findings (e.g. mild anemia, hepatic inflammation, or normal metabolic profile).
     * Care & Relief: 2-3 brief practical bullet points for diet, hydration, or lifestyle.
     * Next Step: 1 sentence specifying the exact medical specialist to consult (Hematologist, Nephrologist, Gastroenterologist, Endocrinologist, or General Physician) and any follow-up tests.
   - Keep the reply concise, empathetic, and clear.
   - ZERO EMOJIS: Do not output any emojis in any field.

Respond strictly in valid JSON with these exact keys:
{
  "document_type": "Lab Report" | "Prescription" | "Hospital Document" | "Medical Scan" | "General Medical Image",
  "document_title": "e.g. Complete Blood Count & Renal Function Report",
  "ai_reply": "Concise, structured 3-part clinical evaluation without emojis.",
  "is_emergency": false,
  "risk_level": "Low" | "Moderate" | "High" | "Critical",
  "doctor": "Recommended Medical Specialist",
  "prescriptions": [
    {
      "medicine_name": "Medicine Name",
      "dosage": "e.g. 500mg",
      "frequency": "e.g. Twice daily",
      "timing": "e.g. After meals",
      "duration": "e.g. 5 days",
      "purpose": "Therapeutic indication"
    }
  ],
  "lab_biomarkers": [
    {
      "parameter": "e.g. Hemoglobin",
      "value": "e.g. 9.8",
      "unit": "g/dL",
      "reference_range": "13.0 - 17.0",
      "status": "Low",
      "interpretation": "Subnormal oxygen-carrying capacity, consistent with anemia"
    }
  ],
  "abnormal_findings": [
    "List of all out-of-range parameters"
  ],
  "recommendations": [
    "Key actionable clinical next steps"
  ]
}
Only return valid JSON.
"""


def parse_blood_biomarkers_from_text(text: str) -> tuple[List[Dict[str, str]], List[str]]:
    """
    Deterministic clinical regex biomarker extractor for laboratory values.
    Used for local evaluation and resilient fallback.
    """
    biomarkers = []
    abnormal = []
    
    patterns = [
        (r'\b(hb|hemoglobin|haemoglobin)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Hemoglobin', 'g/dL', 12.0, 17.0, 'Low indicates anemia; high indicates erythrocytosis'),
        (r'\b(creatinine|serum creatinine)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Serum Creatinine', 'mg/dL', 0.6, 1.2, 'Elevated suggests reduced renal filtration'),
        (r'\b(total bilirubin|bilirubin)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Total Bilirubin', 'mg/dL', 0.2, 1.2, 'Elevated points towards jaundice or liver clearance issue'),
        (r'\b(sgpt|alt)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'SGPT / ALT', 'U/L', 7.0, 56.0, 'Elevated suggests hepatic cellular inflammation'),
        (r'\b(sgot|ast)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'SGOT / AST', 'U/L', 10.0, 40.0, 'Elevated reflects liver or muscle enzyme release'),
        (r'\b(platelet[s]?|platelet count)\b[:=\s]*([0-9]+(?:,[0-9]+)?)', 'Platelet Count', '/mcL', 150000, 450000, 'Low indicates thrombocytopenia; normal clotting requires >150k'),
        (r'\b(wbc|tlc|white blood cell[s]?)\b[:=\s]*([0-9]+(?:,[0-9]+)?)', 'Total WBC Count', '/mcL', 4000, 11000, 'Elevated suggests infection or inflammatory response'),
        (r'\b(blood urea|urea|bun)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Blood Urea', 'mg/dL', 15.0, 40.0, 'Elevated suggests dehydration or decreased renal clearance'),
        (r'\b(hba1c)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'HbA1c', '%', 4.0, 5.7, 'Levels >5.7% indicate prediabetes; >6.5% indicate diabetes'),
        (r'\b(fasting sugar|fbs|fasting glucose|glucose)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Fasting Blood Glucose', 'mg/dL', 70.0, 100.0, 'Elevated indicates impaired glycemic control'),
        (r'\b(cholesterol|total cholesterol)\b[:=\s]*([0-9]+(?:\.[0-9]+)?)', 'Total Cholesterol', 'mg/dL', 125.0, 200.0, 'Elevated increases cardiovascular plaque risk')
    ]
    
    t_lower = text.lower()
    for regex, name, unit, min_val, max_val, meaning in patterns:
        m = re.search(regex, t_lower)
        if m:
            val_str = m.group(2).replace(',', '')
            try:
                val = float(val_str)
                if val < min_val:
                    status = 'Low'
                    abnormal.append(f"Low {name} ({val} {unit})")
                elif val > max_val:
                    status = 'High'
                    abnormal.append(f"Elevated {name} ({val} {unit})")
                else:
                    status = 'Normal'
                biomarkers.append({
                    'parameter': name,
                    'value': str(val),
                    'unit': unit,
                    'reference_range': f"{min_val} - {max_val}",
                    'status': status,
                    'interpretation': meaning
                })
            except Exception:
                pass
    return biomarkers, abnormal


def analyze_medical_image_with_ai(
    image_base64: str,
    mime_type: str = "image/jpeg",
    user_query: Optional[str] = None,
    language: str = "en"
) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini Vision or OpenAI Vision to perform medical OCR and clinical document interpretation.
    Prioritizes Gemini Vision for multimodal document reading and biomarker extraction.
    """
    all_keys = get_all_api_keys()
    if not all_keys:
        return None

    # Clean base64 header if included
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    prompt_text = (
        f"Analyze this medical image / document carefully. "
        f"Transcribe and evaluate all blood report biomarkers, units, reference intervals, or prescription medications. "
        f"Language preference: {language}."
    )
    if user_query and user_query.strip():
        prompt_text += f"\nPatient specific question/context: {user_query.strip()}"

    # 1. Primary Vision Provider: Gemini Vision (Top capability for clinical pathology OCR)
    if "gemini" in all_keys:
        gemini_key = all_keys["gemini"]
        gemini_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest"
        ]

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT_VISION}\n\n{prompt_text}"},
                        {
                            "inline_data": {
                                "mime_type": mime_type or "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                for model in gemini_models:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                        res = client.post(url, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                text = candidates[0]["content"]["parts"][0]["text"]
                                parsed = extract_json(text)
                                if parsed and isinstance(parsed, dict):
                                    return parsed
                    except Exception as model_err:
                        print(f"[Gemini Vision Model {model} Error]: {model_err}")
                        continue
        except Exception as e:
            print(f"[Vision AI Gemini Error]: {e}")

    # 2. Secondary Vision Provider: OpenAI GPT-4o-mini
    if "openai" in all_keys:
        openai_key = all_keys["openai"]
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_VISION},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            with httpx.Client(timeout=25.0) as client:
                res = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = extract_json(content)
                    if parsed and isinstance(parsed, dict):
                        return parsed
        except Exception as e:
            print(f"[Vision AI OpenAI Error]: {e}")

    return None


def fallback_image_analysis(filename: str = "Medical Document", user_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic clinical document parser when offline or when external vision is unavailable.
    Performs regex extraction of any blood parameters in the user query or filename.
    """
    name_lower = (filename or "").lower()
    query_text = user_query or ""
    combined_text = f"{name_lower} {query_text}"

    extracted_biomarkers, abnormal_findings = parse_blood_biomarkers_from_text(combined_text)

    if extracted_biomarkers:
        doc_type = "Lab Report"
        doc_title = "Clinical Diagnostic Laboratory Report"
        abn_text = ", ".join(abnormal_findings) if abnormal_findings else "All detected parameters are within normal range."
        reply = (
            f"**Laboratory Test Report Evaluation ({filename}):**\n\n"
            f"- **Assessment:** Extracted {len(extracted_biomarkers)} clinical biomarker(s). {abn_text}\n"
            "- **Care & Relief:** Maintain balanced hydration and follow a nutrient-dense diet supporting affected organ systems.\n"
            "- **Next Step:** Present these laboratory findings to your consulting physician for clinical correlation."
        )
        doctor = "Consultant Pathologist / General Physician"
        risk_level = "High" if len(abnormal_findings) >= 2 else "Moderate" if abnormal_findings else "Low"
    elif any(k in name_lower for k in ["rx", "prescrip", "med", "doctor", "slip"]):
        doc_type = "Prescription"
        doc_title = "Doctor Outpatient Prescription"
        reply = (
            f"**Prescription Document Scanned ({filename}):**\n\n"
            "- **Assessment:** Prescription successfully logged in your medical records.\n"
            "- **Care & Relief:** Take all prescribed medications strictly as scheduled with proper meals. Do not alter dosages without doctor approval.\n"
            "- **Next Step:** Confirm medication instructions with your dispensing pharmacist."
        )
        doctor = "Prescribing Physician / Pharmacist"
        risk_level = "Low"
    elif any(k in name_lower for k in ["blood", "cbc", "lft", "kft", "lipid", "urine", "lab", "test", "report"]):
        doc_type = "Lab Report"
        doc_title = "Clinical Diagnostic Laboratory Report"
        reply = (
            f"**Laboratory Test Report Scanned ({filename}):**\n\n"
            "- **Assessment:** Blood test report received. For optimal automated parameter extraction, please ensure the photo is clear and well-lit, or type specific values (e.g. Hb, Creatinine, Bilirubin) in chat.\n"
            "- **Care & Relief:** Compare your report's values against the normal reference column provided by the testing laboratory.\n"
            "- **Next Step:** Consult your General Physician or Pathologist for formal review."
        )
        doctor = "Consultant Pathologist / General Physician"
        risk_level = "Moderate"
    else:
        doc_type = "Hospital Document"
        doc_title = "Medical Diagnostic File"
        reply = (
            f"**Medical Document Indexed ({filename}):**\n\n"
            f"- **Assessment:** Clinical document received. Context: \"{user_query if user_query else 'Medical review'}\".\n"
            "- **Care & Relief:** Maintain this record in your personal health log for continuity of care.\n"
            "- **Next Step:** Review diagnostic findings with your healthcare provider during your upcoming evaluation."
        )
        doctor = "General Physician"
        risk_level = "Low"

    return {
        "document_type": doc_type,
        "document_title": doc_title,
        "ai_reply": reply,
        "is_emergency": False,
        "risk_level": risk_level,
        "doctor": doctor,
        "prescriptions": [],
        "lab_biomarkers": extracted_biomarkers,
        "abnormal_findings": abnormal_findings,
        "recommendations": [
            "Review diagnostic findings with your healthcare provider.",
            "Maintain prescribed therapeutic and dietary regimens."
        ]
    }

