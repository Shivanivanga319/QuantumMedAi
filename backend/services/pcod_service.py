from services.quantum_service import predict_pcod_quantum

def predict_pcod(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_pcod_quantum(data, language=lang)