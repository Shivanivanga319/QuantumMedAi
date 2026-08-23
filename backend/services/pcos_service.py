from services.quantum_service import predict_pcos_quantum

def predict_pcos(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_pcos_quantum(data, language=lang)