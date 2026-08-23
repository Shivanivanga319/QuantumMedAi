from services.quantum_service import predict_stroke_quantum

def predict_stroke(data, language: str = "en"):
    lang = getattr(data, 'language', language) or language
    return predict_stroke_quantum(data, language=lang)