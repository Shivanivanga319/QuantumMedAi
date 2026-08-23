from services.quantum_service import predict_liver_quantum

def predict_liver(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_liver_quantum(data, language=lang)