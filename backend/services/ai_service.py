import os
import json
import re
import httpx
from typing import Optional, Dict, Any

def get_all_api_keys() -> Dict[str, str]:
    """
    Returns a dictionary of all configured API keys:
    {'gemini': '...', 'cerebras': '...', 'groq': '...', 'openai': '...'}
    Environment variables take precedence, followed by local .env file.
    """
    keys = {}
    
    # 1. Check system / Render environment variables first
    for env_var, prov in [
        ("GEMINI_API_KEY", "gemini"),
        ("CEREBRAS_API_KEY", "cerebras"),
        ("GROQ_API_KEY", "groq"),
        ("OPENAI_API_KEY", "openai")
    ]:
        val = os.getenv(env_var)
        if val and val.strip() and not val.startswith("your_") and len(val.strip()) > 15:
            keys[prov] = val.strip()

    # 2. Check local .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    for env_var, prov in [
                        ("GEMINI_API_KEY", "gemini"),
                        ("CEREBRAS_API_KEY", "cerebras"),
                        ("GROQ_API_KEY", "groq"),
                        ("OPENAI_API_KEY", "openai")
                    ]:
                        if line.startswith(f"{env_var}="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val and not val.startswith("your_") and len(val) > 15 and prov not in keys:
                                keys[prov] = val
        except Exception as e:
            print(f"Error reading .env: {e}")

    return keys


def get_api_key() -> tuple[Optional[str], str]:
    """
    Returns (api_key, provider_name).
    Prioritizes Gemini -> Cerebras -> Groq -> OpenAI.
    """
    keys = get_all_api_keys()
    for prov in ["gemini", "cerebras", "groq", "openai"]:
        if prov in keys:
            return keys[prov], prov
    return None, "none"


SYSTEM_PROMPT_DOCTOR = """You are Dr. Quantum, the clinical AI physician for QuantumMedAI.
You provide brief, highly focused, concise, and professional clinical medical guidance.

CRITICAL INSTRUCTIONS:
1. STRICT BREVITY & CONCISENESS:
   - Do NOT write long paragraphs or essays. Patients need quick, clear answers.
   - Keep your entire reply strictly under 80 to 120 words total.
   - Directly answer the patient's immediate question or symptom in the very first sentence.

2. STRUCTURED 3-PART FORMAT:
   Organize your response into at most 3 concise bullet sections:
   - Assessment: 1-2 short sentences identifying the likely cause or condition.
   - Care & Relief: 2-3 brief bullet points for immediate safe home care / lifestyle relief.
   - Next Step: 1 sentence specifying the specialist to consult and recommended test.

3. LAB & BLOOD REPORT CLINICAL EVALUATION:
   - When the patient provides blood test values or a lab report (e.g. Hemoglobin, Platelets, WBC, ESR, Blood Sugar, HbA1c, Bilirubin, SGPT/ALT, SGOT/AST, Creatinine, Urea, Lipid Profile/Cholesterol, Thyroid/TSH):
   - Explicitly evaluate each reported number against standard clinical reference ranges (classify as Low, Normal, or High).
   - In Assessment, state what these abnormal biomarkers signify (e.g. anemia, acute infection, hepatic inflammation, renal strain, dyslipidemia).
   - In Care & Relief, provide targeted dietary, hydration, or lifestyle guidance.
   - In Next Step, identify the exact medical specialist (Hematologist, Nephrologist, Gastroenterologist, Endocrinologist) and confirmatory tests.

4. ZERO EMOJIS:
   - Do NOT use any emojis in your response. Keep the tone completely clean, clinical, and professional.

Always format your response as valid JSON with these exact keys:
{
  "ai_reply": "Your brief, concise, emoji-free markdown clinical response.",
  "is_emergency": false,
  "matched_keywords": ["symptoms or conditions mentioned"],
  "detected_diseases": ["Primary Suspected Condition"],
  "risk_level": "Low" | "Moderate" | "High",
  "doctor": "Recommended Specialist (e.g. General Physician, Dermatologist, Cardiologist)",
  "recommendation": "One-line key recommendation."
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
            if text and sender and not text.startswith(" CRITICAL EMERGENCY"):
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
    models_to_try = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-flash-latest"
    ]
    
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
            if text and sender and not text.startswith(" CRITICAL EMERGENCY"):
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
    Executes Gemini, Cerebras, Groq, or OpenAI with resilient multi-provider fallback and language alignment.
    """
    keys = get_all_api_keys()
    if not keys:
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

    # Resilient multi-provider execution chain: Gemini -> Cerebras -> Groq -> OpenAI
    provider_order = ["gemini", "cerebras", "groq", "openai"]
    for prov in provider_order:
        if prov in keys:
            api_key = keys[prov]
            try:
                res = None
                if prov == "gemini":
                    res = call_gemini(api_key, prompt, sys_prompt, history)
                elif prov == "cerebras":
                    res = call_cerebras(api_key, prompt, sys_prompt, history)
                elif prov == "groq":
                    res = call_groq(api_key, prompt, sys_prompt, history)
                elif prov == "openai":
                    res = call_openai(api_key, prompt, sys_prompt, history)
                if res and (res.get("ai_reply") or res.get("emergency")):
                    return res
            except Exception as e:
                print(f"[Provider {prov} failed]: {e}")
                continue

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
