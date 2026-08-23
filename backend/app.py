from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from database import Base, engine
from models.user import User
from models.prediction import Prediction
from routes.auth import router as auth_router
from routes.heart import router as heart_router
from routes.liver import router as liver_router
from routes.pcos import router as pcos_router
from routes.pcod import router as pcod_router
from routes import stroke
from routes import kidney
from routes import emergency
from routes import predictions

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="QuantumMedAI API",
    description="Hybrid Quantum Deep Learning Framework for Multi-Disease Prediction and Intelligent Emergency Response Support",
    version="1.0.0"
)

# Enable CORS for Frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Register All API Routers
app.include_router(auth_router)
app.include_router(heart_router)
app.include_router(liver_router)
app.include_router(pcos_router)
app.include_router(pcod_router)
app.include_router(stroke.router)
app.include_router(kidney.router)
app.include_router(emergency.router)
app.include_router(predictions.router)


@app.get("/")
def home():
    return {
        "project": "QuantumMedAI",
        "message": "Welcome to QuantumMedAI Backend 🚀",
        "status": "Backend is running successfully!",
        "endpoints": {
            "auth": ["/auth/register", "/auth/login", "/auth/me"],
            "predictions": [
                "/heart/predict",
                "/liver/predict",
                "/kidney/predict",
                "/stroke/predict",
                "/pcos/predict",
                "/pcod/predict",
                "/emergency/check",
                "/predictions/symptoms",
                "/predictions/history"
            ],
            "docs": "/docs"
        }
    }