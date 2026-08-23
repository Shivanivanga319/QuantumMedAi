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


SYSTEM_PROMPT_DOCTOR = """You are Dr. Quantum, an empathetic, caring human medical physician with QuantumMedAI.
Speak warmly and naturally like a compassionate, experienced doctor talking to a patient.

GUIDELINES:
1. Warm Empathy: Validate how the patient is feeling with comforting, understanding words.
2. Plain Explanation: Explain in simple terms what is likely causing their discomfort (e.g. common cold, viral infection, tension).
3. Gentle Home Care: Recommend soothing home remedies (warm water, ginger-honey tea, steam inhalation, restful sleep, hydration).
4. Red Flags & Doctor Referral: Mention what warning signs to watch for and advise consulting a General Physician if symptoms persist.
5. Tone: Natural, caring, human. Never output raw JSON or code markers in the conversation text.

Always output your response in valid JSON with these exact keys:
{
  "ai_reply": "Your full warm doctor reply to the patient here.",
  "is_emergency": false,
  "matched_keywords": ["identified symptoms"],
  "detected_diseases": ["probable health topic"],
  "risk_level": "Low" or "Moderate" or "High",
  "doctor": "Recommended Specialist (e.g. General Physician, ENT Specialist, etc.)",
  "recommendation": "Main takeaway health advice."
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


# Global persistent HTTP client for connection reuse / ultra-low latency
_http_client = httpx.Client(timeout=3.0, limits=httpx.Limits(max_keepalive_connections=30, max_connections=50))


def call_groq(api_key: str, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    """Instant sub-second LPU inference using Groq."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    models = ["openai/gpt-oss-20b", "allam-2-7b"]
    
    for model in models:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 400
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
            print(f"[Groq Timeout/Error {model}]: {e}")
            break

    return None


def call_gemini(api_key: str, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    models_to_try = ["gemini-1.5-flash"]
    full_prompt = f"{system_prompt}\n\nPatient Query / Input:\n{prompt}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ]
    }

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
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
        print(f"[Gemini Exception]: {ex}")

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
    Executes Groq (ultra-fast), Gemini, or OpenAI.
    """
    api_key, provider = get_api_key()
    if not api_key:
        return None

    lang_instruction = ""
    if language == "te":
        lang_instruction = "\nCRITICAL: Respond COMPLETELY in warm, natural Telugu (తెలుగు భాషలో సమాధానం ఇవ్వండి)."
    elif language == "hi":
        lang_instruction = "\nCRITICAL: Respond COMPLETELY in warm, natural Hindi (हिंदी भाषा में उत्तर दें)."
    else:
        lang_instruction = "\nRespond warmly in English."

    sys_prompt = SYSTEM_PROMPT_DOCTOR + lang_instruction
    prompt = f"Patient says: {query_text}"
    if document_name:
        prompt += f"\nAttached document context: {document_name}"

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
