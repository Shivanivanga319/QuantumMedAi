from services.quantum_service import predict_kidney_quantum

def predict_kidney(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_kidney_quantum(data, language=lang)