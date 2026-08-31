import os
import json
import re
import httpx
from typing import Optional, Dict, Any

def get_api_key() -> tuple[Optional[str], str]:
    """
    Returns (api_key, provider_name).
    Checks CEREBRAS_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY.
    Environment variables take precedence, followed by local .env file.
    """
    # 1. Check system / Render environment variables first
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key and cerebras_key.strip() and not cerebras_key.startswith("your_") and len(cerebras_key.strip()) > 15:
        return cerebras_key.strip(), "cerebras"

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.startswith("gsk_"):
        return groq_key.strip(), "groq"

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip() and not gemini_key.startswith("your_") and len(gemini_key) > 20:
        return gemini_key.strip(), "gemini"

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.strip() and not openai_key.startswith("your_"):
        return openai_key.strip(), "openai"

    # 2. Check local .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 1st priority: Cerebras Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("CEREBRAS_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your_") and len(val) > 15:
                            return val, "cerebras"

                # 2nd priority: Groq Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val.startswith("gsk_") and len(val) > 20:
                            return val, "groq"

                # 3rd priority: Gemini Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your_") and len(val) > 20:
                            return val, "gemini"

                # 4th priority: OpenAI Key
                for line in lines:
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("your_") and len(val) > 20:
                            return val, "openai"
        except Exception as e:
            print(f"Error reading .env: {e}")

    return None, "none"


SYSTEM_PROMPT_DOCTOR = """You are Dr. Quantum, the lead clinical AI physician and medical consultant for QuantumMedAI.
You provide compassionate, highly intelligent, medically accurate, and structured clinical assessments for patients.

CRITICAL CLINICAL PRINCIPLES:
1. Dynamic & Conversational Tone:
   - Address the patient's specific question or symptom directly and empathetically.
   - If this is a follow-up or clarifying question in the conversation, maintain natural continuity and reference prior statements smoothly.
   - Never sound robotic or generic. Avoid repeating rigid boilerplate when a direct conversational answer is needed.

2. Comprehensive Clinical Reasoning:
   - Empathy & Pathology: Explain clearly what is happening in the body and likely underlying causes in simple, reassuring language.
   - Clinical Prediction: Offer thoughtful differential considerations (e.g. "Based on these symptoms, primary possibilities include...").
   - Hallmark Signs & Red Flags: Highlight symptoms to monitor and when to seek urgent care.
   - Actionable Supportive Self-Care: Give evidence-based lifestyle, hydration, dietary, and gentle relief measures.
   - Specialist Referral & Diagnostics: Specify the exact specialist doctor to consult (e.g. Dermatologist, Cardiologist, Gastroenterologist, Endocrinologist, Neurologist, Pulmonologist, Gynecologist, General Physician) and standard lab tests to consider (e.g. CBC, Ultrasound, ECG, LFT/KFT, HbA1c, Thyroid Panel).
   - QuantumMedAI Tools: Suggest using the platform's Disease Predictors (Heart, Kidney, Liver, Stroke, PCOS, BMI) when relevant.

Always format your response as valid JSON with these exact keys:
{
  "ai_reply": "Your full compassionate, structured clinical explanation with markdown bullet points and clear guidance.",
  "is_emergency": false,
  "matched_keywords": ["symptoms or conditions mentioned"],
  "detected_diseases": ["Primary Suspected Condition / Assessment Profile"],
  "risk_level": "Low" | "Moderate" | "High",
  "doctor": "Recommended Specialist (e.g. Dermatologist, Cardiologist, General Physician)",
  "recommendation": "Main takeaway health recommendation."
}
"""


SYSTEM_PROMPT_EMERGENCY = """You are QuantumMedAI Emergency Triage Intelligence.
Analyze the emergency assessment answers provided for an acute patient.
Respond in valid JSON with these exact keys:
{
  "emergency": "Identified acute emergency condition",
  "severity": "Critical" | "High" | "Moderate" | "Low",
  "confidence": "95%",
  "doctor": "Emergency Physician",
  "first_aid": [
    "Step 1 immediate action",
    "Step 2 action",
    "Step 3 action",
    "Step 4 action"
  ]
}
"""


def clean_human_reply(text: str) -> str:
    """Extracts human text if raw JSON was returned as a string."""
    if not text:
        return ""
    cleaned = text.strip()
    match = re.search(r'"ai_reply"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', cleaned)
    if match:
        extracted = match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
        if len(extracted) > 5:
            return extracted
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
            return parsed
    except Exception:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict) and "ai_reply" in parsed:
                    return parsed
            except Exception:
                pass
    
    # Fallback: if json parsing failed, treat model output directly as human reply
    human_text = clean_human_reply(cleaned)
    if human_text and len(human_text) > 5:
        is_em = any(w in human_text.lower() for w in ["call 108", "call 112", "immediate emergency", "emergency room", "తీవ్రమైన అత్యవసర", "आपातकालीन"])
        return {
            "ai_reply": human_text,
            "is_emergency": is_em,
            "matched_keywords": ["Clinical Assessment"],
            "detected_diseases": ["Medical Evaluation Profile"],
            "risk_level": "High" if is_em else "Moderate",
            "doctor": "General Physician / Specialist",
            "recommendation": "Consult a healthcare provider for comprehensive evaluation."
        }
    return None


# Global persistent HTTP client for connection reuse with resilient timeout
_http_client = httpx.Client(timeout=10.0, limits=httpx.Limits(max_keepalive_connections=30, max_connections=50))


def build_conversation_messages(system_prompt: str, prompt: str, history: Optional[List[dict]] = None) -> list:
    messages = [{"role": "system", "content": system_prompt}]
    if history and isinstance(history, list):
        for msg in history[-8:]:
            sender = msg.get("sender") or msg.get("role")
            text = (msg.get("text") or msg.get("content") or "").strip()
            if text and sender and not text.startswith("🚨 CRITICAL EMERGENCY"):
                clean_text = clean_human_reply(text) if "ai_reply" in text else text
                role = "user" if sender == "user" else "assistant"
                messages.append({"role": role, "content": clean_text[:1200]})
    messages.append({"role": "user", "content": prompt})
    return messages


def call_cerebras(api_key: str, prompt: str, system_prompt: str, history: Optional[List[dict]] = None) -> Optional[Dict[str, Any]]:
    """Ultra-high-speed Wafer-Scale Engine inference using Cerebras (2,000+ tokens/sec)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    models = ["llama-3.3-70b", "llama3.1-70b", "llama3.1-8b"]
    messages = build_conversation_messages(system_prompt, prompt, history)
    
    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.25,
            "max_tokens": 1000
        }
        try:
            res = _http_client.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = extract_json(content)
                if parsed and ("ai_reply" in parsed or "emergency" in parsed):
                    return parsed
                else:
                    clean_msg = clean_human_reply(content)
                    if clean_msg and len(clean_msg) > 5:
                        return {
                            "ai_reply": clean_msg,
                            "is_emergency": False,
                            "matched_keywords": ["Clinical Consultation"],
                            "detected_diseases": ["Medical Assessment"],
                            "risk_level": "Low",
                            "doctor": "General Physician",
                            "recommendation": "Follow clinical advice and consult a physician if symptoms persist."
                        }
        except Exception as e:
            print(f"[Cerebras Error {model}]: {e}")
            continue

    return None


def call_groq(api_key: str, prompt: str, system_prompt: str, history: Optional[List[dict]] = None) -> Optional[Dict[str, Any]]:
    """Instant sub-second LPU inference using Groq."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"]
    messages = build_conversation_messages(system_prompt, prompt, history)
    
    for model in models:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.25,
            "max_tokens": 1000
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
                    if clean_msg and len(clean_msg) > 5:
                        return {
                            "ai_reply": clean_msg,
                            "is_emergency": False,
                            "matched_keywords": ["Clinical Consultation"],
                            "detected_diseases": ["Medical Assessment"],
                            "risk_level": "Low",
                            "doctor": "General Physician",
                            "recommendation": "Follow clinical advice and consult a physician if symptoms persist."
                        }
        except Exception as e:
            print(f"[Groq Error {model}]: {e}")
            continue

    return None


def call_gemini(api_key: str, prompt: str, system_prompt: str, history: Optional[List[dict]] = None) -> Optional[Dict[str, Any]]:
    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
    
    # Build parts from history
    contents = []
    contents.append({
        "role": "user",
        "parts": [{"text": system_prompt}]
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Understood. I am Dr. Quantum, ready to assist."}]
    })
    if history and isinstance(history, list):
        for msg in history[-6:]:
            sender = msg.get("sender") or msg.get("role")
            text = (msg.get("text") or msg.get("content") or "").strip()
            if text and sender and not text.startswith("🚨 CRITICAL EMERGENCY"):
                role = "user" if sender == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": text[:1000]}]
                })
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 1000
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
                        "matched_keywords": ["Clinical Consultation"],
                        "detected_diseases": ["Medical Assessment"],
                        "risk_level": "Low",
                        "doctor": "General Physician",
                        "recommendation": "Consult a healthcare provider for clinical evaluation."
                    }
        except Exception as ex:
            print(f"[Gemini Exception {model}]: {ex}")
            continue

    return None



def call_openai(api_key: str, prompt: str, system_prompt: str, history: Optional[List[dict]] = None) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    messages = build_conversation_messages(system_prompt, prompt, history)
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.25
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


def analyze_with_ai(
    query_text: str,
    document_name: Optional[str] = None,
    language: str = "en",
    history: Optional[List[dict]] = None
) -> Optional[Dict[str, Any]]:
    """
    Main generative AI entrypoint with multi-turn conversation memory.
    Executes Cerebras (ultra-fast 2000+ tok/s), Groq, Gemini, or OpenAI with strict language alignment.
    """
    api_key, provider = get_api_key()
    if not api_key:
        return None

    # Detect language from text intent if requested in prompt
    clean_lang = (language or "en").lower().strip()
    if re.search(r'\b(telugu|telgu|తెలుగు|telugu\s*lo|in\s*telugu)\b', query_text, re.IGNORECASE) or any('\u0c00' <= char <= '\u0c7f' for char in query_text):
        clean_lang = "te"
    elif re.search(r'\b(hindi|हिन्दी|हिंदी|hindi\s*me|in\s*hindi)\b', query_text, re.IGNORECASE) or any('\u0900' <= char <= '\u097f' for char in query_text):
        clean_lang = "hi"
    elif re.search(r'\b(in\s*english|explain\s*in\s*english)\b', query_text, re.IGNORECASE):
        clean_lang = "en"

    lang_instruction = ""
    if clean_lang == "te":
        lang_instruction = (
            "\n\n=======================================================\n"
            "CRITICAL LANGUAGE INSTRUCTION: TELUGU (తెలుగు)\n"
            "The patient requested / selected TELUGU.\n"
            "You MUST respond 100% in natural, polite TELUGU SCRIPT (తెలుగు లిపిలో మాత్రమే సమాధానం రాయండి).\n"
            "If the user asks to explain previous context in Telugu, explain the previous discussion in complete, fluent Telugu.\n"
            "The values for 'ai_reply', 'doctor', and 'recommendation' MUST ALL BE IN TELUGU.\n"
            "DO NOT OUTPUT ENGLISH.\n"
            "======================================================="
        )
    elif clean_lang == "hi":
        lang_instruction = (
            "\n\n=======================================================\n"
            "CRITICAL LANGUAGE INSTRUCTION: HINDI (हिंदी)\n"
            "The patient requested / selected HINDI.\n"
            "You MUST respond 100% in natural, polite HINDI DEVANAGARI SCRIPT (हिंदी लिपि में ही उत्तर दें).\n"
            "If the user asks to explain previous context in Hindi, explain the previous discussion in complete, fluent Hindi.\n"
            "The values for 'ai_reply', 'doctor', and 'recommendation' MUST ALL BE IN HINDI.\n"
            "DO NOT OUTPUT ENGLISH.\n"
            "======================================================="
        )
    else:
        lang_instruction = "\nRespond warmly, conversationally, and professionally in English."

    sys_prompt = SYSTEM_PROMPT_DOCTOR + lang_instruction
    prompt = f"Patient message: {query_text}"
    if document_name:
        prompt += f"\nAttached document name: {document_name}"

    if provider == "cerebras":
        res = call_cerebras(api_key, prompt, sys_prompt, history)
        if res:
            return res
    elif provider == "groq":
        res = call_groq(api_key, prompt, sys_prompt, history)
        if res:
            return res
    elif provider == "gemini":
        res = call_gemini(api_key, prompt, sys_prompt, history)
        if res:
            return res
    elif provider == "openai":
        res = call_openai(api_key, prompt, sys_prompt, history)
        if res:
            return res

    return None


def emergency_with_ai(data: dict) -> Optional[Dict[str, Any]]:
    """
    Emergency assessment using Cerebras, Groq, Gemini, or OpenAI.
    """
    api_key, provider = get_api_key()
    if not api_key:
        return None

    prompt = f"Emergency Assessment Parameters:\n{json.dumps(data, indent=2)}"
    if provider == "cerebras":
        res = call_cerebras(api_key, prompt, SYSTEM_PROMPT_EMERGENCY)
        if res:
            return res
    elif provider == "groq":
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
