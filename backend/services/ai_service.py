import os
import json
import re
import httpx
from typing import Optional, Dict, Any

def get_api_key() -> tuple[Optional[str], str]:
    """
    Returns (api_key, provider_name).
    Checks GROQ_API_KEY first for high-speed LPU inference.
    """
    # 1. Check local .env file first
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 1st priority: Groq Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val.startswith("gsk_") and len(val) > 20:
                            return val, "groq"

                # 2nd priority: Gemini Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your_") and len(val) > 20:
                            return val, "gemini"

                # 3rd priority: OpenAI Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your_") and len(val) > 20:
                            return val, "openai"
        except Exception as e:
            print(f"Error reading .env: {e}")

    # 2. Environment variables
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.startswith("gsk_"):
        return groq_key.strip(), "groq"

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip() and not gemini_key.startswith("your_") and len(gemini_key) > 20:
        return gemini_key.strip(), "gemini"

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.strip() and not openai_key.startswith("your_"):
        return openai_key.strip(), "openai"

    return None, "none"


SYSTEM_PROMPT_DOCTOR = """You are Dr. Quantum, the lead clinical AI physician for QuantumMedAI.
You provide compassionate, medically accurate, and structured clinical assessments for patients.

CRITICAL INSTRUCTIONS WHEN A PATIENT DESCRIBES SYMPTOMS OR ASKS ABOUT A DISEASE:
1. Empathy & Disease Basics: Explain clearly what the disease or symptom cluster is, how it affects the body, and its most common causes.
2. Clinical Prediction & Risk Stratification: Provide a thoughtful diagnostic evaluation (e.g. "Based on the symptoms described, potential conditions to consider include: ...").
3. Specific Symptoms to Watch: Highlight hallmark symptoms and warning red flags.
4. Actionable Home Care & Lifestyle: Recommend evidence-based supportive care (hydration, dietary guidance, rest, vitals tracking).
5. Next Clinical Steps & Doctor Referral: Specify the exact medical specialist to consult (e.g. Cardiologist, Nephrologist, Hepatologist, Neurologist, Endocrinologist, Gynecologist, General Physician) and key diagnostic tests (e.g. Blood Panel, Ultrasound, ECG, LFT, KFT, HbA1c).
6. QuantumMedAI Tool Integration: If the condition relates to Heart, Kidney, Liver, Stroke, PCOS, PCOD, or BMI, advise the patient to use the dedicated Disease Predictor calculator on the platform.

Always format your response as valid JSON with these exact keys:
{
  "ai_reply": "Your full compassionate, structured clinical explanation, disease prediction, and advice.",
  "is_emergency": false,
  "matched_keywords": ["symptoms or disease mentioned"],
  "detected_diseases": ["Primary Suspected Disease / Condition"],
  "risk_level": "Low" | "Moderate" | "High" | "Critical",
  "doctor": "Recommended Specialist (e.g. Cardiologist, Nephrologist, etc.)",
  "recommendation": "Main takeaway health recommendation."
}
"""


SYSTEM_PROMPT_EMERGENCY = """You are QuantumMedAI Emergency Triage Intelligence.
Analyze the emergency assessment answers provided for an acute patient.
Respond in valid JSON with these exact keys:
{
  "emergency": "Identified acute emergency condition",
  "severity": "Critical" or "High" or "Moderate" or "Low",
  "confidence": "95%",
  "doctor": "Emergency Specialist",
  "first_aid": [
    "Step 1 immediate action",
    "Step 2 action",
    "Step 3 action",
    "Step 4 action"
  ]
}
"""


def clean_human_reply(text: str) -> str:
    """Extracts human text and strips any raw JSON syntax."""
    if not text:
        return ""
    cleaned = text.strip()
    match = re.search(r'"ai_reply"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', cleaned)
    if match:
        extracted = match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
        if len(extracted) > 10:
            return extracted
    cleaned = re.sub(r'^\s*\{\s*"ai_reply"\s*:\s*"?', '', cleaned)
    cleaned = re.sub(r'"?\s*,\s*"(?:doctor|is_emergency|matched_keywords|detected_diseases|risk_level|recommendation)".*$', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'["\}]\s*$', '', cleaned)
    return cleaned.strip()


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "ai_reply" in parsed:
            parsed["ai_reply"] = clean_human_reply(parsed["ai_reply"])
        return parsed
    except Exception:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and "ai_reply" in parsed:
                    parsed["ai_reply"] = clean_human_reply(parsed["ai_reply"])
                return parsed
            except Exception:
                pass
        
        # Fallback: if json parsing failed, extract ai_reply directly
        extracted = clean_human_reply(cleaned)
        if extracted and len(extracted) > 10:
            return {
                "ai_reply": extracted,
                "is_emergency": False,
                "matched_keywords": ["General Health"],
                "detected_diseases": ["Clinical Consultation"],
                "risk_level": "Low",
                "doctor": "General Physician",
                "recommendation": "Consult a healthcare provider if symptoms persist."
            }
        return None


# Global persistent HTTP client for connection reuse with resilient timeout
_http_client = httpx.Client(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=30, max_connections=50))


def call_groq(api_key: str, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    """Instant sub-second LPU inference using Groq."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"]
    
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 800
        }
        try:
            res = _http_client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = extract_json(content)
                if parsed and ("ai_reply" in parsed or "emergency" in parsed):
                    return parsed
                else:
                    clean_msg = clean_human_reply(content)
                    if clean_msg and len(clean_msg) > 10:
                        return {
                            "ai_reply": clean_msg,
                            "is_emergency": False,
                            "matched_keywords": ["Clinical inquiry"],
                            "detected_diseases": ["Medical Consultation"],
                            "risk_level": "Low",
                            "doctor": "General Physician",
                            "recommendation": "Consult your healthcare provider if symptoms worsen."
                        }
        except Exception as e:
            print(f"[Groq Error {model}]: {e}")
            continue

    return None


def call_gemini(api_key: str, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    full_prompt = f"{system_prompt}\n\nPatient Query / Input:\n{prompt}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }

    for model in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            res = _http_client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0]["content"]["parts"][0]["text"]
                    parsed = extract_json(text)
                    if parsed:
                        return parsed
                    return {
                        "ai_reply": clean_human_reply(text),
                        "is_emergency": False,
                        "matched_keywords": ["Clinical inquiry"],
                        "detected_diseases": ["Medical Consultation"],
                        "risk_level": "Low",
                        "doctor": "General Physician",
                        "recommendation": "Consult a healthcare provider for clinical evaluation."
                    }
        except Exception as ex:
            print(f"[Gemini Exception {model}]: {ex}")
            continue

    return None



def call_openai(api_key: str, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    try:
        res = _http_client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if res.status_code == 200:
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            return extract_json(content)
    except Exception as e:
        print(f"[OpenAI Error]: {e}")
    return None


def analyze_with_ai(query_text: str, document_name: Optional[str] = None, language: str = "en") -> Optional[Dict[str, Any]]:
    """
    Main generative AI entrypoint.
    Executes Groq (ultra-fast), Gemini, or OpenAI with strict language alignment.
    """
    api_key, provider = get_api_key()
    if not api_key:
        return None

    # Detect language from text if not explicitly set
    clean_lang = (language or "en").lower().strip()
    if any('\u0c00' <= char <= '\u0c7f' for char in query_text):
        clean_lang = "te"
    elif any('\u0900' <= char <= '\u097f' for char in query_text):
        clean_lang = "hi"

    lang_instruction = ""
    if clean_lang == "te":
        lang_instruction = (
            "\n\n=======================================================\n"
            "CRITICAL LANGUAGE INSTRUCTION: TELUGU (తెలుగు)\n"
            "The patient has selected TELUGU.\n"
            "You MUST respond 100% in natural, polite TELUGU SCRIPT (తెలుగు లిపిలో మాత్రమే సమాధానం రాయండి).\n"
            "The values for 'ai_reply', 'doctor', and 'recommendation' MUST ALL BE IN TELUGU.\n"
            "DO NOT OUTPUT ENGLISH.\n"
            "======================================================="
        )
    elif clean_lang == "hi":
        lang_instruction = (
            "\n\n=======================================================\n"
            "CRITICAL LANGUAGE INSTRUCTION: HINDI (हिंदी)\n"
            "The patient has selected HINDI.\n"
            "You MUST respond 100% in natural, polite HINDI DEVANAGARI SCRIPT (हिंदी लिपि में ही उत्तर दें).\n"
            "The values for 'ai_reply', 'doctor', and 'recommendation' MUST ALL BE IN HINDI.\n"
            "DO NOT OUTPUT ENGLISH.\n"
            "======================================================="
        )
    else:
        lang_instruction = "\nRespond warmly and professionally in English."

    sys_prompt = SYSTEM_PROMPT_DOCTOR + lang_instruction
    prompt = f"Patient inquiry: {query_text}"
    if document_name:
        prompt += f"\nAttached document name: {document_name}"

    if provider == "groq":
        res = call_groq(api_key, prompt, sys_prompt)
        if res:
            return res
    elif provider == "gemini":
        res = call_gemini(api_key, prompt, sys_prompt)
        if res:
            return res
    elif provider == "openai":
        res = call_openai(api_key, prompt, sys_prompt)
        if res:
            return res

    return None


def emergency_with_ai(data: dict) -> Optional[Dict[str, Any]]:
    """
    Emergency assessment using Groq, Gemini, or OpenAI.
    """
    api_key, provider = get_api_key()
    if not api_key:
        return None

    prompt = f"Emergency Assessment Parameters:\n{json.dumps(data, indent=2)}"
    if provider == "groq":
        res = call_groq(api_key, prompt, SYSTEM_PROMPT_EMERGENCY)
        if res:
            return res
    elif provider == "gemini":
        res = call_gemini(api_key, prompt, SYSTEM_PROMPT_EMERGENCY)
        if res:
            return res
    elif provider == "openai":
        res = call_openai(api_key, prompt, SYSTEM_PROMPT_EMERGENCY)
        if res:
            return res

    return None
