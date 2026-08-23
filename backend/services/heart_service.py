from services.quantum_service import predict_heart_quantum

def predict_heart(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_heart_quantum(data, language=lang)